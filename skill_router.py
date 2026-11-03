"""English: Map six translation directions to three bilingual Skill files. Resolve paths from source location, and combine shared and pair-specific instructions.
日本語：6方向の翻訳を3つの対訳 Skill に対応させます。ソース位置からパスを求め、共通規則と組専用の指示を結合します。
中文：将六个翻译方向映射到三个双向 Skill；从源文件位置推导路径，组合共享规则和专用指令。
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LANGUAGES = {"zh", "ja", "en"}
SKILLS = {
    frozenset({"zh", "ja"}): "zh-ja",
    frozenset({"zh", "en"}): "zh-en",
    frozenset({"en", "ja"}): "en-ja",
}


def load_skill(source: str, target: str) -> tuple[str, str]:
    if source not in LANGUAGES or target not in LANGUAGES:
        raise ValueError("仅支持 zh、ja、en；本例要求明确指定源语言。")
    if source == target:
        raise ValueError("源语言与目标语言不能相同。")
    name = SKILLS[frozenset({source, target})]
    common = (ROOT / "skills/common.md").read_text(encoding="utf-8")
    specific = (ROOT / "skills" / name / "SKILL.md").read_text(encoding="utf-8")
    return name, common + "\n\n" + specific
