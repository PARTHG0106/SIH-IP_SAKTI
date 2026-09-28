"""Bounded, process-local chat memory; no transcripts or credentials on disk.

Opaque IDs are bearer capabilities, not account authentication. A deployment
with multiple workers needs sticky routing or a separately secured TTL store.
"""
from __future__ import annotations

from collections import OrderedDict, deque
from contextlib import contextmanager
from copy import deepcopy
from dataclasses import dataclass, field
import re
import secrets
from threading import Lock, RLock
import time
from .planning import starts_new_case
from .case_state import replaces_case


TTL_SECONDS = 30 * 60
MAX_SESSIONS = 128
MAX_TURNS = 8


class MemoryError(RuntimeError):
    def __init__(self, reason: str, message: str, status: int = 410):
        super().__init__(message)
        self.reason, self.status = reason, status


@dataclass
class Turn:
    query: str
    context_query: str
    sources: list[dict]
    corpus_version: str
    confidence: float


@dataclass
class Chat:
    id: str
    touched: float
    scope: tuple | None = None
    turns: deque = field(default_factory=lambda: deque(maxlen=MAX_TURNS))
    lock: Lock = field(default_factory=Lock)


class ConversationStore:
    def __init__(self, *, ttl=TTL_SECONDS, max_sessions=MAX_SESSIONS, clock=time.monotonic):
        self.ttl, self.max_sessions, self.clock = ttl, max_sessions, clock
        self._chats: OrderedDict[str, Chat] = OrderedDict()
        self._lock = RLock()

    def _expire(self):
        now = self.clock()
        for key, chat in list(self._chats.items()):
            if now - chat.touched >= self.ttl:
                del self._chats[key]

    def create(self) -> str:
        with self._lock:
            self._expire()
            if len(self._chats) >= self.max_sessions:
                # Evict an idle least-recently-used chat, never an active request.
                key = next((key for key, value in self._chats.items() if not value.lock.locked()), None)
                if key is None:
                    raise MemoryError("chat_capacity", "The chat service is busy. Please retry shortly.", 503)
                del self._chats[key]
            key = secrets.token_urlsafe(32)
            self._chats[key] = Chat(id=key, touched=self.clock())
            return key

    def delete(self, key: str):
        with self._lock:
            self._chats.pop(key, None)

    def purge_expired(self):
        with self._lock:
            self._expire()

    @contextmanager
    def transaction(self, key: str, scope: tuple):
        with self._lock:
            self._expire()
            chat = self._chats.get(key)
            if chat is None:
                raise MemoryError("chat_expired", "This temporary chat expired or was cleared. Start a new chat and restate the question.")
            if chat.scope is not None and chat.scope != scope:
                raise MemoryError("chat_scope_changed", "The research scope changed. Start a new chat to keep its evidence separate.", 409)
            if not chat.lock.acquire(blocking=False):
                raise MemoryError("chat_busy", "A question is already being answered in this chat. Please wait and retry.", 409)
            chat.scope = scope
            chat.touched = self.clock()
            self._chats.move_to_end(key)
        try:
            yield chat
        finally:
            chat.lock.release()

    def append(self, chat: Chat, turn: Turn):
        with self._lock:
            self._expire()
            if self._chats.get(chat.id) is not chat:
                raise MemoryError("chat_expired", "This chat was cleared or expired while answering. Start a new chat.")
            chat.turns.append(deepcopy(turn))
            chat.touched = self.clock()


# Format instructions are not legal-search terms. Resolve them before retrieval.
_SOURCE_ONLY = re.compile(
    r"\b(?:only|solely|exclusively|just)\b[\s\S]{0,180}\b(?:retrieved|previous|earlier|above|already|those|these|same)\b"
    r"|\b(?:retrieved|previous|earlier|above|already|those|these|same)\b[\s\S]{0,180}\b(?:only|solely|exclusively)\b"
    r"|\b(?:do not|don.t|without)\s+(?:retrieve|search|fetch|add|use)\s+(?:any\s+)?(?:new|additional|more)\s+(?:sources|evidence)\b",
    re.I,
)
_REFERENCE = re.compile(
    r"\b(?:previous|earlier|original|last|first)\s+(?:question|answer|response|sources?|case)\b"
    r"|\b(?:above|same chat|you retrieved|you (?:said|mentioned)|those sources|these sources|my case|my product|this product|that formulation)\b"
    r"|\b(?:your|this|that|the)\s+(?:answer|response|table|conclusion)\b"
    r"|^\s*(?:and |also |what about |how about |now |then |instead |continue\b|expand\b|summari[sz]e\b|shorten\b|make (?:it|that|a table)|put (?:it|that)|turn (?:it|that)|explain (?:it|that)|reformat\b)"
    r"|\b(?:it|that|this)\s+(?:apply|applies|mean|means|require|requires|qualify|qualifies|change|affect|matter)\b"
    r"|^\s*(?:why\??$|explain more|what (?:should|do) I do next|what if|suppose|assuming|correction|actually|we are|my company is)\b",
    re.I,
)


def source_only(query: str) -> bool:
    if _SOURCE_ONLY.search(query):
        return True
    # 'Use the same sources' is a source boundary even without the word only.
    # An explicit request to find additional sources instead permits retrieval.
    same = re.search(r"\b(?:use|using|based on|from)\s+(?:the\s+)?(?:same|previous|earlier|above|those|these)\s+(?:sources|evidence)\b", query, re.I)
    expand = re.search(r"\b(?:add|find|retrieve|search for)\s+(?:any\s+)?(?:new|more|additional)\s+(?:sources|evidence)\b", query, re.I)
    return bool(same and not expand)


def refers_back(query: str) -> bool:
    return source_only(query) or replaces_case(query) or bool(_REFERENCE.search(query))


def needs_history(query: str) -> bool:
    """Distinguish unresolved references from standalone 'my product' questions."""
    return source_only(query) or bool(re.search(
        r"\b(?:previous|earlier|original|last|first)\s+(?:question|answer|response|sources?)\b"
        r"|\b(?:you retrieved|you (?:said|mentioned)|above answer)\b"
        r"|\b(?:your|this|that)\s+(?:answer|response|table|conclusion)\b"
        r"|^\s*(?:(?:summari[sz]e|shorten|reformat|expand)\s+(?:it|that|this)|make (?:it|that)|put (?:it|that)|turn (?:it|that))\b",
        query, re.I))


def context_for(turns, query: str) -> Turn | None:
    if not turns or starts_new_case(query) or not refers_back(query):
        return None
    # Every retained continuation includes the original question for its topic,
    # while an independent new question starts a fresh context chain.
    return turns[-1]
