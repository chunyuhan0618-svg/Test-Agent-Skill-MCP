"""English: Own the local stdio MCP connection lifecycle, adapt tool schemas, and validate terminology tool requests and results.
日本語：ローカル stdio MCP 接続の開始・終了、ツール定義の変換、用語検索の要求と結果の検証を行います。
中文：管理本地 stdio MCP 连接生命周期、转换工具定义，并校验术语查询请求和结果。
"""
import asyncio
import json
import sys
from contextlib import asynccontextmanager
from datetime import timedelta

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from skill_router import ROOT
from debug_trace import step


@asynccontextmanager
async def connect_mcp():
    # 使用同一个虚拟环境解释器，绝对路径使任意工作目录都能启动。
    params = StdioServerParameters(
        command=sys.executable,
        args=[str(ROOT / "mcp_server.py")],
        env={"PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"},
    )
    await step("MCP", "启动 MCP 子进程", "使用当前 Python 解释器运行 mcp_server.py，建立 stdio 协议通道。")
    async with stdio_client(params) as (reader, writer):
        async with ClientSession(
            reader, writer, read_timeout_seconds=timedelta(seconds=30)
        ) as session:
            await step("MCP", "初始化 MCP 会话", "Client 与 Server 完成协议握手；尚未查询术语。")
            await session.initialize()
            yield session


def to_openai_tool(tool) -> dict:
    # 最小示例关闭 strict：直接使用 MCP 给出的 JSON Schema，不伪造兼容性。
    return {
        "type": "function",
        "name": tool.name,
        "description": tool.description or "",
        "parameters": tool.inputSchema,
        "strict": False,
    }


async def call_lookup(session, arguments: dict) -> dict:
    await step("MCP", "调用术语工具", "通过 tools/call 执行 lookup_term；服务端 mcp_server.py 读取本地 glossary.json。")
    result = await asyncio.wait_for(
        session.call_tool("lookup_term", arguments=arguments), timeout=30
    )
    if result.isError:
        raise RuntimeError("MCP 工具执行失败：" + str(result.content))
    if result.structuredContent is not None:
        return result.structuredContent
    # 兼容只返回文本 JSON 的 MCP 实现。
    text = "\n".join(c.text for c in result.content if c.type == "text")
    return json.loads(text)
