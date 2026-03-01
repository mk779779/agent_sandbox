import json
import os
import re
import sqlite3
import threading
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from litellm import completion
from pydantic import BaseModel, Field


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_json_loads(value: str | None) -> dict[str, Any]:
    if not value:
        return {}
    try:
        loaded = json.loads(value)
        if isinstance(loaded, dict):
            return loaded
        return {"value": loaded}
    except json.JSONDecodeError:
        return {"raw": value}


class Database:
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        self._lock = threading.Lock()
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._init_schema()

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _init_schema(self) -> None:
        with self.connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                  id TEXT PRIMARY KEY,
                  app_name TEXT NOT NULL,
                  user_id TEXT,
                  status TEXT NOT NULL DEFAULT 'active',
                  title TEXT,
                  created_at TEXT NOT NULL,
                  updated_at TEXT NOT NULL,
                  last_event_seq INTEGER NOT NULL DEFAULT 0,
                  metadata_json TEXT
                );

                CREATE TABLE IF NOT EXISTS events (
                  id TEXT PRIMARY KEY,
                  session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
                  seq INTEGER NOT NULL,
                  event_type TEXT NOT NULL,
                  role TEXT,
                  timestamp TEXT NOT NULL,
                  payload_json TEXT NOT NULL,
                  request_id TEXT,
                  tool_name TEXT,
                  tool_call_id TEXT,
                  error_code TEXT,
                  UNIQUE(session_id, seq)
                );

                CREATE INDEX IF NOT EXISTS idx_sessions_user_updated
                  ON sessions(user_id, updated_at DESC);
                CREATE INDEX IF NOT EXISTS idx_sessions_status_updated
                  ON sessions(status, updated_at DESC);
                CREATE INDEX IF NOT EXISTS idx_events_session_seq
                  ON events(session_id, seq);
                CREATE INDEX IF NOT EXISTS idx_events_session_timestamp
                  ON events(session_id, timestamp);
                CREATE INDEX IF NOT EXISTS idx_events_type_timestamp
                  ON events(event_type, timestamp);
                CREATE INDEX IF NOT EXISTS idx_events_request
                  ON events(session_id, request_id, event_type);
                """
            )


@dataclass
class Session:
    id: str
    app_name: str
    user_id: str | None
    status: str
    created_at: str
    updated_at: str
    last_event_seq: int


class SessionStore:
    def __init__(self, db: Database, app_name: str) -> None:
        self.db = db
        self.app_name = app_name

    def create_session(self, user_id: str | None = None, title: str | None = None) -> Session:
        now = utc_now_iso()
        session_id = str(uuid.uuid4())
        with self.db.connect() as conn:
            conn.execute(
                """
                INSERT INTO sessions (
                  id, app_name, user_id, status, title, created_at, updated_at, last_event_seq, metadata_json
                ) VALUES (?, ?, ?, 'active', ?, ?, ?, 0, NULL)
                """,
                (session_id, self.app_name, user_id, title, now, now),
            )
        return Session(
            id=session_id,
            app_name=self.app_name,
            user_id=user_id,
            status="active",
            created_at=now,
            updated_at=now,
            last_event_seq=0,
        )

    def get_session(self, session_id: str) -> Session | None:
        with self.db.connect() as conn:
            row = conn.execute(
                """
                SELECT id, app_name, user_id, status, created_at, updated_at, last_event_seq
                FROM sessions
                WHERE id = ? AND app_name = ?
                """,
                (session_id, self.app_name),
            ).fetchone()
        if not row:
            return None
        return Session(
            id=row["id"],
            app_name=row["app_name"],
            user_id=row["user_id"],
            status=row["status"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            last_event_seq=int(row["last_event_seq"]),
        )


class EventStore:
    def __init__(self, db: Database, app_name: str) -> None:
        self.db = db
        self.app_name = app_name

    def append_event(
        self,
        session_id: str,
        event_type: str,
        role: str | None,
        payload: dict[str, Any],
        request_id: str | None = None,
        tool_name: str | None = None,
        tool_call_id: str | None = None,
        error_code: str | None = None,
    ) -> dict[str, Any]:
        with self.db._lock:
            with self.db.connect() as conn:
                conn.execute("BEGIN IMMEDIATE")
                row = conn.execute(
                    "SELECT last_event_seq FROM sessions WHERE id = ? AND app_name = ?",
                    (session_id, self.app_name),
                ).fetchone()
                if not row:
                    conn.execute("ROLLBACK")
                    raise ValueError(f"Session not found: {session_id}")
                next_seq = int(row["last_event_seq"]) + 1
                now = utc_now_iso()
                event_id = str(uuid.uuid4())
                conn.execute(
                    """
                    INSERT INTO events (
                      id, session_id, seq, event_type, role, timestamp, payload_json,
                      request_id, tool_name, tool_call_id, error_code
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        event_id,
                        session_id,
                        next_seq,
                        event_type,
                        role,
                        now,
                        json.dumps(payload, default=str),
                        request_id,
                        tool_name,
                        tool_call_id,
                        error_code,
                    ),
                )
                conn.execute(
                    "UPDATE sessions SET updated_at = ?, last_event_seq = ? WHERE id = ?",
                    (now, next_seq, session_id),
                )
                conn.execute("COMMIT")
                return {
                    "id": event_id,
                    "session_id": session_id,
                    "seq": next_seq,
                    "event_type": event_type,
                    "role": role,
                    "timestamp": now,
                    "payload": payload,
                }

    def list_events(self, session_id: str, after_seq: int | None = None, limit: int = 200) -> list[dict[str, Any]]:
        params: list[Any] = [session_id]
        condition = ""
        if after_seq is not None:
            condition = "AND seq > ?"
            params.append(after_seq)
        params.append(limit)
        with self.db.connect() as conn:
            rows = conn.execute(
                f"""
                SELECT id, session_id, seq, event_type, role, timestamp, payload_json, request_id, tool_name, tool_call_id, error_code
                FROM events
                WHERE session_id = ? {condition}
                ORDER BY seq ASC
                LIMIT ?
                """,
                tuple(params),
            ).fetchall()
        return [
            {
                "id": row["id"],
                "session_id": row["session_id"],
                "seq": row["seq"],
                "event_type": row["event_type"],
                "role": row["role"],
                "timestamp": row["timestamp"],
                "payload": _safe_json_loads(row["payload_json"]),
                "request_id": row["request_id"],
                "tool_name": row["tool_name"],
                "tool_call_id": row["tool_call_id"],
                "error_code": row["error_code"],
            }
            for row in rows
        ]

    def get_turn_result(self, session_id: str, request_id: str) -> dict[str, Any] | None:
        with self.db.connect() as conn:
            row = conn.execute(
                """
                SELECT payload_json
                FROM events
                WHERE session_id = ?
                  AND request_id = ?
                  AND event_type = 'turn.completed'
                ORDER BY seq DESC
                LIMIT 1
                """,
                (session_id, request_id),
            ).fetchone()
        if not row:
            return None
        return _safe_json_loads(row["payload_json"])


