"""English: Validate translation requests, load pair rules, and run a bounded model/tool loop. Tool results return through MCP with matching call IDs.
日本語：翻訳要求を検証し、組の規則を読み込み、回数制限付きのモデル・ツール処理を実行します。MCP の結果は対応する call ID で返します。
中文：校验翻译请求、加载组合规则，执行有轮数限制的模型与工具循环，并用对应 call ID 回传 MCP 结果。
"""
import json
import sys
from dataclasses import dataclass

from mcp_bridge import call_lookup, connect_mcp, to_openai_tool
from skill_router import LANGUAGES, load_skill
from debug_trace import step, DebugPauseTimeout


@dataclass(frozen=True)
class TranslationRequest:
    text: str
    source: str
    target: str
    explain: str = "zh"

    def validate(self):
        if not self.text.strip() or len(self.text) > 10000:
            raise ValueError("原文不能为空，且不能超过 10000 个字符。")
        if self.explain not in LANGUAGES:
            raise ValueError("解释语言仅支持 zh、ja、en。")
        # 校验不读取 Skill；真正加载发生在有明确调试节点的执行路径中。
        if self.source not in LANGUAGES or self.target not in LANGUAGES:
            raise ValueError("仅支持 zh、ja、en；本例要求明确指定源语言。")
        if self.source == self.target:
            raise ValueError("源语言与目标语言不能相同。")


def trace(message: str, enabled: bool):
    if enabled:
        print(message, file=sys.stderr)


async def run_model_loop(client, session, tools, request, instructions, model,
                         verbose=False, max_rounds=5, output_schema=None) -> str:
    """保留完整 output，包括推理项；每个 call_id 都要回传对应工具结果。"""
    history = [{"role": "user", "content": json.dumps(request.__dict__, ensure_ascii=False)}]
    allowed = {t["name"] for t in tools}
    for round_number in range(max_rounds):
        trace(f"[model] round={round_number + 1}", verbose)
        await step("Agent", "请求大模型", f"模型循环第 {round_number + 1} 轮：发送 Skill、请求和工具定义；此步骤可能产生 API 用量。")
        response = await client.responses.create(
            model=model, instructions=instructions, input=history,
            tools=tools, store=False, parallel_tool_calls=False,
            # 教学模式首轮必须查询，保证能观察到真实 MCP 调用。
            tool_choice={"type": "function", "name": "lookup_term"}
            if round_number == 0 else "auto",
            **({"text": {"format": {"type": "json_schema", "name": "comparison",
                "strict": True, "schema": output_schema}}} if output_schema else {}),
        )
        history.extend(response.output)
        await step("Agent", "检查模型返回", "判断模型请求的是工具调用还是最终译文；不展示隐藏推理内容。")
        calls = [item for item in response.output if item.type == "function_call"]
        if not calls:
            if response.status != "completed" or not response.output_text.strip():
                raise RuntimeError("模型没有返回完整答案，请重试或检查模型配置。")
            return response.output_text
        for call in calls:
            try:
                if call.name not in allowed or call.name != "lookup_term":
                    raise ValueError("模型请求了未授权工具")
                args = json.loads(call.arguments)
                if not isinstance(args, dict):
                    raise ValueError("工具参数必须是 JSON 对象")
                if set(args) != {"query", "source", "target"}:
                    raise ValueError("工具参数必须包含 query、source、target")
                if args["source"] != request.source or args["target"] != request.target:
                    raise ValueError("工具语言参数必须与本次翻译方向一致")
                trace(f"[mcp] call lookup_term {json.dumps(args, ensure_ascii=False)}", verbose)
                result = await call_lookup(session, args)
                trace(f"[mcp] result {json.dumps(result, ensure_ascii=False)}", verbose)
            except DebugPauseTimeout:
                raise
            except (ValueError, TypeError, RuntimeError, TimeoutError) as exc:
                # 参数错误作为工具结果回传，允许模型在轮数限制内修正。
                result = {"error": str(exc)}
            await step("Agent", "回传工具结果", "用 call_id 将 MCP 查询结果交给模型，随后进入下一轮。")
            history.append({
                "type": "function_call_output", "call_id": call.call_id,
                "output": json.dumps(result, ensure_ascii=False),
            })
    raise RuntimeError(f"达到 {max_rounds} 轮上限，尚未生成最终答案。")


async def translate(request: TranslationRequest, *, demo=False, verbose=False,
                    model=None, api_key=None) -> str:
    request.validate()
    name, instructions = load_skill(request.source, request.target)
    trace(f"[skill] selected={name}", verbose)
    if not demo and (not api_key or api_key == "replace-with-your-api-key" or not model):
        raise ValueError("请在 .env 设置真实 OPENAI_API_KEY 和 OPENAI_MODEL，或使用 --demo。")
    async with connect_mcp() as session:
        discovered = await session.list_tools()
        tools = [to_openai_tool(t) for t in discovered.tools if t.name == "lookup_term"]
        if not tools:
            raise RuntimeError("MCP Server 没有提供 lookup_term")
        trace("[mcp] initialized; discovered=lookup_term", verbose)
        if demo:
            result = await call_lookup(session, {
                "query": request.text, "source": request.source, "target": request.target,
            })
            # 明确返回数据与加载信息，不伪造模型翻译。
            return json.dumps({
                "mode": "demo: no model called; not a translation",
                "selected_skill": name,
                "loaded_instruction_characters": len(instructions),
                "direction": f"{request.source}->{request.target}",
                "mcp_result": result,
            }, ensure_ascii=False, indent=2)
        from openai import AsyncOpenAI
        async with AsyncOpenAI(api_key=api_key, timeout=60, max_retries=1) as client:
            return await run_model_loop(
                client, session, tools, request, instructions, model, verbose,
            )
