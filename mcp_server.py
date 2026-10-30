"""真正的 MCP Server：从 JSON 查询资料，以 stdio 对外提供工具。"""
import json
import unicodedata
from typing import Literal

from mcp.server.fastmcp import FastMCP
from skill_router import ROOT

mcp = FastMCP("trilingual-glossary", log_level="WARNING")
Language = Literal["zh", "ja", "en"]


def normalize(text: str) -> str:
    return unicodedata.normalize("NFKC", text).casefold().strip()


@mcp.tool()
def lookup_term(query: str, source: Language, target: Language) -> dict:
    """查找原文整句中包含的术语，返回目标语言候选及语境提醒；未命中返回空列表。"""
    if not query.strip() or len(query) > 10000:
        raise ValueError("query 不能为空且不能超过 10000 个字符")
    if source == target:
        raise ValueError("源语言与目标语言必须不同")
    entries = json.loads((ROOT / "data/glossary.json").read_text(encoding="utf-8"))
    normalized = normalize(query)
    matches = []
    for entry in entries:
        # 简单子串匹配，适合教学；不是分词器、向量搜索或完整词典。
        if any(normalize(term) in normalized for term in entry["terms"][source]):
            matches.append({
                "id": entry["id"],
                "source_terms": entry["terms"][source],
                "target_terms": entry["terms"][target],
                "note": entry["note"],
            })
    return {"found": bool(matches), "matches": matches}


if __name__ == "__main__":
    # stdout 专用于协议消息；调试日志必须写 stderr。
    mcp.run(transport="stdio")
