"""确定性选择语言组合；Skill 是指令文件，不是 Python 可执行函数。"""
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
