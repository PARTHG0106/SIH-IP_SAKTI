"""Hybrid, metadata-filtered retrieval over the curated statute corpus.

Design (from the architecture): BM25 keyword + optional dense embeddings,
fused by Reciprocal Rank Fusion, with a jurisdiction/regime/category metadata
filter applied BEFORE scoring. Both scopes are included only when explicitly
requested, and every returned record retains its original jurisdiction.

BM25 is implemented in pure Python so retrieval works with zero heavy
dependencies (important on new Python versions); dense embeddings are an
optional upgrade enabled with RETRIEVER=hybrid.
"""
from __future__ import annotations
import json
import hashlib
import math
import re
from collections import Counter, defaultdict
from .config import settings
from .sources import validate_source
from .planning import plan_query

_STOP = set("""a an the of to in on for and or is are be as by with from at this that these those
which who whom what when where how do does did can could should would may might must i my me we our
you your it its their them they he she his her not no yes if then than so such about into over under
per etc eg ie please explain tell give know information details
answer answers question questions previous original retrieved sources source table columns
issue issues relevant establish establishes established inference application insufficient evidence
write statement statements directly reproduce excerpts step steps based only include every
requested supported conclusion conclusions create provide remains unanswered separate format""".split())

_TOKEN = re.compile(r"[a-z0-9]+")


def _tok(text: str) -> list[str]:
    text = re.sub(r"\b(\d+)\s*\(([a-z])\)", r"\1\2", (text or "").lower())
    return _TOKEN.findall(text)


def _content_terms(text: str) -> set[str]:
    return {t for t in _tok(text) if len(t) >= 2 and t not in _STOP}


class Corpus:
    def __init__(self, path=None):
        self.docs: list[dict] = []
        with open(path or settings.corpus_path, encoding="utf-8") as f:
            raw = f.read()
            seen = set()
            for line_number, line in enumerate(raw.splitlines(), 1):
                line = line.strip()
                if line:
                    try:
                        doc = validate_source(json.loads(line))
                        if doc["id"] in seen:
                            raise ValueError(f"Duplicate source id: {doc['id']}")
                        seen.add(doc["id"])
                        self.docs.append(doc)
                    except (ValueError, TypeError) as exc:
                        raise ValueError(f"Invalid corpus record on line {line_number}: {exc}") from exc
        if not self.docs:
            raise ValueError("The corpus must contain at least one source")
        self.version = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
        self.by_id = {d["id"]: d for d in self.docs}
        # searchable text per doc = title + statute + section + text + keywords
        self._search_text = []
        self._tokens = []
        for d in self.docs:
            blob = " ".join([
                d.get("title", ""), d.get("statute", ""), d.get("section", ""),
                d.get("text", ""), " ".join(d.get("keywords", [])),
            ])
            self._search_text.append(blob)
            self._tokens.append(_tok(blob))
        self._build_bm25()

    # ---------------- BM25 ----------------
    def _build_bm25(self, k1: float = 1.5, b: float = 0.75):
        self.k1, self.b = k1, b
        self.N = len(self._tokens)
        self.doc_len = [len(t) for t in self._tokens]
        self.avgdl = (sum(self.doc_len) / self.N) if self.N else 0.0
        self.tf = [Counter(t) for t in self._tokens]
        df: Counter = Counter()
        for toks in self._tokens:
            for term in set(toks):
                df[term] += 1
        self.idf = {term: math.log(1 + (self.N - n + 0.5) / (n + 0.5)) for term, n in df.items()}

    def _bm25_score(self, q_terms: list[str], idx: int) -> float:
        tf, dl = self.tf[idx], self.doc_len[idx]
        s = 0.0
        for term in q_terms:
            if term not in tf:
                continue
            freq = tf[term]
            denom = freq + self.k1 * (1 - self.b + self.b * dl / (self.avgdl or 1))
            s += self.idf.get(term, 0.0) * (freq * (self.k1 + 1) / (denom or 1))
        return s

    def _passes_filter(self, d: dict, jurisdiction, regime, category) -> bool:
        if jurisdiction and jurisdiction != "Both" and d.get("jurisdiction") != jurisdiction:
            return False
        if regime and d.get("regime") != regime:
            return False
        if category:
            cats = d.get("categories") or []
            if cats and category not in cats:
                return False
        return True


class _DenseIndex:
    """Optional dense retriever (sentence-transformers). Lazy + fail-soft."""
    def __init__(self, corpus: "Corpus"):
        self.ok = False
        try:
            from sentence_transformers import SentenceTransformer  # type: ignore
            import numpy as np  # type: ignore
            self.np = np
            self.model = SentenceTransformer(settings.dense_model)
            passages = ["passage: " + t for t in corpus._search_text]
            self.emb = self.model.encode(passages, normalize_embeddings=True, convert_to_numpy=True)
            self.ok = True
        except Exception as e:  # pragma: no cover - optional path
            self.error = str(e)

    def rank(self, query: str) -> list[int]:
        q = self.model.encode(["query: " + query], normalize_embeddings=True, convert_to_numpy=True)
        sims = (self.emb @ q[0])
        return list(self.np.argsort(-sims))


