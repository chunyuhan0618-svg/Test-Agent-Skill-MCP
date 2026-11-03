# v3.5.0 — International edition / 国際版 / 国际版

## English

Start the Agent using the OS-specific installation and `web.py` commands in [README.md](../README.md). Open http://127.0.0.1:8000 . English is the default on each page load; use the header language menu for English, Chinese or Japanese. Switching is immediate and does not resend a translation or change the source language, text, credentials, pair selection, translated content, actual code or original Skill source.

`static/locales.json` is the shared three-language presentation catalog. `static/i18n.js` translates static and dynamically inserted presentation text and accessibility labels while retaining original text in WeakMaps; program state is never inferred from translated labels. Interface language is held in page memory. Same-origin API requests carry `X-UI-Language`; `ui_locale.py` isolates the language per request with ContextVar. Model explanations use the language captured when a task starts, including background debug tasks. Existing model explanations require another run to be regenerated in a new language. Free-mode glossary notes are catalog translations and switch immediately.

Python source comments and original Skill content remain source material when viewed in the debugger. Every Python module includes a specific English/Japanese/Chinese explanation. Every Markdown file has trilingual guidance; Skill rules include full English and Japanese equivalents alongside Chinese. Historical release details remain historical. Free translation still sends text to MyMemory; optional model mode sends it to OpenAI. Keys are not persisted. Node.js is only used for developer JavaScript syntax checks, not application startup.

## 日本語

起動は [README.md](../README.md) の OS 別インストールと `web.py` コマンドを参照し、http://127.0.0.1:8000 を開いてください。再読み込み時は英語が初期表示で、上部メニューから英語・中国語・日本語へ切り替えます。切替だけでは翻訳を再要求せず、原文言語・入力・キー・組選択・訳文・実際のコード・Skill 原文は変えません。

`static/locales.json` が3言語の表示辞書、`static/i18n.js` が静的・動的な表示とアクセシビリティラベルを更新します。原文を WeakMap に保持し、表示ラベルをプログラムの状態判定に使いません。表示言語はページ内メモリーで保持します。同一オリジンの API に `X-UI-Language` を付け、`ui_locale.py` の ContextVar で要求ごとに隔離します。モデルの説明は開始時の言語で生成し、既存の説明を別言語にするには再実行します。無料モードの用語説明は即時切替できます。

デバッガー内の Python と Skill は原文表示です。全 Python に内容別の3言語説明を追加し、全 Markdown に3言語の案内、Skill に同等の英語・日本語ルールを追加しました。過去の記録は維持します。無料翻訳は MyMemory、任意のモデルモードは OpenAI にデータを送信します。キーは保存しません。Node.js は開発時の構文確認のみで、アプリ実行には不要です。

## 中文

按 [README.md](../README.md) 的对应系统步骤安装并启动 `web.py`，访问 http://127.0.0.1:8000 。每次打开默认英文；页首可选择中英日，切换不会重新发送翻译请求，也不改变原文语言、输入、凭据、组合选择、译文、真实代码或 Skill 原文。

`static/locales.json` 集中维护三语文案，`static/i18n.js` 更新静态与动态显示文字及无障碍标签，用 WeakMap 保存原始文案，逻辑不依赖翻译后的显示字符串。语言仅存于当前页面内存。同源 API 请求携带 `X-UI-Language`；`ui_locale.py` 用 ContextVar 按请求隔离，后台调试继承开始时的语言。模型解释使用任务开始时的界面语言；生成后的模型说明需重新运行才能换语言，免费本地术语说明则可即时切换。

调试中的 Python 代码和 Skill 原文保持真实。每个 Python 文件均有具体三语模块说明，所有 Markdown 有三语阅读说明，Skill 增加等价英文和日文规则。历史版本保持原始事实。免费翻译仍将原文发往 MyMemory，可选模型模式发往 OpenAI，不保存 Key。Node.js 只用于开发语法检查，不是应用启动依赖。

## Verification / 検証 / 验证

- English: **46 tests passed**, including concurrent language isolation, background debug language inheritance, model prompt language, complete trilingual file coverage and existing real MCP integration. JavaScript syntax, relative Markdown links and fixed-path scans passed. Browser checks covered all three UI languages, real three-pair free translation with MCP (31 recorded steps), localized length validation messages, re-enabling pairs, unchanged translations/source code, cancellation, 1440px desktop and 390px mobile with no horizontal overflow. Browser console reported no warnings or errors. Live OpenAI translation was not called; model responses were substituted locally.
- 日本語：**46件のテストが成功**しました。並行要求の言語分離、バックグラウンド実行の言語継承、モデル指示、全ファイルの3言語説明、実際の MCP 統合を含みます。JavaScript 構文・相対リンク・固定パス検査も成功しました。3言語切替、実際の無料3組翻訳と MCP（31ステップ）、入力長エラー、組の再有効化、訳文・コード保持、キャンセル、1440px/390px の横方向はみ出しなしをブラウザーで確認しました。警告・エラーは記録されず、実際の OpenAI 呼び出しは行っていません。
- 中文：**46 项测试通过**，覆盖并发语言隔离、后台调试语言继承、模型指令语言、全部文件三语覆盖及原有真实 MCP 集成。JavaScript 语法、相对链接和固定路径扫描通过。浏览器验证三语切换、三组真实免费翻译与 MCP（31 个步骤）、输入长度提示、组合重新启用、译文和代码不变、取消、1440px 桌面和 390px 手机无横向溢出。浏览器无警告或脚本错误；未调用线上 OpenAI，模型响应使用本地替身。
