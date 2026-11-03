"""English: Start the local web Agent with python web.py. Serve static assets and validated APIs, protect credentials, and manage actual debug tasks. Display language is request-scoped.
日本語：python web.py でローカル Web Agent を起動します。静的画面と検証済み API を提供し、キーを保護し、実際のデバッグタスクを管理します。表示言語は要求単位です。
中文：用 python web.py 启动本地网页 Agent，提供静态资源和校验后的 API，保护凭据并管理真实调试任务；界面语言按请求隔离。
"""
import asyncio
from contextlib import asynccontextmanager
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, SecretStr, ValidationError
from starlette.applications import Starlette
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import FileResponse, JSONResponse
from starlette.routing import Route, Mount
from starlette.staticfiles import StaticFiles

from ui_locale import UI_LANGUAGE
from comparison import compare
from free_translation import compare_free, FreeTranslationError
from skill_router import ROOT
from debug_trace import CURRENT, DebugSessions, DebugPauseTimeout, step

debug_sessions = DebugSessions()


def is_pause_timeout(exc):
    return isinstance(exc, DebugPauseTimeout) or (isinstance(exc, BaseExceptionGroup)
        and any(is_pause_timeout(child) for child in exc.exceptions))


class CompareInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str = Field(min_length=1, max_length=10000)
    source: Literal["zh", "ja", "en"]
    pair: Literal["zh-ja", "zh-en", "en-ja"]
    model: str = Field(default="", max_length=120, pattern=r"^[a-zA-Z0-9._:/-]*$")
    api_key: SecretStr = Field(default=SecretStr(""), max_length=512)


class DebugInput(CompareInput):
    pair: Literal["zh-ja", "zh-en", "en-ja"] = "zh-ja"
    pairs: list[Literal["zh-ja", "zh-en", "en-ja"]] = Field(min_length=1, max_length=3)


def error_message(exc: Exception) -> tuple[int, str]:
    # AnyIO 可能将 SDK 错误包在 ExceptionGroup 中；从不回显请求或密钥。
    if isinstance(exc, BaseExceptionGroup):
        return error_message(exc.exceptions[0])
    if isinstance(exc, DebugPauseTimeout):
        return 408, "调试暂停超过 5 分钟，会话已结束，请重新开始。"
    if isinstance(exc, FreeTranslationError):
        return 503, str(exc)
    status = getattr(exc, "status_code", None)
    if status in (401, 403):
        return 401, "API Key 无效或没有模型访问权限，请检查后重试。"
    if status == 429:
        # 429 同时用于余额/额度问题和速率限制；不能一律建议稍后重试。
        body = getattr(exc, "body", None)
        detail = body.get("error", body) if isinstance(body, dict) else {}
        if not isinstance(detail, dict):
            detail = {}
        codes = [getattr(exc, "code", None), getattr(exc, "type", None),
                 detail.get("code"), detail.get("type")]
        specific = {
            "credit_balance_exhausted": "API 预付余额已耗尽（credit_balance_exhausted）。请在 API 平台 Billing 检查并补充可用余额；重复请求不会恢复余额。",
            "organization_spend_limit_exceeded": "组织 API 消费上限已达到（organization_spend_limit_exceeded）。请联系组织管理员核对消费限制。",
            "project_spend_limit_exceeded": "当前项目 API 消费上限已达到（project_spend_limit_exceeded）。请在项目设置中核对消费限制。",
            "organization_usage_limit_exceeded": "组织 API 用量上限已达到（organization_usage_limit_exceeded）。请在 Limits 核对额度，必要时申请提高限制。",
        }
        for code in codes:
            if isinstance(code, str) and code in specific:
                return 429, specific[code]
        if any(code in ("insufficient_quota", "billing_hard_limit_reached") for code in codes):
            return 429, ("API 可用额度不足（insufficient_quota / billing limit）。"
                         "请在 OpenAI API 平台检查 Billing、余额、组织/项目及用量限制。"
                         "单纯等待或重复点击通常无法解决；创建 API Key 不代表已有可用额度。")
        if any(code in ("rate_limit_exceeded", "slow_down", "rate_limit_error") for code in codes):
            return 429, ("触发 API 速率限制（rate_limit_exceeded / slow_down）。"
                         "请稍后重试，先只勾选一组、缩短原文，并在 API 平台 Limits 查看限制。")
        return 429, ("OpenAI 返回 HTTP 429，但未提供可识别的错误代码。"
                     "请先检查 API 平台 Billing 和 Limits；若有可用额度，"
                     "稍后仅勾选一组重试。当前信息无法确定是额度不足还是速率限制。")
    if status in (400, 404):
        return 400, "模型不存在、不可用，或不支持当前工具调用及结构化输出。"
    if isinstance(exc, TimeoutError):
        return 504, "翻译超时，请缩短原文或稍后重试。"
    return 502, "翻译未完成，请检查网络、模型配置或稍后重试。"


