import unittest
from unittest.mock import patch

import httpx

from free_translation import chunks, translate_text, compare_free, FreeTranslationError


class ChunkTests(unittest.TestCase):
    def test_utf8_chunks_preserve_source_and_byte_limit(self):
        for text in ["你好。"*300, "Hello world! "*100, "日英🙂\n"*200, "x"*1001]:
            parts = chunks(text)
            self.assertEqual("".join(parts), text)
            self.assertTrue(all(len(x.encode("utf-8"))<=500 for x in parts))


class FreeTests(unittest.IsolatedAsyncioTestCase):
    async def test_six_directions_no_keys_and_original_preserved(self):
        calls=[]
        def handle(request):
            calls.append(request)
            return httpx.Response(200,json={"responseStatus":200,"quotaFinished":False,
                "responseData":{"translatedText":"translated &amp; text"}})
        async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
            for source,target in [("zh","ja"),("ja","zh"),("zh","en"),("en","zh"),("en","ja"),("ja","en")]:
                self.assertEqual(await translate_text(client,"Hello",source,target),"translated & text")
            self.assertEqual(await translate_text(client,"原文", "zh","zh"),"原文")
        self.assertEqual(len(calls),6)
        self.assertTrue(all("key" not in r.url.params for r in calls))
        self.assertTrue(all(r.method=="GET" and r.url.path=="/get" for r in calls))

    async def test_quota_and_invalid_response_not_returned_as_translation(self):
        cases = [httpx.Response(429), httpx.Response(200,json={"quotaFinished":True}),
                 httpx.Response(200,json={"responseStatus":403}),
                 httpx.Response(200,json={"responseStatus":200,"responseData":{"translatedText":"MYMEMORY WARNING: quota"}}),
                 httpx.Response(200,text="not json")]
        for response in cases:
            async with httpx.AsyncClient(transport=httpx.MockTransport(lambda r: response)) as client:
                with self.assertRaises(FreeTranslationError):
                    await translate_text(client,"Hello","en","ja")

    async def test_free_result_uses_real_mcp_and_no_openai(self):
        async def fake(client,text,source,target):
            return text if source==target else "translated"
        with patch("free_translation.translate_text", side_effect=fake), patch("comparison.AsyncOpenAI") as ai:
            result=await compare_free("お疲れ様です", "ja", "zh-ja")
            self.assertEqual(result["right"],"お疲れ様です")
            self.assertEqual(result["mode"],"free")
            self.assertIn("otsukaresama",result["references"])
            self.assertIn("未使用大模型",result["explanation"])
            ai.assert_not_called()

    async def test_free_length_limit(self):
        with self.assertRaises(FreeTranslationError):
            await compare_free("x"*1001,"en","zh-ja")

    async def test_unchanged_translation_prefers_exact_target_candidate(self):
        data={"responseStatus":200,"responseData":{"translatedText":"hello!"},"matches":[
            {"segment":"Other", "target":"zh-CN", "translation":"不相关"},
            {"segment":"Hello!", "target":"ja", "translation":"こんにちは"},
            {"segment":"Hello!", "target":"zh-CN", "translation":"您好！"},
        ]}
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda r:httpx.Response(200,json=data))) as client:
            self.assertEqual(await translate_text(client,"Hello!","en","zh"),"您好！")
