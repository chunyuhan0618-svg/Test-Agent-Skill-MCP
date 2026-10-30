"""离线模型替身 + 真实 MCP 子进程：不需要 API Key，不评估翻译质量。"""
import json
import unittest
from functools import wraps
from types import SimpleNamespace
from unittest.mock import AsyncMock

from agent import TranslationRequest, run_model_loop, translate
from mcp_bridge import call_lookup, connect_mcp, to_openai_tool
from skill_router import load_skill


def response(*calls, text="", status="completed"):
    return SimpleNamespace(output=list(calls), output_text=text, status=status)


def call(arguments, name="lookup_term", call_id="call_1"):
    return SimpleNamespace(type="function_call", name=name, call_id=call_id,
                           arguments=json.dumps(arguments, ensure_ascii=False))


class RoutingTests(unittest.TestCase):
    def test_all_six_directions(self):
        for a, b, expected in [("zh", "ja", "zh-ja"), ("zh", "en", "zh-en"),
                               ("en", "ja", "en-ja")]:
            for source, target in [(a, b), (b, a)]:
                with self.subTest(source=source, target=target):
                    name, instructions = load_skill(source, target)
                    self.assertEqual(name, expected)
                    self.assertIn("lookup_term", instructions)

    def test_invalid_requests(self):
        for request in [TranslationRequest("", "zh", "en"),
                        TranslationRequest("x", "en", "en"),
                        TranslationRequest("x", "auto", "en"),
                        TranslationRequest("x", "en", "ja", "fr")]:
            with self.assertRaises(ValueError):
                request.validate()


def with_mcp(test):
    # AnyIO 的取消作用域必须在同一 asyncio Task 中进入和退出；
    # unittest 的 asyncSetUp/test/asyncTearDown 分属不同 Task。
    @wraps(test)
    async def wrapped(self):
        async with connect_mcp() as session:
            self.session = session
            discovered = await session.list_tools()
            self.tools = [to_openai_tool(t) for t in discovered.tools]
            await test(self)
    return wrapped


class MCPIntegrationTests(unittest.IsolatedAsyncioTestCase):

    @with_mcp
    async def test_real_mcp_all_six_directions(self):
        cases = [("zh", "ja", "跟进"), ("ja", "zh", "お疲れ様です"),
                 ("zh", "en", "跟进"), ("en", "zh", "Please follow up tomorrow"),
                 ("en", "ja", "power outlet"), ("ja", "en", "コンセント")]
        for source, target, text in cases:
            with self.subTest(source=source, target=target):
                result = await call_lookup(self.session, {
                    "query": text, "source": source, "target": target,
                })
                self.assertTrue(result["found"])
                self.assertTrue(result["matches"][0]["target_terms"])

    @with_mcp
    async def test_unknown_and_invalid_tool_arguments(self):
        result = await call_lookup(self.session, {
            "query": "xyz-unlisted", "source": "en", "target": "zh",
        })
        self.assertEqual(result, {"found": False, "matches": []})
        with self.assertRaises(RuntimeError):
            await call_lookup(self.session, {"query": "x", "source": "fr", "target": "zh"})

    @with_mcp
    async def test_model_tool_round_trip(self):
        # 只替换模型响应；工具仍跨 stdio 调用真实 MCP Server。
        args = {"query": "お疲れ様です", "source": "ja", "target": "zh"}
        reasoning = SimpleNamespace(type="reasoning", id="reasoning_1")
        client = SimpleNamespace(responses=SimpleNamespace(create=AsyncMock(side_effect=[
            response(reasoning, call(args)), response(text="mock final answer"),
        ])))
        result = await run_model_loop(client, self.session, self.tools,
            TranslationRequest(args["query"], "ja", "zh"), "skill instructions", "test-model")
        self.assertEqual(result, "mock final answer")
        kwargs = client.responses.create.call_args_list[1].kwargs
        self.assertIn(reasoning, kwargs["input"])
        outputs = [x for x in kwargs["input"] if isinstance(x, dict)
                   and x.get("type") == "function_call_output"]
        self.assertEqual(outputs[0]["call_id"], "call_1")
        self.assertTrue(json.loads(outputs[0]["output"])["found"])
        self.assertFalse(kwargs["store"])

    @with_mcp
    async def test_unknown_tool_and_wrong_direction_return_errors(self):
        bad_calls = [call({}, name="delete_file"), call({
            "query": "hello", "source": "en", "target": "ja",
        })]
        for bad in bad_calls:
            client = SimpleNamespace(responses=SimpleNamespace(create=AsyncMock(side_effect=[
                response(bad), response(text="recovered"),
            ])))
            await run_model_loop(client, self.session, self.tools,
                TranslationRequest("hello", "en", "zh"), "instructions", "test-model")
            history = client.responses.create.call_args.kwargs["input"]
            self.assertIn("error", json.loads(history[-1]["output"]))

    @with_mcp
    async def test_round_limit(self):
        args = {"query": "hello", "source": "en", "target": "zh"}
        client = SimpleNamespace(responses=SimpleNamespace(create=AsyncMock(
            return_value=response(call(args)))))
        with self.assertRaisesRegex(RuntimeError, "上限"):
            await run_model_loop(client, self.session, self.tools,
                TranslationRequest("hello", "en", "zh"), "instructions", "test-model", max_rounds=2)

    @with_mcp
    async def test_incomplete_response_fails(self):
        client = SimpleNamespace(responses=SimpleNamespace(create=AsyncMock(
            return_value=response(text="partial", status="incomplete"))))
        with self.assertRaisesRegex(RuntimeError, "完整答案"):
            await run_model_loop(client, self.session, self.tools,
                TranslationRequest("hello", "en", "zh"), "instructions", "test-model")