async def index(request):
    return FileResponse(ROOT / "static/index.html")


async def compare_endpoint(request: Request):
    origin = request.headers.get("origin")
    if origin and origin != f"{request.url.scheme}://{request.url.netloc}":
        return JSONResponse({"error": "仅接受同源页面请求。"}, status_code=403)
    if request.headers.get("content-type", "").split(";")[0] != "application/json":
        return JSONResponse({"error": "请求必须为 JSON。"}, status_code=415)
    # 流式读取并限制请求大小，不将无限制正文读入内存。
    body = bytearray()
    async for chunk in request.stream():
        body.extend(chunk)
        if len(body) > 80000:
            return JSONResponse({"error": "请求内容过大。"}, status_code=413)
    try:
        data = CompareInput.model_validate_json(body)
        if not data.text.strip():
            raise ValueError("empty input")
    except (ValidationError, ValueError):
        return JSONResponse({"error": "请检查原文、语言、模型与 API Key；原文限 10000 字符。"}, status_code=422)
    try:
        # 每个请求独立持有 key/client/session，不修改环境变量或共享凭据。
        key = data.api_key.get_secret_value().strip()
        if data.model and key:
            operation = compare(data.text, data.source, data.pair, data.model, key)
        else:
            operation = compare_free(data.text, data.source, data.pair)
        result = await asyncio.wait_for(operation, timeout=180)
        return JSONResponse(result)
    except Exception as exc:
        status, message = error_message(exc)
        return JSONResponse({"error": message}, status_code=status)


async def run_debug(session, data):
    token = CURRENT.set(session)
    try:
        async with asyncio.timeout(1200):
            for pair in data.pairs:
                session.pair = pair
                try:
                    await step("Agent", "安排本组翻译", "Agent 编排程序按勾选顺序处理组合；此处选择免费或大模型执行路径。")
                    key = data.api_key.get_secret_value().strip()
                    if data.model and key:
                        result = await compare(data.text, data.source, pair, data.model, key)
                    else:
                        result = await compare_free(data.text, data.source, pair)
                    await step("Agent", "交付本组结果", "把本组的双语文本和说明交给网页；其他未勾选组合不运行。")
                    session.results[pair] = result
                except DebugPauseTimeout:
                    raise
                except Exception as exc:
                    if is_pause_timeout(exc):
                        raise
                    session.errors[pair] = error_message(exc)[1]
                    if session.events:
                        session.events[-1]["status"] = "error"
            session.finish("completed")
    except asyncio.CancelledError:
        session.finish("cancelled")
        raise
    except Exception as exc:
        session.finish("error", error_message(exc)[1])
    finally:
        CURRENT.reset(token)


async def debug_start(request):
    body = bytearray()
    async for chunk in request.stream():
        body.extend(chunk)
        if len(body)>80000:
            return JSONResponse({"error":"请求内容过大。"},status_code=413)
    try:
        data = DebugInput.model_validate_json(body)
        if not data.text.strip() or len(set(data.pairs))!=len(data.pairs):
            raise ValueError("invalid request")
        if not (data.model and data.api_key.get_secret_value().strip()) and len(data.text)>1000:
            return JSONResponse({"error":"免费模式每次最多 1000 字符。"},status_code=422)
        session = debug_sessions.create()
    except (ValueError, ValidationError):
        return JSONResponse({"error":"调试请求无效，或现有会话过多；请检查输入并结束旧会话。"},status_code=422)
    session.task = asyncio.create_task(run_debug(session, data))
    return JSONResponse({"id":session.id},status_code=201)