def tool_get_time_utc() -> dict[str, str]:
    return {"utc_time": utc_now_iso()}


def tool_sleep_ms(ms: int = 0) -> dict[str, Any]:
    bounded_ms = max(0, min(ms, 2000))
    start = time.time()
    time.sleep(bounded_ms / 1000.0)
    elapsed = int((time.time() - start) * 1000)
    return {"slept_ms": elapsed}


TOOL_REGISTRY: dict[str, Any] = {
    "get_time_utc": tool_get_time_utc,
    "sleep_ms": tool_sleep_ms,
}

MODEL_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_time_utc",
            "description": "Get the current UTC timestamp.",
            "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "sleep_ms",
            "description": "Sleep for up to 2000 milliseconds.",
            "parameters": {
                "type": "object",
                "properties": {"ms": {"type": "integer", "minimum": 0, "maximum": 2000}},
                "required": ["ms"],
                "additionalProperties": False,
            },
        },
    },
]


class ChatOrchestrator:
    def __init__(
        self,
        session_store: SessionStore,
        event_store: EventStore,
        model: str,
    ) -> None:
        self.session_store = session_store
        self.event_store = event_store
        self.model = model

    def _resolve_session(self, session_id: str | None, user_id: str | None) -> tuple[Session, bool]:
        if not session_id:
            created = self.session_store.create_session(user_id=user_id)
            return created, True
        session = self.session_store.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail=f"session_id not found: {session_id}")
        if session.status != "active":
            raise HTTPException(status_code=409, detail=f"session is not active: {session.status}")
        return session, False

    def handle_turn(
        self,
        prompt: str,
        session_id: str | None = None,
        user_id: str | None = None,
        request_id: str | None = None,
    ) -> dict[str, Any]:
        session, is_new_session = self._resolve_session(session_id=session_id, user_id=user_id)
        event_ids: list[str] = []

        if request_id and not is_new_session:
            existing = self.event_store.get_turn_result(session.id, request_id)
            if existing:
                return {
                    "session_id": session.id,
                    "assistant_text": existing.get("assistant_text", ""),
                    "event_ids": [],
                    "turn_status": "ok",
                    "deduplicated": True,
                }

        if is_new_session:
            e = self.event_store.append_event(
                session_id=session.id,
                event_type="session.created",
                role="system",
                payload={"user_id": user_id},
                request_id=request_id,
            )
            event_ids.append(e["id"])

        e = self.event_store.append_event(
            session_id=session.id,
            event_type="user.prompt.received",
            role="user",
            payload={"text": prompt},
            request_id=request_id,
        )
        event_ids.append(e["id"])

        self.event_store.append_event(
            session_id=session.id,
            event_type="model.response.started",
            role="assistant",
            payload={"model": self.model},
            request_id=request_id,
        )

        messages: list[dict[str, Any]] = [{"role": "user", "content": prompt}]
        max_loops = 8
        assistant_text = ""

        try:
            for _ in range(max_loops):
                try:
                    resp = completion(model=self.model, messages=messages, tools=MODEL_TOOLS, tool_choice="auto")
                except Exception as model_error:
                    assistant_text = self._offline_fallback_response(
                        prompt=prompt,
                        session_id=session.id,
                        request_id=request_id,
                        model_error=model_error,
                    )
                    self.event_store.append_event(
                        session_id=session.id,
                        event_type="model.response.completed",
                        role="assistant",
                        payload={
                            "text": assistant_text,
                            "fallback": True,
                            "fallback_reason": str(model_error),
                        },
                        request_id=request_id,
                    )
                    done = self.event_store.append_event(
                        session_id=session.id,
                        event_type="turn.completed",
                        role="system",
                        payload={"assistant_text": assistant_text, "fallback": True},
                        request_id=request_id,
                    )
                    event_ids.append(done["id"])
                    return {
                        "session_id": session.id,
                        "assistant_text": assistant_text,
                        "event_ids": event_ids,
                        "turn_status": "ok",
                    }
                choice = resp.choices[0].message
                tool_calls = getattr(choice, "tool_calls", None) or []
                content = getattr(choice, "content", "") or ""

                if tool_calls:
                    messages.append(
                        {
                            "role": "assistant",
                            "content": content or "",
                            "tool_calls": [tc.model_dump() if hasattr(tc, "model_dump") else tc for tc in tool_calls],
                        }
                    )
                    for call in tool_calls:
                        call_id = getattr(call, "id", None) or str(uuid.uuid4())
                        function = getattr(call, "function", None)
                        tool_name = getattr(function, "name", None) if function else None
                        raw_args = getattr(function, "arguments", "{}") if function else "{}"
                        args = _safe_json_loads(raw_args)

                        self.event_store.append_event(
                            session_id=session.id,
                            event_type="tool.call.started",
                            role="tool",
                            payload={"name": tool_name, "args": args},
                            request_id=request_id,
                            tool_name=tool_name,
                            tool_call_id=call_id,
                        )

                        tool_start = time.time()
                        try:
                            if tool_name not in TOOL_REGISTRY:
                                raise ValueError(f"Unknown tool: {tool_name}")
                            tool_result = TOOL_REGISTRY[tool_name](**args)
                            latency_ms = int((time.time() - tool_start) * 1000)
                            self.event_store.append_event(
                                session_id=session.id,
                                event_type="tool.call.completed",
                                role="tool",
                                payload={
                                    "name": tool_name,
                                    "args": args,
                                    "result": tool_result,
                                    "latency_ms": latency_ms,
                                },
                                request_id=request_id,
                                tool_name=tool_name,
                                tool_call_id=call_id,
                            )
                            messages.append(
                                {
                                    "role": "tool",
                                    "tool_call_id": call_id,
                                    "name": tool_name,
                                    "content": json.dumps(tool_result),
                                }
                            )
                        except Exception as tool_error:
                            self.event_store.append_event(
                                session_id=session.id,
                                event_type="tool.call.failed",
                                role="tool",
                                payload={"name": tool_name, "args": args, "error": str(tool_error)},
                                request_id=request_id,
                                tool_name=tool_name,
                                tool_call_id=call_id,
                                error_code="TOOL_EXECUTION_ERROR",
                            )
                            raise
                    continue

                assistant_text = content
                self.event_store.append_event(
                    session_id=session.id,
                    event_type="model.response.completed",
                    role="assistant",
                    payload={"text": assistant_text, "usage": getattr(resp, "usage", None)},
                    request_id=request_id,
                )
                done = self.event_store.append_event(
                    session_id=session.id,
                    event_type="turn.completed",
                    role="system",
                    payload={"assistant_text": assistant_text},
                    request_id=request_id,
                )
                event_ids.append(done["id"])
                return {
                    "session_id": session.id,
                    "assistant_text": assistant_text,
                    "event_ids": event_ids,
                    "turn_status": "ok",
                }

            raise RuntimeError("Exceeded tool/model loop limit")

        except Exception as exc:
            fail = self.event_store.append_event(
                session_id=session.id,
                event_type="turn.failed",
                role="system",
                payload={"error": str(exc)},
                request_id=request_id,
                error_code="TURN_FAILED",
            )
            event_ids.append(fail["id"])
            raise HTTPException(
                status_code=500,
                detail={
                    "session_id": session.id,
                    "turn_status": "failed",
                    "error": str(exc),
                },
            )

    def _run_tool_with_events(
        self, session_id: str, request_id: str | None, tool_name: str, args: dict[str, Any]
    ) -> dict[str, Any]:
        tool_call_id = str(uuid.uuid4())
        self.event_store.append_event(
            session_id=session_id,
            event_type="tool.call.started",
            role="tool",
            payload={"name": tool_name, "args": args},
            request_id=request_id,
            tool_name=tool_name,
            tool_call_id=tool_call_id,
        )
        start = time.time()
        try:
            if tool_name not in TOOL_REGISTRY:
                raise ValueError(f"Unknown tool: {tool_name}")
            result = TOOL_REGISTRY[tool_name](**args)
            latency_ms = int((time.time() - start) * 1000)
            self.event_store.append_event(
                session_id=session_id,
                event_type="tool.call.completed",
                role="tool",
                payload={"name": tool_name, "args": args, "result": result, "latency_ms": latency_ms},
                request_id=request_id,
                tool_name=tool_name,
                tool_call_id=tool_call_id,
            )
            return result
        except Exception as exc:
            self.event_store.append_event(
                session_id=session_id,
                event_type="tool.call.failed",
                role="tool",
                payload={"name": tool_name, "args": args, "error": str(exc)},
                request_id=request_id,
                tool_name=tool_name,
                tool_call_id=tool_call_id,
                error_code="TOOL_EXECUTION_ERROR",
            )
            raise

    def _offline_fallback_response(
        self, prompt: str, session_id: str, request_id: str | None, model_error: Exception
    ) -> str:
        prompt_l = prompt.lower()
        parts: list[str] = [f"Model unavailable ({model_error}). Returned fallback response."]
        used_tool = False

        if "utc" in prompt_l or "time" in prompt_l:
            out = self._run_tool_with_events(session_id, request_id, "get_time_utc", {})
            parts.append(f"Current UTC time: {out['utc_time']}")
            used_tool = True

        sleep_match = re.search(r"(\\d{1,4})\\s*ms", prompt_l)
        if "sleep" in prompt_l and sleep_match:
            ms = int(sleep_match.group(1))
            out = self._run_tool_with_events(session_id, request_id, "sleep_ms", {"ms": ms})
            parts.append(f"Slept for {out['slept_ms']} ms.")
            used_tool = True

        if not used_tool:
            parts.append("No offline tool action matched your prompt.")

        return " ".join(parts)


