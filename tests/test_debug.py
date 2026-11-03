"""English: Test real checkpoint pausing, next-step sequencing, run-to-end, cancellation and session cleanup, including integration paths.
日本語：実際の停止、次ステップの順序、最後まで実行、キャンセル、セッション回収と統合経路を検証します。
中文：测试真实暂停、下一步序号、一步到底、取消、会话回收及集成路径。
"""
import asyncio
import inspect
import json
import time
import threading
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

import httpx
from starlette.testclient import TestClient

from debug_trace import CURRENT, DebugSession, DebugSessions, DebugPauseTimeout, step
from skill_router import ROOT
from web import app

PAYLOAD = {"text":"Hello!", "source":"en", "pairs":["zh-en"]}
RESULT = {"pair":"zh-en", "skill":"zh-en", "left_language":"zh", "right_language":"en",
          "left":"您好！", "right":"Hello!", "explanation":"说明", "keywords":"用法", "references":"词条"}


async def wait_paused(session, previous=0):
    async with asyncio.timeout(2):
        while not (session.status=="paused" and session.events[-1]["seq"]>previous):
            await asyncio.sleep(0)


class GateTests(unittest.IsolatedAsyncioTestCase):
    def test_completed_sessions_are_recycled_at_capacity(self):
        registry=DebugSessions()
        for _ in range(16):
            registry.create().finish()
        registry.create()
        self.assertEqual(len(registry.items),16)
        active=DebugSessions()
        for _ in range(16):
            active.create()
        with self.assertRaises(ValueError):
            active.create()

    async def test_no_execution_until_next_and_no_double_release(self):
        session, effects = DebugSession(), []
        async def work():
            token=CURRENT.set(session)
            try:
                await step("Agent", "first")
                effects.append("one")
                await step("MCP", "second")
                effects.append("two")
                session.finish()
            finally:
                CURRENT.reset(token)
        task=asyncio.create_task(work())
        try:
            await wait_paused(session)
            self.assertEqual(effects,[])
            first=session.events[-1]
            lines=(ROOT/first["file"]).read_text(encoding="utf-8").splitlines()
            self.assertEqual(lines[first["line"]-1].strip(),'effects.append("one")')
            self.assertTrue(session.advance(1))
            self.assertFalse(session.advance(1))
            await wait_paused(session,1)
            self.assertEqual(effects,["one"])
            self.assertFalse(session.advance(1))
            self.assertTrue(session.advance(2))
            await task
            self.assertEqual(effects,["one","two"])
            self.assertEqual(session.status,"completed")
        finally:
            if not task.done():
                task.cancel()
                await asyncio.gather(task,return_exceptions=True)

    async def test_cancel_does_not_execute_paused_operation(self):
        session,effects=DebugSession(),[]
        async def work():
            token=CURRENT.set(session)
            try:
                await step("Engine","network request")
                effects.append("request")
            finally:
                CURRENT.reset(token)
        task=asyncio.create_task(work())
        await wait_paused(session)
        task.cancel()
        await asyncio.gather(task,return_exceptions=True)
        self.assertEqual(effects,[])

    async def test_pause_timeout(self):
        session=DebugSession()
        token=CURRENT.set(session)
        try:
            with patch("debug_trace.PAUSE_SECONDS",0.01):
                with self.assertRaises(DebugPauseTimeout):
                    await step("Agent","timeout")
        finally:
            CURRENT.reset(token)

    async def test_non_debug_is_immediate(self):
        await step("Agent","ordinary execution")
        self.assertIsNone(CURRENT.get())