async def debug_control(request):
    debug_sessions.reap()
    session = debug_sessions.items.get(request.path_params["session_id"])
    if session is None:
        return JSONResponse({"error":"调试会话不存在或已过期，请重新开始。"},status_code=404)
    action = request.path_params.get("action", "status")
    if request.method == "GET" and action == "status":
        return JSONResponse(session.snapshot())
    if request.method == "POST" and action == "continue":
        if not session.continue_to_end():
            return JSONResponse({"error":"会话已结束，无法继续。"},status_code=409)
        return JSONResponse(session.snapshot())
    if request.method == "POST" and action == "cancel":
        if session.task and not session.task.done():
            session.task.cancel()
            await asyncio.gather(session.task, return_exceptions=True)
        session.finish("cancelled")
        return JSONResponse(session.snapshot())
    if request.method == "POST" and action == "next":
        # next 请求只需小整数，限制流式读取，避免无限大小的控制正文。
        body = bytearray()
        async for chunk in request.stream():
            body.extend(chunk)
            if len(body)>256:
                return JSONResponse({"error":"控制请求过大。"},status_code=413)
        try:
            import json
            seq = json.loads(body)["seq"]
            if type(seq) is not int:
                raise ValueError("invalid sequence")
        except (ValueError, KeyError, TypeError):
            return JSONResponse({"error":"步骤序号无效。"},status_code=422)
        if not session.advance(seq):
            return JSONResponse({"error":"该步骤已放行或尚未暂停，请等待最新状态。"},status_code=409)
        return JSONResponse(session.snapshot())
    return JSONResponse({"error":"未知调试操作。"},status_code=405)


@asynccontextmanager
async def lifespan(app):
    async def cleanup():
        while True:
            await asyncio.sleep(30)
            debug_sessions.reap()
    cleaner = asyncio.create_task(cleanup())
    try:
        yield
    finally:
        cleaner.cancel()
        await asyncio.gather(cleaner, return_exceptions=True)
        await debug_sessions.close()


app = Starlette(lifespan=lifespan, routes=[Route("/", index), Route("/api/compare", compare_endpoint, methods=["POST"]),
                        Route("/api/debug/start", debug_start, methods=["POST"]),
                        Route("/api/debug/{session_id}", debug_control, methods=["GET"]),
                        Route("/api/debug/{session_id}/{action}", debug_control, methods=["POST"]),
                        Mount("/static", StaticFiles(directory=ROOT / "static"), name="static")])
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["localhost", "127.0.0.1", "testserver"])


async def response_headers(request, call_next):
    if request.url.path.startswith("/api/debug/") and request.method == "POST":
        origin = request.headers.get("origin")
        if origin and origin != f"{request.url.scheme}://{request.url.netloc}":
            return JSONResponse({"error":"仅接受同源页面请求。"}, status_code=403)
        if request.headers.get("content-type", "").split(";")[0] != "application/json":
            return JSONResponse({"error":"请求必须为 JSON。"},status_code=415)
    language = request.headers.get("x-ui-language", "zh")
    token = UI_LANGUAGE.set(language if language in ("en", "ja", "zh") else "en")
    try:
        response = await call_next(request)
    finally:
        UI_LANGUAGE.reset(token)
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; script-src 'self'; style-src 'self'; "
        "connect-src 'self'; img-src 'self' data:; frame-ancestors 'none'; base-uri 'none'"
    )
    return response


app.add_middleware(BaseHTTPMiddleware, dispatch=response_headers)


if __name__ == "__main__":
    import argparse
    import uvicorn
    parser = argparse.ArgumentParser(description="Trilingual translation Agent")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    print(f"Open http://127.0.0.1:{args.port} in your browser. Stop: Ctrl+C")
    uvicorn.run(app, host="127.0.0.1", port=args.port, access_log=False)
