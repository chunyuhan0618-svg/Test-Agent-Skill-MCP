# Agent collaboration guide / エージェント作業ガイド / Agent 协作说明

## English

- Purpose: a Python teaching application showing how an Agent routes three bilingual Skills and calls a real local MCP terminology service. Read README.md for installation and startup.
- Work from the repository root, wherever it is cloned. Use relative paths or paths derived from source files; never commit personal machine paths.
- Inspect Git status before editing; preserve existing user changes. Submit changes to `current-draft`, unless the maintainer requests another branch.
- Web entry point: `web.py`; CLI entry point: `main.py`. The Agent starts the MCP server automatically. Skills live under `skills/`; terminology lives in `data/glossary.json`.
- Free web translation uses MyMemory over the network and local MCP notes; it does not use an LLM to interpret Skills. The optional OpenAI mode requires both model and API key. CLI `--demo` validates Skills/MCP and does not translate.
- Keep API keys out of tracked files, logs, screenshots and browser storage. `.env` is local and ignored by Git.
- Preserve real debug checkpoints: Next advances execution, Continue runs to completion, Cancel stops subsequent work. Do not replace execution with simulated progress.
- Keep the page version, README.md and CHANGELOG.md consistent. Preserve accurate historical version records. Run the relevant checks below before committing and state the validation limits.

## 日本語

- 目的：Agent が3種類の対訳 Skill を選び、実際のローカル MCP 用語サービスを呼び出す仕組みを学ぶ Python アプリです。インストールと起動は README.md を参照してください。
- クローン先は任意です。作業はプロジェクトルートで行い、相対パスまたはソースから求めたパスを使います。個人の固定ディレクトリをコミットしないでください。
- 編集前に Git の状態を確認し、既存の変更を保持します。管理者から別の指定がない限り、提出先は `current-draft` です。
- Web の入口は `web.py`、CLI は `main.py` です。MCP サーバーは Agent が自動起動します。Skill は `skills/`、用語データは `data/glossary.json` にあります。
- 無料 Web 翻訳は MyMemory への通信と MCP の用語情報を使い、LLM による Skill 解釈は行いません。OpenAI モードはモデルと API キーの両方が必要です。CLI の `--demo` は Skill/MCP の確認のみで翻訳しません。
- キーを追跡ファイル、ログ、画像、ブラウザー保存領域に残さないでください。`.env` はローカル専用で Git 対象外です。
- デバッグは実際の実行を制御します。「下一步」は次のステップ、「一步到底」は最後まで実行、「结束调试」は後続処理を停止します。見かけだけの進行に置き換えないでください。
- 画面、README.md、CHANGELOG.md の現在バージョンを一致させ、過去の記録は正確に残します。コミット前に関連する確認を行い、検証範囲を明示してください。

## 中文

- 目的：通过 Python 翻译产品学习 Agent 如何路由三个双向 Skill，并调用真实本地 MCP 术语服务。安装、启动和使用步骤见 README.md。
- 可克隆到任意目录；从项目根目录操作，使用相对路径或由源文件推导的路径，不提交个人机器的固定目录。
- 编辑前检查 Git 状态，保留用户已有修改；维护者没有另行指定时，提交到 `current-draft`。
- 网页入口为 `web.py`，命令行入口为 `main.py`；Agent 自动启动 MCP 服务。Skill 位于 `skills/`，术语表位于 `data/glossary.json`。
- 免费网页模式使用联网 MyMemory 翻译和 MCP 术语资料，不使用大模型解释 Skill；OpenAI 模式需同时提供模型和 API Key。CLI 的 `--demo` 只验证 Skill/MCP，不生成译文。
- 不把密钥写入受版本控制文件、日志、截图或浏览器存储；`.env` 只在本地使用，已被 Git 忽略。
- 保持真实调试语义：“下一步”放行步骤，“一步到底”执行至结束，“结束调试”停止后续处理；不要用模拟动画替代真实执行。
- 页面、README.md 和 CHANGELOG.md 的当前版本保持一致，历史记录保持准确；提交前执行相关检查，并说明验证范围。

## Commands / コマンド / 常用命令

Run from the repository root after installing dependencies as described in README.md.
README.md の依存関係をインストール後、プロジェクトルートで実行します。
先按 README.md 安装依赖，再从项目根目录运行。

| Action / 操作 | Windows PowerShell | macOS / Linux |
|---|---|---|
| Start web Agent / Web起動 / 启动网页 | `.\.venv\Scripts\python.exe web.py` | `.venv/bin/python web.py` |
| Tests / テスト / 测试 | `.\.venv\Scripts\python.exe -m unittest discover -s tests -v` | `.venv/bin/python -m unittest discover -s tests -v` |

Open / 開く / 浏览器访问：http://127.0.0.1:8000 。Stop / 停止：Ctrl+C。
For JavaScript changes / JavaScript 変更時 / 修改 JavaScript 时：`node --check static/app.js` and `node --check static/debug.js`。
Before commit / コミット前 / 提交前：`git diff --check`。

## Internationalization / 国際化 / 国际化

- English: maintain English, Japanese and Chinese entries in `static/locales.json`; verify both initial and dynamically inserted UI text. Do not translate user input, translation paragraphs, actual source code or original Skill source. Model explanations follow the task-start language. Add specific trilingual module guidance to new Python files and trilingual reading guidance to new Markdown files. Also check `node --check static/i18n.js` when modifying localization.
- 日本語：`static/locales.json` の英語・日本語・中国語を維持し、初期表示と動的表示を確認します。原文・訳文・実際のコード・Skill 原文は表示切替で翻訳しません。モデル説明は開始時の言語を使います。新しい Python には内容別の3言語説明、Markdown には3言語の案内を追加します。国際化変更時は `node --check static/i18n.js` も確認します。
- 中文：维护 `static/locales.json` 中英日文案，验证初始与动态文字；切换时不翻译用户输入、译文段落、真实源码和 Skill 原文。模型解释使用任务开始时的语言。新增 Python 文件需具体三语模块说明，新增 Markdown 需三语阅读说明；国际化变更也检查 `node --check static/i18n.js`。

## Project keywords / プロジェクトの検索用語 / 项目检索关键词

**English:** AI agent tutorial; Agent Skills; SKILL.md; Model Context Protocol (MCP); Python AI agent example; MCP client/server; stdio; tool calling; function calling; OpenAI Responses API; Chinese Japanese English translator; bilingual comparison; translation explanation; language learning; workflow visualization; step-by-step debugging; internationalization (i18n); local web app; free online translation without an API key.

**日本語：** AIエージェント入門、Agent Skills、MCP 学習、Model Context Protocol、Python サンプル、MCPクライアント・サーバー、ツール呼び出し、関数呼び出し、OpenAI Responses API、中国語・日本語・英語の翻訳、対訳比較、意味と用法、語学学習、フロー可視化、ステップ実行、国際化、多言語Webアプリ、APIキー不要の無料オンライン翻訳。

**中文：** AI 智能体教程、Agent Skills 技能开发、MCP 模型上下文协议、Python 示例、MCP 客户端服务器、工具调用、函数调用、OpenAI Responses API、中日英翻译、双语对照、词义与用法解释、语言学习、流程可视化、单步调试、国际化 i18n、多语言网页、无需密钥的免费联网翻译。

English: Use accurate terminology when maintaining descriptions; keep the distinction between free online translation and optional LLM mode. 日本語：説明には実装に合う用語を使い、無料オンライン翻訳と任意の LLM モードを区別してください。中文：维护说明时使用与实际功能一致的关键词，区分免费联网翻译与可选大模型模式。
