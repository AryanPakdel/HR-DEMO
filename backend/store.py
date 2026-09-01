"""نگهداری نشست‌های داده در حافظه فرآیند."""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field

import pandas as pd

SESSION_TTL_SECONDS = 2 * 60 * 60  # دو ساعت
MAX_SESSIONS = 24


@dataclass
class Session:
    id: str
    df: pd.DataFrame
    summary: dict
    created_at: float = field(default_factory=time.time)
    touched_at: float = field(default_factory=time.time)
    # کش مدل پیش‌بینی تا در هر درخواست دوباره آموزش نبیند
    cache: dict = field(default_factory=dict)


class SessionStore:
    def __init__(self) -> None:
        self._sessions: dict[str, Session] = {}
        self._lock = threading.Lock()

    def create(self, df: pd.DataFrame, summary: dict) -> Session:
        session = Session(id=uuid.uuid4().hex, df=df, summary=summary)
        with self._lock:
            self._prune_locked()
            if len(self._sessions) >= MAX_SESSIONS:
                oldest = min(self._sessions.values(), key=lambda s: s.touched_at)
                self._sessions.pop(oldest.id, None)
            self._sessions[session.id] = session
        return session

    def get(self, session_id: str | None) -> Session | None:
        if not session_id:
            return None
        with self._lock:
            self._prune_locked()
            session = self._sessions.get(session_id)
            if session is not None:
                session.touched_at = time.time()
            return session

    def _prune_locked(self) -> None:
        cutoff = time.time() - SESSION_TTL_SECONDS
        for sid in [s.id for s in self._sessions.values() if s.touched_at < cutoff]:
            self._sessions.pop(sid, None)


store = SessionStore()
