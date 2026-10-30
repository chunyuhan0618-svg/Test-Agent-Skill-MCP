"""无需模型和 Key 的联网翻译；只调用 MyMemory GET，不上传翻译记忆。"""
import html
import re

import httpx

from comparison import PAIRS
from mcp_bridge import call_lookup, connect_mcp
from skill_router import load_skill
from debug_trace import step

CODES = {"zh": "zh-CN", "ja": "ja", "en": "en"}


class FreeTranslationError(Exception):
    """只包含可安全展示的本地提示，不包含上游响应或原文。"""


def byte_chunks(text: str, limit=500) -> list[str]:
    """服务每段最多 500 UTF-8 字节；优先在标点或空白处分段。"""
    output = []
    while text:
        size, end, boundary = 0, 0, 0
        for index, char in enumerate(text):
            size += len(char.encode("utf-8"))
            if size > limit:
                break
            end = index + 1
            if char.isspace() or char in "。！？.!?；;":
                boundary = end
        if end == len(text):
            output.append(text)
            break
        end = boundary or end
        if not end:
            raise ValueError("分段字节上限太小")
        output.append(text[:end])
        text = text[end:]
    return output


def chunks(text: str, limit=500) -> list[str]:
    # 先按句切分，避免短的多句原文只命中服务中的一条近似翻译记忆。
    sentences = re.findall(r"[^。！？!?\n]+[。！？!?\n]*|[。！？!?\n]+", text)
    return [part for sentence in sentences for part in byte_chunks(sentence, limit)]


async def translate_text(client, text: str, source: str, target: str) -> str:
    if source == target:
        await step("Agent", "保留原文", f"目标语言 {target} 就是原文语言，不发送外部翻译请求。")
        return text
    output = []
    for segment in chunks(text):
        if not segment.strip():
            output.append(segment)
            continue
        try:
            await step("Engine", "请求免费翻译", f"将当前分句从 {source} 翻译为 {target}；调用 MyMemory，消耗免费服务额度，不调用大模型。")
            response = await client.get("https://api.mymemory.translated.net/get", params={
                "q": segment, "langpair": f"{CODES[source]}|{CODES[target]}", "mt": "1",
            })
            if response.status_code == 429:
                raise FreeTranslationError("免费翻译服务额度已用完或请求受限，请稍后再试。")
            response.raise_for_status()
            data = response.json()
            if data.get("quotaFinished") or str(data.get("responseStatus")) == "429":
                raise FreeTranslationError("免费翻译服务今日额度已用完，请稍后再试。")
            if str(data.get("responseStatus")) != "200":
                raise FreeTranslationError("免费翻译服务暂不支持此请求，请缩短原文或稍后再试。")
            value = data.get("responseData", {}).get("translatedText")
            if not isinstance(value, str) or not value.strip():
                raise FreeTranslationError("免费翻译服务未返回有效译文，请稍后再试。")
            # 翻译记忆的首选项偶尔只是重复原文；优先选择同句、同目标语言的实际译文。
            if value.casefold().strip() == segment.casefold().strip():
                for match in data.get("matches", []):
                    candidate = match.get("translation")
                    if (str(match.get("segment", "")).casefold().strip() == segment.casefold().strip()
                            and str(match.get("target", "")).split("-")[0] == target
                            and isinstance(candidate, str) and candidate.strip()
                            and candidate.casefold().strip() != segment.casefold().strip()):
                        value = candidate
                        break
            # 避免把服务配额提示当作正常译文。
            if value.upper().startswith("MYMEMORY WARNING:"):
                raise FreeTranslationError("免费翻译服务暂时受限，请稍后再试。")
            prefix = segment[:len(segment)-len(segment.lstrip())]
            suffix = segment[len(segment.rstrip()):]
            output.append(prefix + html.unescape(value).strip() + suffix)
        except (httpx.HTTPError, ValueError, TypeError, AttributeError):
            raise FreeTranslationError("无法连接免费翻译服务或响应无效，请检查网络后重试。") from None
    separator = " " if target == "en" else ""
    return separator.join(output)


async def compare_free(text: str, source: str, pair: str) -> dict:
    if len(text) > 1000:
        raise FreeTranslationError("免费模式每次最多 1000 字符，请缩短原文后重试。")
    left, right = PAIRS[pair]
    await step("Skill", "读取组合 Skill", f"读取 {pair} 技能文件以展示组合规则；免费引擎不理解或执行大模型指令。", resource=f"skills/{pair}/SKILL.md")
    load_skill(left, right)  # 保留相同的组合路由；不声称免费引擎能执行模型指令。
    async with httpx.AsyncClient(timeout=25, follow_redirects=False) as client:
        # 两种目标语言均直接从原文翻译，原文语言不访问外部服务。
        left_text = await translate_text(client, text, source, left)
        right_text = await translate_text(client, text, source, right)
    target = right if source == left else left
    async with connect_mcp() as session:
        glossary = await call_lookup(session, {"query":text, "source":source, "target":target})
    await step("Agent", "整理词义与用法", "由程序将 MCP 命中的本地资料整理为说明；这不是大模型生成的语义分析。")
    notes = [entry["note"] for entry in glossary["matches"]]
    references = [f"{entry['id']}：{' / '.join(entry['target_terms'])}" for entry in glossary["matches"]]
    return {
        "pair":pair, "skill":pair, "engine":"MyMemory 免费翻译", "mode":"free",
        "left_language":left, "right_language":right, "left":left_text, "right":right_text,
        "explanation":"免费联网翻译模式：以上为机器译文；未使用大模型，不生成逐句语义或语气分析。",
        "keywords":"\n".join(notes) if notes else "本地术语表未命中，暂无可提供的词义和用法说明。",
        "references":"\n".join(references) if references else "本次 MCP 本地术语查询未命中。",
    }