class DemoTests(unittest.IsolatedAsyncioTestCase):
    async def test_demo_does_not_claim_translation(self):
        result = json.loads(await translate(
            TranslationRequest("Please follow up", "en", "zh"), demo=True))
        self.assertEqual(result["selected_skill"], "zh-en")
        self.assertIn("not a translation", result["mode"])
        self.assertTrue(result["mcp_result"]["found"])

    async def test_missing_key_fails_before_connection(self):
        with self.assertRaisesRegex(ValueError, "OPENAI_API_KEY"):
            await translate(TranslationRequest("hello", "en", "zh"))


class SDKContractTests(unittest.IsolatedAsyncioTestCase):
    async def test_real_sdk_serialization_without_network(self):
        """使用真实 OpenAI SDK 和本地 HTTP 替身验证请求、响应及历史序列化。"""
        import httpx
        from openai import AsyncOpenAI

        requests = []
        args = {"query": "follow up", "source": "en", "target": "zh"}

        def handle(request):
            body = json.loads(request.content)
            requests.append(body)
            if len(requests) == 1:
                output = [{"type": "function_call", "id": "fc_1", "status": "completed",
                           "name": "lookup_term", "call_id": "call_sdk",
                           "arguments": json.dumps(args)}]
            else:
                output = [{"type": "message", "id": "msg_1", "status": "completed",
                           "role": "assistant", "content": [{"type": "output_text",
                           "text": "SDK contract verified", "annotations": []}]}]
            return httpx.Response(200, json={
                "id": f"resp_{len(requests)}", "object": "response", "created_at": 0,
                "status": "completed", "model": "test-model", "output": output,
                "error": None, "incomplete_details": None, "instructions": None,
                "metadata": {}, "parallel_tool_calls": False, "tool_choice": "auto",
                "tools": [], "temperature": 1, "top_p": 1,
            })

        async with connect_mcp() as session:
            tools = [to_openai_tool(t) for t in (await session.list_tools()).tools]
            async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as http:
                async with AsyncOpenAI(api_key="local-test-only", http_client=http) as client:
                    result = await run_model_loop(client, session, tools,
                        TranslationRequest("follow up", "en", "zh"), "skill", "test-model",
                        output_schema={"type": "object", "properties": {},
                                       "required": [], "additionalProperties": False})
        self.assertEqual(result, "SDK contract verified")
        self.assertEqual(len(requests), 2)
        self.assertEqual(requests[0]["text"]["format"]["type"], "json_schema")
        self.assertEqual(requests[0]["tools"][0]["parameters"]["type"], "object")
        tool_output = requests[1]["input"][-1]
        self.assertEqual(tool_output["call_id"], "call_sdk")
        self.assertTrue(json.loads(tool_output["output"])["found"])


if __name__ == "__main__":
    unittest.main()
