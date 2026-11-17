"""Durable Run storage: a thread-safe wrapper around the SQLite checkpointer.

LangGraph's `SqliteSaver` is single-threaded by design. The API polls the
Checkpoint from request threads while the pipeline executes in background
worker threads, so all checkpointer access is serialized behind a reentrant
lock around one shared connection — concurrent access otherwise crashes the
interpreter (access violation inside the sqlite3 C extension).
"""

from __future__ import annotations

import sqlite3
import threading

from langgraph.checkpoint.sqlite import SqliteSaver


class ThreadSafeSqliteSaver(SqliteSaver):
    """`SqliteSaver` with every operation serialized behind one lock."""

    def __init__(self, connection: sqlite3.Connection):
        super().__init__(connection)
        # Reentrant: overridden methods call each other via `self.cursor()`.
        self._lock = threading.RLock()

    def setup(self, *args, **kwargs):
        with self._lock:
            return super().setup(*args, **kwargs)

    def get_tuple(self, *args, **kwargs):
        with self._lock:
            return super().get_tuple(*args, **kwargs)

    def list(self, *args, **kwargs):
        with self._lock:
            return super().list(*args, **kwargs)

    def put(self, *args, **kwargs):
        with self._lock:
            return super().put(*args, **kwargs)

    def put_writes(self, *args, **kwargs):
        with self._lock:
            return super().put_writes(*args, **kwargs)

    def delete_thread(self, *args, **kwargs):
        with self._lock:
            return super().delete_thread(*args, **kwargs)

    def cursor(self, *args, **kwargs):
        with self._lock:
            return super().cursor(*args, **kwargs)
