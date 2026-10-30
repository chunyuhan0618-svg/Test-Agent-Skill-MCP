"""真实异步检查点。无调试上下文时直接返回，不改变普通调用方式。"""
import asyncio
import inspect
import secrets
import time
from contextvars import ContextVar
from pathlib import Path

from skill_router import ROOT

CURRENT = ContextVar("translation_debug_session", default=None)
PAUSE_SECONDS = 300


class DebugPauseTimeout(TimeoutError):
    pass


def code_location(frame) -> dict:
    """定位检查点下一条实际代码；不读取局部变量或密钥。"""
    path = Path(frame.f_code.co_filename).resolve()
    relative = path.relative_to(ROOT).as_posix()
    lines = path.read_text(encoding="utf-8").splitlines()
    line = frame.f_lineno + 1
    while line <= len(lines) and (not lines[line-1].strip() or lines[line-1].lstrip().startswith("#")):
        line += 1
    line = min(line, len(lines))
    start, end = max(1, line-2), min(len(lines), line+5)
    return {"file": relative, "line": line,
            "code": [{"number": n, "text": lines[n-1]} for n in range(start, end+1)]}


async def step(kind: str, title: str, detail: str = "", resource: str | None = None):
    session = CURRENT.get()
    if session is None:
        return
    frame = inspect.currentframe().f_back
    try:
        location = code_location(frame)
    finally:
        del frame
    if resource:
        path = (ROOT / resource).resolve()
        if path.is_relative_to(ROOT / "skills") and path.name == "SKILL.md":
            location["resource"] = {"file": resource, "text": path.read_text(encoding="utf-8")}
    await session.checkpoint(kind, title, detail, location)


class DebugSession:
    def __init__(self):
        self.id = secrets.token_urlsafe(24)
        self.status = "running"
        self.pair = ""
        self.events = []
        self.results = {}
        self.errors = {}
        self.error = ""
        self.gate = None
        self.task = None
        self.updated = time.monotonic()
        self.run_to_end = False

    async def checkpoint(self, kind, title, detail, location):
        if self.events and self.events[-1]["status"] == "running":
            self.events[-1]["status"] = "completed"
        event = {"seq": len(self.events)+1, "kind":kind, "title":title,
                 "detail":detail, "pair":self.pair, "status":"paused", **location}
        self.events.append(event)
        if self.run_to_end:
            self.status = event["status"] = "running"
            self.updated = time.monotonic()
            # 保留真实流程记录，并让出调度机会，使取消请求仍可处理。
            await asyncio.sleep(0)
            return
        self.status = "paused"
        self.updated = time.monotonic()
        self.gate = asyncio.Event()
        try:
            await asyncio.wait_for(self.gate.wait(), timeout=PAUSE_SECONDS)
        except TimeoutError:
            raise DebugPauseTimeout("调试暂停超过 5 分钟，会话已结束，请重新开始。") from None
        event["status"] = "running"

    def advance(self, seq):
        # 同一序号只允许放行一次；双击不能预存下一步的许可。
        if self.status != "paused" or not self.events or self.events[-1]["seq"] != seq:
            return False
        self.status = "running"
        self.events[-1]["status"] = "running"
        self.updated = time.monotonic()
        self.gate.set()
        return True

    def snapshot(self):
        return {"id": self.id, "status":self.status, "pair":self.pair,
                "events":self.events, "results":self.results,
                "errors":self.errors, "error":self.error, "run_to_end":self.run_to_end}

    def continue_to_end(self):
        if self.status not in ("paused", "running"):
            return False
        self.run_to_end = True
        if self.status == "paused":
            self.advance(self.events[-1]["seq"])
        return True

    def finish(self, status="completed", error=""):
        self.status, self.error = status, error
        if self.events and self.events[-1]["status"] in ("running", "paused"):
            self.events[-1]["status"] = "completed" if status=="completed" else status
        self.updated = time.monotonic()


class DebugSessions:
    def __init__(self):
        self.items = {}

    def create(self):
        self.reap()
        # 优先回收已结束会话，避免正常重复试用 16 次后只能等待过期。
        if len(self.items) >= 16:
            for key, old in list(self.items.items()):
                if old.status in ("completed", "cancelled", "error"):
                    del self.items[key]
                    if len(self.items) < 16:
                        break
        if len(self.items) >= 16:
            raise ValueError("调试会话过多，请结束现有会话后重试。")
        session = DebugSession()
        self.items[session.id] = session
        return session

    def reap(self):
        now = time.monotonic()
        for key, session in list(self.items.items()):
            if now-session.updated > 900:
                if session.task and not session.task.done():
                    session.task.cancel()
                del self.items[key]

    async def close(self):
        tasks = [s.task for s in self.items.values() if s.task and not s.task.done()]
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        self.items.clear()
