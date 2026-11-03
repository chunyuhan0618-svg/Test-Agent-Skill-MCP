"""English: Provide explicitly simulated translation results for repeatable browser checks. This fixture is not proof of live model or provider availability.
日本語：再現可能なブラウザー確認向けに、明示的な模擬翻訳を返します。実際のモデルやサービスの可用性を示すものではありません。
中文：为可复现浏览器检查提供明确标注的模拟结果，不能作为线上模型或翻译服务可用的证据。
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import web
from comparison import PAIRS


async def fixture_compare(text, source, pair, model, api_key):
    print(f"UI_FIXTURE pair={pair}", flush=True)  # 不记录 Key 或原文。
    await asyncio.sleep(0.1)
    if model == "test-error":
        raise RuntimeError("UI fixture failure")
    left, right = PAIRS[pair]
    values = {"zh": "您好，麻烦您确认一下。", "ja": "お疲れ様です。ご確認をお願いいたします。",
              "en": "Hello, could you please check this?"}
    values[source] = text
    return {"pair":pair, "skill":pair, "left_language":left, "right_language":right,
            "left":values[left], "right":values[right],
            "explanation":"【界面测试模拟结果】这是一种礼貌的工作沟通表达。",
            "keywords":"模拟说明：保留原文语气，按场景处理寒暄。",
            "references":"模拟资料；本服务不调用模型或 MCP。"}


web.compare = fixture_compare


async def fixture_free(text, source, pair):
    return await fixture_compare(text, source, pair, "", "")


web.compare_free = fixture_free
app = web.app

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8001, access_log=False)
