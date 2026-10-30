"""网页版：每个勾选栏位独立加载对应 Skill，生成两种语言的结构化结果。"""

from openai import AsyncOpenAI
from pydantic import BaseModel, ConfigDict, Field

from agent import TranslationRequest, run_model_loop
from mcp_bridge import connect_mcp, to_openai_tool
from skill_router import load_skill

PAIRS = {"zh-ja": ("zh", "ja"), "zh-en": ("zh", "en"), "en-ja": ("ja", "en")}


class ComparisonResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    left: str = Field(min_length=1)
    right: str = Field(min_length=1)
    explanation: str = Field(min_length=1)
    keywords: str = Field(min_length=1)
    references: str = Field(min_length=1)


async def compare(text: str, source: str, pair: str, model: str, api_key: str) -> dict:
    left, right = PAIRS[pair]
    _, instructions = load_skill(left, right)
    # 若原文属于第三种语言，直接由原文生成两种译文，避免串行转译误差。
    target = right if source == left else left
    request = TranslationRequest(text, source, target, "zh")
    request.validate()
    instructions += f"""\n\n# 网页双语对照模式（覆盖普通输出格式）
本次展示语言组合为 {left} 与 {right}，原文语言为 {source}。
原文可能是第三种语言；仍从同一份原文直接生成两种表达，不串行转译。
输出 JSON：left 是 {left}，right 是 {right}。
如果其中一种是原文语言，对应字段原样保留原文。
explanation、keywords、references 使用中文，分别解释意思、关键词用法、实际术语参考。
仍先查询 MCP 术语；工具 source={source}，target={target}。
对照的语序、语气、礼貌等分析应用当前选中 Skill。
"""
    async with connect_mcp() as session:
        tools = [to_openai_tool(t) for t in (await session.list_tools()).tools
                 if t.name == "lookup_term"]
        if not tools:
            raise RuntimeError("MCP 未提供术语查询工具")
        async with AsyncOpenAI(api_key=api_key, timeout=60, max_retries=1) as client:
            raw = await run_model_loop(
                client, session, tools, request, instructions, model,
                output_schema=ComparisonResult.model_json_schema(),
            )
    result = ComparisonResult.model_validate_json(raw).model_dump()
    # 原文不依赖模型复写，保证可逐字对照。
    if source == left:
        result["left"] = text
    if source == right:
        result["right"] = text
    return {"pair": pair, "skill": pair, "left_language": left,
            "right_language": right, **result}
