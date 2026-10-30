"""一个 Agent 加载一个语言 Skill，通过 MCP 获取资料，再生成翻译解释。"""
import json
import sys
from dataclasses import dataclass

from mcp_bridge import call_lookup, connect_mcp, to_openai_tool
from skill_router import LANGUAGES, load_skill


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
        load_skill(self.source, self.target)


def trace(message: str, enabled: bool):
    if enabled:
        print(message, file=sys.stderr)


async def run_model_loop(client, session, tools, request, instructions, model,
                         verbose=False, max_rounds=5) -> str:
    """保留完整 output，包括推理项；每个 call_id 都要回传对应工具结果。"""
    history = [{"role": "user", "content": json.dumps(request.__dict__, ensure_ascii=False)}]
    allowed = {t["name"] for t in tools}
    for round_number in range(max_rounds):
        trace(f"[model] round={round_number + 1}", verbose)
        response = await client.responses.create(
            model=model, instructions=instructions, input=history,
            tools=tools, store=False, parallel_tool_calls=False,
            # 教学模式首轮必须查询，保证能观察到真实 MCP 调用。
            tool_choice={"type": "function", "name": "lookup_term"}
            if round_number == 0 else "auto",
        )
        history.extend(response.output)
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
            except (ValueError, TypeError, RuntimeError, TimeoutError) as exc:
                # 参数错误作为工具结果回传，允许模型在轮数限制内修正。
                result = {"error": str(exc)}
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
