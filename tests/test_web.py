"""网页版 API 与 Skill 选择回归；不访问线上模型。"""
import json
import unittest
from unittest.mock import AsyncMock, patch
import httpx
from openai import RateLimitError

from starlette.testclient import TestClient
from web import app, CompareInput
from comparison import compare

RESULT = {"left": "原文", "right": "translation", "explanation": "含义",
          "keywords": "用法", "references": "无术语命中"}
PAYLOAD = {"text": "请确认", "source": "zh", "pair": "zh-ja",
           "model": "gpt-4.1-mini", "api_key": "test-key-not-real"}


class WebTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_page_and_assets(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("中日对照", response.text)
        self.assertEqual(response.text.count('type="checkbox"'), 4)
        self.assertEqual(response.text.count('value="zh-ja" checked'), 1)
        self.assertEqual(response.headers["cache-control"], "no-store")
        for path in ["/static/app.js", "/static/style.css"]:
            self.assertEqual(self.client.get(path).status_code, 200)

    def test_only_requested_pair_runs(self):
        for pair in ("zh-ja", "zh-en", "en-ja"):
            with patch("web.compare", new_callable=AsyncMock, return_value={"pair": pair, **RESULT}) as run:
                response = self.client.post("/api/compare", json={**PAYLOAD, "pair": pair})
                self.assertEqual(response.status_code, 200)
                run.assert_awaited_once_with("请确认", "zh", pair, "gpt-4.1-mini", "test-key-not-real")
                self.assertNotIn("test-key-not-real", response.text)

    def test_invalid_inputs_do_not_call_agent_or_echo_key(self):
        cases = [{"source":"fr"}, {"pair":"unknown"}, {"text":" "},
                 {"text":"x"*10001},
                 {"api_key":123}, {"pairs":["zh-ja"]}]
        with patch("web.compare", new_callable=AsyncMock) as run:
            for changes in cases:
                response = self.client.post("/api/compare", json={**PAYLOAD, **changes})
                self.assertEqual(response.status_code, 422)
                self.assertNotIn("test-key-not-real", response.text)
            run.assert_not_awaited()

    def test_key_redacted_from_repr(self):
        self.assertNotIn("test-key-not-real", repr(CompareInput(**PAYLOAD)))

    def test_model_and_key_optional_use_free_mode(self):
        cases = [{}, {"model":"gpt-4.1-mini"}, {"api_key":"unused-key"},
                 {"model":"", "api_key":""}]
        for optional in cases:
            with self.subTest(optional=optional), patch("web.compare_free", new_callable=AsyncMock,
                    return_value={"mode":"free", **RESULT}) as free, patch("web.compare", new_callable=AsyncMock) as ai:
                response = self.client.post("/api/compare", json={
                    "text":"你好", "source":"zh", "pair":"zh-ja", **optional})
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json()["mode"], "free")
                free.assert_awaited_once_with("你好", "zh", "zh-ja")
                ai.assert_not_awaited()

    def test_cross_origin_and_wrong_content_type(self):
        with patch("web.compare", new_callable=AsyncMock) as run:
            response = self.client.post("/api/compare", json=PAYLOAD, headers={"origin":"https://other.example"})
            self.assertEqual(response.status_code, 403)
            self.assertEqual(self.client.post("/api/compare", content="x").status_code, 415)
            run.assert_not_awaited()

    def test_size_limit(self):
        response = self.client.post("/api/compare", content="x"*80001, headers={"content-type":"application/json"})
        self.assertEqual(response.status_code, 413)

    def test_errors_sanitized(self):
        with patch("web.compare", new_callable=AsyncMock, side_effect=RuntimeError("secret-test-key-not-real")):
            response = self.client.post("/api/compare", json=PAYLOAD)
            self.assertEqual(response.status_code, 502)
            self.assertNotIn("test-key-not-real", response.text)

    def test_independent_credentials(self):
        with patch("web.compare", new_callable=AsyncMock, return_value=RESULT) as run:
            for key in ("key-one", "key-two"):
                self.client.post("/api/compare", json={**PAYLOAD, "api_key":key})
            self.assertEqual([call.args[-1] for call in run.await_args_list], ["key-one", "key-two"])

    def test_quota_and_rate_limit_are_distinguished(self):
        cases = [
            ({"code":"insufficient_quota", "type":"insufficient_quota"}, "可用额度不足"),
            ({"error":{"code":"billing_hard_limit_reached"}}, "可用额度不足"),
            ({"code":"credit_balance_exhausted", "type":"insufficient_quota"}, "预付余额已耗尽"),
            ({"code":"organization_spend_limit_exceeded"}, "组织 API 消费上限"),
            ({"code":"project_spend_limit_exceeded"}, "当前项目 API 消费上限"),
            ({"code":"organization_usage_limit_exceeded"}, "组织 API 用量上限"),
            ({"code":"rate_limit_exceeded"}, "触发 API 速率限制"),
            ({"code":"slow_down", "type":"rate_limit_error"}, "触发 API 速率限制"),
            ({"message":"unknown"}, "无法确定"),
        ]
        for body, expected in cases:
            exc = RateLimitError("secret-test-key-not-real", body=body,
                response=httpx.Response(429, request=httpx.Request("POST", "https://api.openai.com/v1/responses")))
            with self.subTest(body=body), patch("web.compare", new_callable=AsyncMock,
                    side_effect=ExceptionGroup("MCP lifecycle", [exc])):
                response = self.client.post("/api/compare", json=PAYLOAD)
                self.assertEqual(response.status_code, 429)
                self.assertIn(expected, response.json()["error"])
                self.assertNotIn("test-key-not-real", response.text)


class ComparisonTests(unittest.IsolatedAsyncioTestCase):
    async def test_each_pair_loads_own_skill_including_third_language(self):
        # 工具发现仍经过真实 MCP；模型循环替身避免消耗 API。
        for pair in ("zh-ja", "zh-en", "en-ja"):
            with patch("comparison.run_model_loop", new_callable=AsyncMock, return_value=json.dumps(RESULT)) as run:
                result = await compare("原文", "zh", pair, "test-model", "local-test-only")
                self.assertEqual(result["skill"], pair)
                instructions = run.call_args.args[4]
                self.assertIn(f"name: {pair}", instructions)
                self.assertIn("left", run.call_args.kwargs["output_schema"]["properties"])
                if pair != "en-ja":
                    self.assertEqual(result["left"], "原文")


if __name__ == "__main__":
    unittest.main()