class ChatRequest(BaseModel):
    prompt: str = Field(min_length=1)
    session_id: str | None = None
    user_id: str | None = None
    request_id: str | None = None


class ChatResponse(BaseModel):
    session_id: str
    assistant_text: str
    event_ids: list[str]
    turn_status: str
    deduplicated: bool = False


DEFAULT_DB_PATH = os.getenv("APP_DB_PATH", ".adk/session_events.db")
DEFAULT_MODEL = os.getenv("CHAT_MODEL", "openai/gpt-4o-mini")
APP_NAME = os.getenv("APP_NAME", "agent_sandbox_chat")

db = Database(DEFAULT_DB_PATH)
session_store = SessionStore(db=db, app_name=APP_NAME)
event_store = EventStore(db=db, app_name=APP_NAME)
orchestrator = ChatOrchestrator(session_store=session_store, event_store=event_store, model=DEFAULT_MODEL)

app = FastAPI(title="Session Event Chat API", version="0.1.0")


@app.post("/chat", response_model=ChatResponse)
async def chat(request: Request) -> ChatResponse:
    try:
        raw_body = await request.body()
        payload = json.loads(raw_body.decode("utf-8"), strict=False)
        req = ChatRequest.model_validate(payload)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=422, detail=f"Invalid JSON body: {exc.msg}") from exc
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Invalid request body: {exc}") from exc

    result = orchestrator.handle_turn(
        prompt=req.prompt,
        session_id=req.session_id,
        user_id=req.user_id,
        request_id=req.request_id,
    )
    return ChatResponse(**result)


@app.get("/sessions/{session_id}/events")
def list_session_events(session_id: str, after_seq: int | None = None, limit: int = 200) -> dict[str, Any]:
    session = session_store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="session_id not found")
    events = event_store.list_events(session_id=session_id, after_seq=after_seq, limit=min(max(limit, 1), 1000))
    return {"session_id": session_id, "events": events}
