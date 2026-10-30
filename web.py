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
from free_translation import compare_free, FreeTranslationError
from skill_router import ROOT


class CompareInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str = Field(min_length=1, max_length=10000)
    source: Literal["zh", "ja", "en"]
    pair: Literal["zh-ja", "zh-en", "en-ja"]
    model: str = Field(default="", max_length=120, pattern=r"^[a-zA-Z0-9._:/-]*$")
    api_key: SecretStr = Field(default=SecretStr(""), max_length=512)


def error_message(exc: Exception) -> tuple[int, str]:
    # AnyIO 可能将 SDK 错误包在 ExceptionGroup 中；从不回显请求或密钥。
    if isinstance(exc, BaseExceptionGroup):
        return error_message(exc.exceptions[0])
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
