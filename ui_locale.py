"""English: Keep display language in a ContextVar so concurrent requests and background debug tasks do not mix explanation languages.
日本語：表示言語を ContextVar に保持し、並行要求やバックグラウンドのデバッグ間で説明言語が混ざるのを防ぎます。
中文：用 ContextVar 保存界面语言，避免并发请求和后台调试任务的解释语言串用。
"""
from contextvars import ContextVar

UI_LANGUAGE = ContextVar("ui_language", default="zh")
