"""CLI 入口：python main.py --help。"""
import argparse
import asyncio
import os
import sys

from dotenv import load_dotenv
from agent import TranslationRequest, translate
from skill_router import ROOT


def main() -> int:
    parser = argparse.ArgumentParser(description="中日英翻译 Agent + Skills + MCP")
    parser.add_argument("--text", required=True, help="待翻译原文")
    parser.add_argument("--source", required=True, choices=["zh", "ja", "en"])
    parser.add_argument("--target", required=True, choices=["zh", "ja", "en"])
    parser.add_argument("--explain", default="zh", choices=["zh", "ja", "en"])
    parser.add_argument("--demo", action="store_true", help="真实 MCP 查询；不调用模型、不生成翻译")
    parser.add_argument("--verbose", action="store_true", help="在 stderr 显示 Skill、工具调用及结果")
    args = parser.parse_args()
    load_dotenv(ROOT / ".env")  # 系统环境变量优先；不依赖当前工作目录。
    request = TranslationRequest(args.text, args.source, args.target, args.explain)
    try:
        result = asyncio.run(translate(
            request, demo=args.demo, verbose=args.verbose,
            api_key=os.getenv("OPENAI_API_KEY"), model=os.getenv("OPENAI_MODEL"),
        ))
    except Exception as exc:
        # 不输出整个 SDK 响应，避免错误信息过度暴露请求内容。
        if isinstance(exc, (ValueError, RuntimeError)):
            message = str(exc)
        else:
            message = f"{type(exc).__name__}；请检查依赖、网络、API 密钥及模型权限。"
        print(f"错误：{message}", file=sys.stderr)
        return 1
    print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
