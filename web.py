"""本地独立网页入口：python web.py。只绑定本机，不存储 API Key。"""
import asyncio
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, SecretStr, ValidationError
from starlette.applications import Starlette
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import FileResponse, JSONResponse
from starlette.routing import Route, Mount
from starlette.staticfiles import StaticFiles

from comparison import compare
from skill_router import ROOT


class CompareInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str = Field(min_length=1, max_length=10000)
    source: Literal["zh", "ja", "en"]
    pair: Literal["zh-ja", "zh-en", "en-ja"]
    model: str = Field(min_length=1, max_length=120, pattern=r"^[a-zA-Z0-9._:/-]+$")
    api_key: SecretStr = Field(min_length=1, max_length=512)


def error_message(exc: Exception) -> tuple[int, str]:
    # AnyIO 可能将 SDK 错误包在 ExceptionGroup 中；从不回显请求或密钥。
    if isinstance(exc, BaseExceptionGroup):
        return error_message(exc.exceptions[0])
    status = getattr(exc, "status_code", None)
    if status in (401, 403):
        return 401, "API Key 无效或没有模型访问权限，请检查后重试。"
    if status == 429:
        return 429, "API 额度不足或请求过于频繁，请稍后重试。"
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
        if not data.text.strip() or not data.api_key.get_secret_value().strip():
            raise ValueError("empty input")
    except (ValidationError, ValueError):
        return JSONResponse({"error": "请检查原文、语言、模型与 API Key；原文限 10000 字符。"}, status_code=422)
    try:
        # 每个请求独立持有 key/client/session，不修改环境变量或共享凭据。
        result = await asyncio.wait_for(compare(
            data.text, data.source, data.pair, data.model,
            data.api_key.get_secret_value().strip(),
        ), timeout=180)
        return JSONResponse(result)
    except Exception as exc:
        status, message = error_message(exc)
        return JSONResponse({"error": message}, status_code=status)


app = Starlette(routes=[Route("/", index), Route("/api/compare", compare_endpoint, methods=["POST"]),
                        Mount("/static", StaticFiles(directory=ROOT / "static"), name="static")])
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["localhost", "127.0.0.1", "testserver"])


async def response_headers(request, call_next):
    response = await call_next(request)
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
    parser = argparse.ArgumentParser(description="中日英对照工作台")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    print(f"打开浏览器：http://127.0.0.1:{args.port}（Ctrl+C 停止）")
    uvicorn.run(app, host="127.0.0.1", port=args.port, access_log=False)