class DebugAPITests(unittest.TestCase):
    def wait_state(self,client,session_id,predicate):
        deadline=time.monotonic()+5
        while time.monotonic()<deadline:
            response=client.get(f"/api/debug/{session_id}")
            self.assertEqual(response.status_code,200)
            data=response.json()
            if predicate(data):
                return data
        self.fail("debug state did not arrive")

    def test_start_pauses_before_agent_and_result_is_gated(self):
        with TestClient(app) as client, patch("web.compare_free",new_callable=AsyncMock,return_value=RESULT) as provider:
            response=client.post("/api/debug/start",json=PAYLOAD)
            self.assertEqual(response.status_code,201)
            sid=response.json()["id"]
            data=self.wait_state(client,sid,lambda d:d["status"]=="paused")
            provider.assert_not_awaited()
            self.assertEqual(data["results"],{})
            client.post(f"/api/debug/{sid}/next",json={"seq":1})
            data=self.wait_state(client,sid,lambda d:d["status"]=="paused" and len(d["events"])==2)
            provider.assert_awaited_once_with("Hello!","en","zh-en")
            self.assertEqual(data["results"],{})
            self.assertEqual(client.post(f"/api/debug/{sid}/next",json={"seq":1}).status_code,409)
            client.post(f"/api/debug/{sid}/next",json={"seq":2})
            data=self.wait_state(client,sid,lambda d:d["status"]=="completed")
            self.assertEqual(list(data["results"]),["zh-en"])

    def test_continue_finishes_all_selected_pairs_with_real_mcp(self):
        requests=[]
        real_client=httpx.AsyncClient
        def handle(request):
            requests.append(request)
            return httpx.Response(200,json={"responseStatus":200,"responseData":{"translatedText":"译文"}})
        def factory(**kwargs):
            return real_client(transport=httpx.MockTransport(handle),**kwargs)
        with TestClient(app) as client, patch("free_translation.httpx.AsyncClient",side_effect=factory):
            sid=client.post("/api/debug/start",json={**PAYLOAD,"pairs":["zh-ja","zh-en","en-ja"]}).json()["id"]
            self.wait_state(client,sid,lambda d:d["status"]=="paused")
            response=client.post(f"/api/debug/{sid}/continue",json={})
            self.assertEqual(response.status_code,200)
            self.assertTrue(response.json()["run_to_end"])
            data=self.wait_state(client,sid,lambda d:d["status"] in ("completed","error"))
            self.assertEqual(data["status"],"completed",data)
            self.assertEqual(set(data["results"]),{"zh-ja","zh-en","en-ja"})
            self.assertEqual(len(requests),4)
            self.assertTrue(all(e["status"]=="completed" for e in data["events"]))
            self.assertEqual({e["kind"] for e in data["events"]},{"Agent","Skill","MCP","Engine"})
            self.assertEqual(client.post(f"/api/debug/{sid}/continue",json={}).status_code,409)

    def test_continue_while_running_still_allows_cancel(self):
        started=threading.Event()
        async def slow_pipeline(*args):
            started.set()
            await asyncio.Event().wait()
        with TestClient(app) as client, patch("web.compare_free",side_effect=slow_pipeline) as provider:
            sid=client.post("/api/debug/start",json=PAYLOAD).json()["id"]
            self.wait_state(client,sid,lambda d:d["status"]=="paused")
            client.post(f"/api/debug/{sid}/next",json={"seq":1})
            self.assertTrue(started.wait(timeout=2))
            response=client.post(f"/api/debug/{sid}/continue",json={})
            self.assertEqual(response.status_code,200)
            self.assertTrue(response.json()["run_to_end"])
            result=client.post(f"/api/debug/{sid}/cancel",json={}).json()
            self.assertEqual(result["status"],"cancelled")
            self.assertEqual(result["results"],{})
            self.assertEqual(provider.call_count,1)

    def test_real_free_pipeline_pauses_at_skill_provider_and_mcp(self):
        requests=[]
        real_client=httpx.AsyncClient
        def handle(request):
            requests.append(request)
            return httpx.Response(200,json={"responseStatus":200,"responseData":{"translatedText":"您好！"}})
        def factory(**kwargs):
            return real_client(transport=httpx.MockTransport(handle),**kwargs)
        with TestClient(app) as client, patch("free_translation.httpx.AsyncClient",side_effect=factory):
            sid=client.post("/api/debug/start",json=PAYLOAD).json()["id"]
            seq,seen=0,[]
            for _ in range(30):
                data=self.wait_state(client,sid,lambda d:d["status"] in ("completed","error") or
                    (d["status"]=="paused" and d["events"][-1]["seq"]>seq))
                if data["status"] in ("completed","error"):
                    break
                event=data["events"][-1]
                seen.append(event)
                if event["kind"]=="Engine":
                    self.assertEqual(len(requests),0)
                if event["kind"]=="MCP":
                    self.assertEqual(len(requests),1)
                if event["kind"]=="Skill":
                    self.assertIn("name: zh-en",event["resource"]["text"])
                # 显示的源码来自真实文件，并定位到检查点后的操作。
                lines=(ROOT/event["file"]).read_text(encoding="utf-8").splitlines()
                current=next(x for x in event["code"] if x["number"]==event["line"])
                self.assertEqual(current["text"],lines[event["line"]-1])
                self.assertNotIn("await step(",current["text"])
                seq=event["seq"]
                self.assertEqual(client.post(f"/api/debug/{sid}/next",json={"seq":seq}).status_code,200)
            self.assertEqual(data["status"],"completed",data)
            self.assertEqual(set(e["kind"] for e in seen),{"Agent","Skill","Engine","MCP"})
            self.assertEqual(data["results"]["zh-en"]["left"],"您好！")
            self.assertEqual(data["results"]["zh-en"]["right"],"Hello!")

    def test_cancel_and_credentials_not_exposed(self):
        with TestClient(app) as client, patch("web.compare",new_callable=AsyncMock) as ai:
            sid=client.post("/api/debug/start",json={**PAYLOAD,"model":"test-model","api_key":"private-key-value"}).json()["id"]
            data=self.wait_state(client,sid,lambda d:d["status"]=="paused")
            self.assertNotIn("private-key-value",json.dumps(data))
            response=client.post(f"/api/debug/{sid}/cancel",json={})
            self.assertEqual(response.json()["status"],"cancelled")
            ai.assert_not_awaited()
            self.assertEqual(client.post(f"/api/debug/{sid}/next",json={"seq":1}).status_code,409)

    def test_real_model_loop_gates_sdk_requests_and_mcp_feedback(self):
        from openai import AsyncOpenAI
        requests=[]
        def handle(request):
            requests.append(json.loads(request.content))
            if len(requests)==1:
                output=[{"type":"function_call","id":"fc_debug","status":"completed",
                         "name":"lookup_term","call_id":"call_debug",
                         "arguments":json.dumps({"query":"Hello!","source":"en","target":"zh"})}]
            else:
                output=[{"type":"message","id":"msg_debug","status":"completed","role":"assistant",
                         "content":[{"type":"output_text","annotations":[],"text":json.dumps({
                             k:RESULT[k] for k in ["left","right","explanation","keywords","references"]})}]}]
            return httpx.Response(200,json={"id":f"resp_{len(requests)}","object":"response",
                "created_at":0,"status":"completed","model":"test-model","output":output,
                "error":None,"incomplete_details":None,"instructions":None,"metadata":{},
                "parallel_tool_calls":False,"tool_choice":"auto","tools":[],"temperature":1,"top_p":1})
        def factory(**kwargs):
            return AsyncOpenAI(http_client=httpx.AsyncClient(transport=httpx.MockTransport(handle)),**kwargs)
        with TestClient(app) as client, patch("comparison.AsyncOpenAI",side_effect=factory):
            sid=client.post("/api/debug/start",json={**PAYLOAD,"model":"test-model","api_key":"private-key-value"}).json()["id"]
            seq,titles=0,[]
            for _ in range(40):
                data=self.wait_state(client,sid,lambda d:d["status"] in ("completed","error") or
                    (d["status"]=="paused" and d["events"][-1]["seq"]>seq))
                self.assertNotIn("private-key-value",json.dumps(data))
                if data["status"] in ("completed","error"):
                    break
                event=data["events"][-1]
                if event["title"]=="请求大模型":
                    self.assertEqual(len(requests),titles.count("请求大模型"))
                titles.append(event["title"])
                seq=event["seq"]
                client.post(f"/api/debug/{sid}/next",json={"seq":seq})
            self.assertEqual(data["status"],"completed",data)
            self.assertEqual(len(requests),2)
            self.assertIn("调用术语工具",titles)
            self.assertIn("回传工具结果",titles)
            self.assertIn("校验结构化译文",titles)
            self.assertEqual(requests[1]["input"][-1]["type"],"function_call_output")
            self.assertEqual(data["results"]["zh-en"]["left"],"您好！")

    def test_input_origin_and_unknown_session(self):
        with TestClient(app) as client:
            self.assertEqual(client.post("/api/debug/start",json=PAYLOAD,
                headers={"origin":"https://other.example"}).status_code,403)
            for pairs in [[],["unknown"],["zh-ja","zh-ja"]]:
                self.assertEqual(client.post("/api/debug/start",json={**PAYLOAD,"pairs":pairs}).status_code,422)
            self.assertEqual(client.get("/api/debug/nonexistent").status_code,404)
            self.assertEqual(client.post("/api/debug/start",content="x").status_code,415)

    def test_timeout_inside_mcp_context_ends_whole_job(self):
        from mcp_bridge import connect_mcp
        async def pipeline(*args):
            async with connect_mcp():
                return RESULT
        with TestClient(app) as client, patch("web.compare_free",side_effect=pipeline):
            sid=client.post("/api/debug/start",json=PAYLOAD).json()["id"]
            self.wait_state(client,sid,lambda d:d["status"]=="paused")
            client.post(f"/api/debug/{sid}/next",json={"seq":1})
            self.wait_state(client,sid,lambda d:d["status"]=="paused" and len(d["events"])==2)
            # 在 MCP 子进程上下文内等待初始化的检查点超时，异常会被 AnyIO 包装。
            with patch("debug_trace.PAUSE_SECONDS",0.05):
                client.post(f"/api/debug/{sid}/next",json={"seq":2})
                data=self.wait_state(client,sid,lambda d:d["status"]=="error")
            self.assertIn("调试暂停",data["error"])
            self.assertEqual(data["results"],{})


if __name__=="__main__":
    unittest.main()
