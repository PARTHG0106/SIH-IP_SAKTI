"""IP-SAKTI Sahayak HTTP API and static application."""
from __future__ import annotations

import logging
import asyncio
from contextlib import asynccontextmanager, suppress
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from . import consent, i18n
from .config import settings, DISCLAIMER
from .classifier import Classifier
from .models import ClassifyRequest, ClassifyResponse, AskRequest, AskResponse, ConsentRequest
from .pipeline import Assistant
from .memory import MemoryError, MAX_TURNS, TTL_SECONDS
from .retrieval import Retriever
from .router import RegistryRouter
from .sources import citation

@asynccontextmanager
async def lifespan(application):
    async def expire_chats():
        while True:
            await asyncio.sleep(60)
            assistant.memory.purge_expired()
    sweeper = asyncio.create_task(expire_chats())
    try:
        yield
    finally:
        sweeper.cancel()
        with suppress(asyncio.CancelledError):
            await sweeper


app = FastAPI(title="IP-SAKTI Sahayak", version="1.2.0", lifespan=lifespan,
              description="Dated, source-grounded Ayurveda IP and preliminary regulatory guidance.")
classifier = Classifier()
retriever = Retriever()
router = RegistryRouter()
assistant = Assistant(retriever, router)
FRONTEND = Path(__file__).resolve().parent.parent / "frontend"


@app.middleware("http")
async def privacy_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    # Generated API docs use CDN assets and an inline boot script.
    if request.url.path in {"/docs", "/redoc", "/docs/oauth2-redirect"}:
        response.headers["Content-Security-Policy"] = "base-uri 'self'; frame-ancestors 'none'"
    else:
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; "
            "connect-src 'self'; base-uri 'self'; frame-ancestors 'none'; form-action 'self'")
    if request.url.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store"
    return response


@app.get("/api/health")
def health():
    translation = i18n.available()
    return {
        "status": "ok", "llm_enabled": settings.llm_enabled,
        "llm_provider": settings.llm_provider if settings.llm_enabled else None,
        "llm_model": settings.llm_model if settings.llm_enabled else None,
        "retriever": retriever.effective_mode, "requested_retriever": retriever.requested_mode,
        "dense_ok": bool(retriever.dense and retriever.dense.ok),
        "corpus_size": len(retriever.corpus.docs), "corpus_version": retriever.corpus.version,
        "sources_needing_review": sum(d["review_status"] == "needs_review" for d in retriever.corpus.docs),
        "abstain_threshold": settings.abstain_threshold,
        "translation_available": translation,
        "languages": [{"code": "en", "name": "English", "available": True}]
                     + [{"code": code, "name": name, "available": translation} for code, name in i18n.INDIC.items()],
        "answer_mode": "rag_synthesis" if settings.llm_enabled else "reviewed_guidance",
        "domain": "Ayurveda IP and regulatory guidance",
        "chat_memory": {"storage": "process_memory", "ttl_seconds": TTL_SECONDS, "max_turns": MAX_TURNS},
        "privacy": {"query_text_logged": False, "external_provider_enabled": settings.llm_enabled,
                    "chat_transcripts_persisted": False},
    }


@app.post("/api/classify", response_model=ClassifyResponse)
def classify(req: ClassifyRequest):
    try:
        result = classifier.classify(req.answers, req.description)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    ids = (result.get("category_detail") or result.get("next_question") or {}).get("statutes", [])
    if result["needs_review"] and not ids and result["trail"]:
        ids = classifier.nodes[result["trail"][-1]["node"]].get("statutes", [])
    result["citations"] = [citation(retriever.corpus.by_id[i]) for i in ids]
    for item in result["citations"]:
        if item.review_status == "needs_review":
            item.snippet = ""
    result["disclaimer"] = "Preliminary India regulatory routing based on supplied facts. " + DISCLAIMER
    return ClassifyResponse(**result)


@app.post("/api/ask", response_model=AskResponse)
def ask(req: AskRequest):
    try:
        if req.conversation_id is None:
            req = req.model_copy(update={"conversation_id": assistant.memory.create()})
        response = assistant.answer(req)
    except MemoryError as exc:
        raise HTTPException(status_code=exc.status, detail={"reason": exc.reason, "message": str(exc)}) from exc
    try:
        consent.log_query(req.query, req.jurisdiction, req.lang, response.confidence,
                          response.abstained, [c.id for c in response.citations], response.answer_source,
                          request_id=response.request_id, category=req.category, reason=response.reason)
    except OSError:
        # Source-based information remains usable; do not claim a log was saved.
        logging.getLogger(__name__).warning("Query audit metadata could not be saved")
        response.notices.append("Audit metadata could not be saved for this request.")
    return response


@app.post("/api/chat")
def create_chat():
    try:
        return {"conversation_id": assistant.memory.create(), "ttl_seconds": TTL_SECONDS, "max_turns": MAX_TURNS}
    except MemoryError as exc:
        raise HTTPException(status_code=exc.status, detail={"reason": exc.reason, "message": str(exc)}) from exc


@app.delete("/api/chat/{conversation_id}")
def clear_chat(conversation_id: str):
    assistant.memory.delete(conversation_id)
    return {"cleared": True}


@app.post("/api/consent")
def post_consent(req: ConsentRequest):
    resource = router.get(req.resource_id)
    if resource is None:
        raise HTTPException(status_code=404, detail="Unknown registry resource.")
    if resource.get("access", "free") == "free":
        raise HTTPException(status_code=400, detail="This public resource does not require consent.")
    try:
        record = consent.log_consent(req.user_id, resource["id"], resource["name"],
                                     req.consent, req.purpose)
    except OSError as exc:
        raise HTTPException(status_code=503, detail="Consent could not be saved. Access has not been opened.") from exc
    return {"logged": True, "record": record, "url": resource["url"] if req.consent else None,
            "notice": "Opening a referral does not grant access to a restricted database or purchase a subscription."}


@app.get("/api/sources")
def sources():
    docs = retriever.corpus.docs
    return {"count": len(docs), "version": retriever.corpus.version,
            "needs_review": sum(d["review_status"] == "needs_review" for d in docs),
            "note": "Dossier-derived research notes. Source dates are not live verification dates.",
            "sources": [{**citation(d).model_dump(), "url": d["source_url"],
                         "snippet": "" if d["review_status"] == "needs_review" else d["text"]}
                        for d in docs]}


@app.get("/", response_class=HTMLResponse)
def index():
    return HTMLResponse((FRONTEND / "index.html").read_text(encoding="utf-8"))


app.mount("/assets", StaticFiles(directory=FRONTEND), name="assets")
