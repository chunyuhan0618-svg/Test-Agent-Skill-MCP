"""English: Build structured bilingual web results. Both target texts come directly from the source; explanation language follows the request interface language.
日本語：構造化した Web 対訳を生成します。両方の訳文を原文から直接作り、説明は要求時の表示言語を使います。
中文：生成网页结构化双语结果；两种表达都直接来自原文，解释使用请求时的界面语言。
"""
from openai import AsyncOpenAI
from pydantic import BaseModel, ConfigDict, Field

from agent import TranslationRequest, run_model_loop
from mcp_bridge import connect_mcp, to_openai_tool
from skill_router import load_skill
from debug_trace import step
from ui_locale import UI_LANGUAGE

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
    await step("Skill", "加载双语 Skill", f"读取 {pair} 的专业规则及共享规则，准备放入模型上下文。", resource=f"skills/{pair}/SKILL.md")
    _, instructions = load_skill(left, right)
    # 若原文属于第三种语言，直接由原文生成两种译文，避免串行转译误差。
    target = right if source == left else left
    request = TranslationRequest(text, source, target, UI_LANGUAGE.get())
    request.validate()
    instructions += f"""\n\n# 网页双语对照模式（覆盖普通输出格式）
本次展示语言组合为 {left} 与 {right}，原文语言为 {source}。
原文可能是第三种语言；仍从同一份原文直接生成两种表达，不串行转译。
输出 JSON：left 是 {left}，right 是 {right}。
如果其中一种是原文语言，对应字段原样保留原文。
explanation、keywords、references 使用 {UI_LANGUAGE.get()} 对应的语言（en=英文、ja=日文、zh=中文），分别解释意思、关键词用法、实际术语参考。
仍先查询 MCP 术语；工具 source={source}，target={target}。
对照的语序、语气、礼貌等分析应用当前选中 Skill。
"""
    async with connect_mcp() as session:
        await step("MCP", "发现可用工具", "通过 tools/list 获取真实 MCP Server 提供的工具定义。")
        tools = [to_openai_tool(t) for t in (await session.list_tools()).tools
                 if t.name == "lookup_term"]
        if not tools:
            raise RuntimeError("MCP 未提供术语查询工具")
        async with AsyncOpenAI(api_key=api_key, timeout=60, max_retries=1) as client:
            raw = await run_model_loop(
                client, session, tools, request, instructions, model,
                output_schema=ComparisonResult.model_json_schema(),
            )
    await step("Agent", "校验结构化译文", "检查两种语言文本、意思解释、关键词和术语参考字段。")
    result = ComparisonResult.model_validate_json(raw).model_dump()
    # 原文不依赖模型复写，保证可逐字对照。
    if source == left:
        result["left"] = text
    if source == right:
        result["right"] = text
    return {"pair": pair, "skill": pair, "left_language": left,
            "right_language": right, **result}
