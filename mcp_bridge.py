"""连接本地 MCP 子进程，并适配 MCP 工具与 Responses function calling。"""
import asyncio
import json
import sys
from contextlib import asynccontextmanager
from datetime import timedelta

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from skill_router import ROOT


@asynccontextmanager
async def connect_mcp():
    # 使用同一个虚拟环境解释器，绝对路径使任意工作目录都能启动。
    params = StdioServerParameters(
        command=sys.executable,
        args=[str(ROOT / "mcp_server.py")],
        env={"PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"},
    )
    async with stdio_client(params) as (reader, writer):
        async with ClientSession(
            reader, writer, read_timeout_seconds=timedelta(seconds=30)
        ) as session:
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
