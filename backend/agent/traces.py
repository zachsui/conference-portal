"""In-memory ring-buffer for agent conversation traces."""
from __future__ import annotations

import threading
import uuid
from collections import deque
from datetime import datetime, timezone
from typing import Deque, Dict, List, Optional


class TraceStore:
    def __init__(self, max_traces: int = 200) -> None:
        self._lock = threading.Lock()
        self._max = max_traces
        self._order: Deque[str] = deque()
        self._traces: Dict[str, dict] = {}

    @staticmethod
    def new_trace_id() -> str:
        return f"trace_{uuid.uuid4().hex[:12]}"

    def save(self, trace_id: str, payload: dict) -> None:
        with self._lock:
            payload = dict(payload)
            payload.setdefault(
                "created_at", datetime.now(timezone.utc).isoformat()
            )
            self._traces[trace_id] = payload
            self._order.append(trace_id)
            while len(self._order) > self._max:
                old = self._order.popleft()
                self._traces.pop(old, None)

    def get(self, trace_id: str) -> Optional[dict]:
        with self._lock:
            return self._traces.get(trace_id)

    def list(self) -> List[dict]:
        """Return most-recent-first."""
        with self._lock:
            return [self._traces[tid] for tid in reversed(self._order)]


trace_store = TraceStore()