class Retriever:
    def __init__(self, corpus: Corpus | None = None, mode: str | None = None):
        self.corpus = corpus or Corpus()
        self.dense = None
        self.requested_mode = mode or settings.retriever
        if self.requested_mode == "hybrid":
            self.dense = _DenseIndex(self.corpus)

    @property
    def effective_mode(self):
        return "hybrid" if self.dense and self.dense.ok else "bm25"

    def _rrf(self, rankings: list[list[int]], k: int = 60) -> dict[int, float]:
        fused: dict[int, float] = defaultdict(float)
        for ranking in rankings:
            for rank, idx in enumerate(ranking):
                fused[idx] += 1.0 / (k + rank + 1)
        return fused

    def search(self, query, jurisdiction=None, regime=None, category=None, top_k=None, *, plan=None):
        plan = plan or plan_query(query)
        # Each requested issue gets an independent evidence budget. A long
        # question must not squeeze fourteen issues into a global top-three set.
        requested_ids = list(dict.fromkeys(source for issue in plan.issues for source in issue.source_ids))
        budget = top_k if top_k is not None else max(settings.top_k, len(requested_ids), len(plan.subquestions) * 3)
        top_k = max(1, min(budget, 48))
        q_terms = sorted(_content_terms(query))
        if not q_terms:
            return [], 0.0
        allowed = [i for i, d in enumerate(self.corpus.docs)
                   if self.corpus._passes_filter(d, jurisdiction, regime, category)]
        if not allowed:
            return [], 0.0

        issue_terms = {issue.key: sorted(_content_terms(issue.search)) for issue in plan.issues}
        relevant = {i for i in allowed if self.corpus.docs[i]["id"] in requested_ids}
        scores = {i: self.corpus._bm25_score(q_terms, i) for i in allowed}
        # Reviewed concept mappings supply paraphrase recall ("brand" -> the
        # trademark provision) while keeping formatting words out of retrieval.
        topic_rankings = []
        for issue in plan.issues:
            topic = [i for i in relevant if self.corpus.docs[i]["id"] in issue.source_ids]
            for i in topic:
                scores[i] = max(scores[i], self.corpus._bm25_score(issue_terms[issue.key], i))
            topic_rankings.append(sorted(topic, key=lambda i: scores[i], reverse=True))
        # Model-decomposed search phrases can discover relevant records without
        # requiring a hardcoded source-ID mapping for every future question.
        # They never change the caller's metadata boundary.
        if plan.planner == "model":
            for phrase in plan.search_queries:
                terms = sorted(_content_terms(phrase))
                ranking = sorted(allowed, key=lambda i: self.corpus._bm25_score(terms, i), reverse=True)
                hits = [i for i in ranking[:4] if self.corpus._bm25_score(terms, i) > 0
                        and len(set(terms) & set(self.corpus._tokens[i])) >= 2]
                relevant.update(hits)
                for i in hits:
                    scores[i] = max(scores[i], self.corpus._bm25_score(terms, i))
                topic_rankings.append(hits)
        if relevant:
            allowed = list(relevant)
        # Stopwords and zero-score documents cannot create apparent evidence.
        allowed = [i for i in allowed if scores[i] > 0]
        if not allowed:
            return [], 0.0
        bm25 = sorted(allowed, key=lambda i: scores[i], reverse=True)
        rankings = [bm25, *topic_rankings]
        if self.dense and self.dense.ok:
            allowed_set = set(allowed)
            dense_rank = [i for i in self.dense.rank(query) if i in allowed_set]
            rankings.append(dense_rank)
        fused = self._rrf(rankings)
        order = sorted(allowed, key=lambda i: fused.get(i, 0.0), reverse=True)[:top_k]

        # ---- confidence for the abstain gate (length-independent) ----
        # Coverage as a fraction of the query penalises long, multi-topic questions
        # (a single statute chunk can only cover part of them). Score instead on
        # retrieval strength + the ABSOLUTE number of distinct query terms the best
        # top-3 document shares, so a detailed question is easier to answer, not harder.
        qc = _content_terms(query)
        top_bm25 = scores[order[0]] if order else 0.0
        score_norm = 1 - math.exp(-top_bm25 / 6.0)
        best_matches = 0
        for i in order[:3]:
            doc_terms = _content_terms(self.corpus._search_text[i])
            best_matches = max(best_matches, len(qc & doc_terms))
        if relevant:
            best_matches = max(2, best_matches)
        match_strength = min(1.0, best_matches / 3.0)  # >=3 shared terms => full strength
        confidence = round(0.55 * score_norm + 0.45 * match_strength, 3)
        # out-of-scope guard: almost no lexical overlap with the corpus -> force abstain
        if best_matches < 2:
            confidence = min(confidence, settings.abstain_threshold - 0.001)

        results = []
        for rank, i in enumerate(order):
            d = self.corpus.docs[i]
            results.append({
                "doc": d,
                "score": round(fused.get(i, 0.0), 5),
                "bm25": round(scores[i], 3),
                "rank": rank,
            })
        return results, confidence
