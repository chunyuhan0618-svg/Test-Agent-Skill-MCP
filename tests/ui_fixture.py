"""仅供界面验证：python tests/ui_fixture.py。返回显式标注的模拟译文，不调用模型。"""
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
app = web.app

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8001, access_log=False)
