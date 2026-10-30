# 言间 · 中日英翻译 Agent：网页版 v3.1.0 + Skills + MCP

## 版本信息

当前功能版本为 **v3.1.0（可调宽流程调试版）**。完整历史见 [CHANGELOG.md](CHANGELOG.md)。以下版本号记录开发阶段及对应代码提交，不代表已发布同名 Git 标签或 GitHub Release。

| 版本 | 名称 | 主要变化 | 验证结果 | 对应代码提交 |
|---|---|---|---|---|
| v3.1.0 | 可调宽流程调试版 | 半屏可拖拽流程面板、底部固定按钮、一步到底 | 41 项测试通过 | [0be2caa](https://github.com/chunyuhan0618-svg/Test-Agent-Skill-MCP/commit/0be2caa4645569198384957c3f63b6d8addad6f8) |
| v3.0.0 | 流程调试版 | 可选右侧流程图、真实下一步、Agent/Skill/MCP 标识及代码行 | 39 项测试通过 | [67d14da](https://github.com/chunyuhan0618-svg/Test-Agent-Skill-MCP/commit/67d14dac1c8401b131b23b79f59e02568d9189a7) |
| v2.1.0 | 免费翻译版 | 模型与 API Key 改为选填，默认免费翻译 | 28 项测试通过 | [f858aa9](https://github.com/chunyuhan0618-svg/Test-Agent-Skill-MCP/commit/f858aa9bbd1461b33fbe8347bb97337b68ac9a4d) |
| v2.0.1 | 错误提示修正版 | 区分余额、消费/用量上限与请求限速 | 10 项网页相关测试通过 | [aa0b05d](https://github.com/chunyuhan0618-svg/Test-Agent-Skill-MCP/commit/aa0b05df0c233fa18c44f9543c3801706dad681a) |
| v2.0.0 | 网页版 | 三栏对照、组合勾选、模型选择与 Key 输入 | 20 项测试通过 | [dab1e10](https://github.com/chunyuhan0618-svg/Test-Agent-Skill-MCP/commit/dab1e10c020f77103a67226f37515a18886d2da3) |
| v1.0.0 | 命令行版 | 一个 Agent、三个双向 Skill、真实 MCP 术语查询 | 11 项测试通过 | [2fc5751](https://github.com/chunyuhan0618-svg/Test-Agent-Skill-MCP/commit/2fc5751ea45c93ee2fa294e4d0d645b572f06f07) |

## v3.1.0 更新

- 右侧流程面板默认约占页面一半，可拖拽中间分隔条调整宽度；也支持键盘方向键调整。
- **下一步 → / 一步到底 / 结束调试** 固定在面板底部，不随上方流程、代码和 Skill 内容滚走。
- 点击 **一步到底**，自动执行当前步骤及本次所有已勾选组合的后续步骤，仍保留真实流程与代码记录；运行中可结束调试。
- 保留默认关闭的流程选项、单步模式、免费翻译和可选模型/Key；本版没有新增 Python 依赖。

更新后重启 `web.py` 并刷新页面。详见 **[v3.1.0 使用说明](docs/web-v3.1.md)**。本次 41 项测试通过，浏览器已验证拖拽、底部按钮可见及一次点击完成三组真实免费翻译。

## V3 流程调试快速开始

第三版新增可选的 **显示流程图 · 单步调试**。默认关闭，普通翻译不受影响。

1. 按下方命令更新并运行 `web.py`，刷新浏览器页面。
2. 勾选“显示流程图 · 单步调试”，选择需要的翻译组合后开始。
3. 右侧按真实执行顺序显示 **Agent / Skill / MCP / Engine** 节点。
4. 程序在关键步骤前暂停，点击 **下一步** 才继续；代码区显示真实文件名、行号并高亮下一条操作。
5. Skill 节点可以查看指令原文；点击历史节点可以回看代码。
6. 点击“结束调试”或取消流程选项可停止后续步骤。免费模式仍无需模型和 Key。

这是关键步骤单步执行器，不是逐条 Python 语句的完整调试器。免费模式中的 Agent 表示程序编排，不表示大模型推理。调试时逐组执行，普通模式仍并行处理选中组合。

完整架构、接口和验证说明见 **[V3 流程调试说明](docs/web-v3.md)**。本次 39 项测试通过，已在浏览器验证免费翻译、真实 MCP、暂停/放行、取消恢复及代码展示；线上大模型路径使用真实 SDK 配合本地响应替身验证。

## 网页版安装与启动

第二版已提供本地独立运行的网页：**左侧中日对照、中间中英对照、右侧日英对照**。三组默认勾选，可取消任意组合；只会为选中的组合调用 Agent、Skill 和 MCP。

已安装初版的 Windows 用户，在 PowerShell 执行：

```powershell
cd C:\AI-Study\Test-Agent-Skill-MCP
git pull --ff-only
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe web.py
```

浏览器打开 **[http://127.0.0.1:8000](http://127.0.0.1:8000)**。保持终端运行，按 Ctrl+C 停止。端口被占用时，运行 `python web.py --port 8002` 并打开对应地址。

1. 默认“不指定模型 · 免费翻译”，无需选择模型。
2. API Key 可以留空。只有同时填写模型与 Key 才进入大模型模式，无需填写 `.env`。
3. 输入原文，并选择中文、日文或英文作为原文语言。
4. 保持所需对照组合勾选，点击“开始对照翻译”。
5. 每栏显示两种语言、意思解释、关键词与用法、术语参考。

一份原文可生成三组对照。例如中文原文的日英栏会直接生成日文、英文，而不先串行转译。该栏使用日英 Skill 分析对应表达。每栏独立生成，因此不同栏中的同语言译文可能存在措辞差异。

**默认免费模式**通过 MyMemory 联网翻译，无需模型和 API Key。每次原文最多 1000 字符，服务有每日免费额度；会将原文发送至 MyMemory。意思解释区域明确标注机器翻译，关键词与用法来自 MCP 本地术语表；不提供大模型级的逐句语义分析。

**可选大模型模式**同时选择 OpenAI 模型并填写 Key 后启用。下拉框中的预置模型不保证你的账号都有权限；所选模型需要支持 Responses、function calling、Structured Outputs。API Key 仅在当前页面及请求内存中使用，不写入磁盘、Cookie 或 localStorage；原文、选中的 Skill 和查询结果会发送至 OpenAI。页面关闭或刷新后需重新输入。大模型模式失败不会悄悄把内容改送免费服务；需要手动选择免费模式。

这是带本地 Python 后端的独立网页应用，无需 Codex、Node.js 或前端构建；免费模式需要联网，但不需要 API Key。默认只监听本机地址，不是公开部署服务，也不是无需 Python 的 exe。

完整架构、接口和验证说明见 **[V2 网页版说明](docs/web-v2.md)**。下文保留初版 CLI 的使用方法。

一个 Python 命令行项目，演示 **一个 Agent 根据语言方向加载三个 Skill 之一，再通过真实 MCP 查询术语，并调用模型完成翻译和意思解释**。

| 组件 | 本项目中的实现 | 解决的问题 |
|---|---|---|
| Agent | `agent.py` | 组织指令、调用模型、执行工具、回传结果、结束任务 |
| Skills | `skills/zh-ja`、`zh-en`、`en-ja` | 不同语言组合各自需要哪些翻译和解释规则 |
| MCP Client | `mcp_bridge.py` | 与本地 MCP Server 通信，并适配模型工具格式 |
| MCP Server | `mcp_server.py` | 提供 `lookup_term` 查询工具 |
| 知识数据 | `data/glossary.json` | 维护固定表达和术语的候选译法、注意事项 |

**两个运行模式：**

- 正常模式：调用 OpenAI Responses API，生成译文和意思解释。需要你自己的 API 密钥和模型权限。
- `--demo`：加载真实 Skill，启动真实 MCP 子进程并查询术语，不调用模型、不生成翻译，适合先验证环境。

## 1. 框架结构

```text
Test-Agent-Skill-MCP/
├── main.py                   # 命令行入口、环境配置、错误提示
├── agent.py                  # 请求校验、Skill 加载、模型与工具循环
├── skill_router.py           # 六个方向映射到三个 Skill
├── mcp_bridge.py             # MCP 生命周期及 Responses 工具适配
├── mcp_server.py             # FastMCP 术语服务，stdio 通信
├── requirements.txt          # 运行依赖
├── requirements-dev.txt      # Skill 格式校验的可选开发依赖
├── .env.example              # 密钥和模型配置示例
├── .gitignore
├── skills/
│   ├── common.md             # 共享输出格式、忠实原意等规则
│   ├── zh-ja/SKILL.md        # 中文 ↔ 日文
│   ├── zh-en/SKILL.md        # 中文 ↔ 英文
│   └── en-ja/SKILL.md        # 英文 ↔ 日文
├── data/glossary.json        # 小型教学术语表
├── tests/test_agent.py       # 离线模型替身 + 真实 MCP 集成验证
└── docs/
    ├── walkthrough.md       # 代码级详细说明
    ├── examples.md          # 六个方向的命令与预期观察结果
    └── validation.md        # 本次验证范围及结果
```

```mermaid
flowchart TD
    U[用户：原文、源语言、目标语言、解释语言] --> CLI[main.py]
    CLI --> A[agent.py]
    A --> R[skill_router.py]
    R --> S1[zh-ja Skill]
    R --> S2[zh-en Skill]
    R --> S3[en-ja Skill]
    S1 --> I[共享规则 + 选中 Skill]
    S2 --> I
    S3 --> I
    I --> L[模型：翻译与解释]
    L -->|function_call| A
    A --> B[MCP Client / Bridge]
    B -->|stdio 协议| M[MCP Server]
    M --> G[glossary.json]
    G --> M
    M --> B
    B --> A
    A -->|function_call_output| L
    L --> O[最终译文和意思解释]
```

Skill 以文本指令进入模型上下文。它不是独立模型，也不是调用后会自动执行的函数。MCP 是本地 Client 与 Server 之间的协议；模型 API 不会直接访问本机 stdio Server。

## 2. 安装

需要 **Python 3.11 或更高版本**，建议使用 Python 3.12。

### Windows PowerShell

```powershell
git clone https://github.com/chunyuhan0618-svg/Test-Agent-Skill-MCP.git
cd Test-Agent-Skill-MCP
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

后续命令使用 `python` 时，请替换为 `.\.venv\Scripts\python.exe`，或先激活虚拟环境。直接使用解释器路径不需要更改 PowerShell 执行策略。

若提示 `Python was not found`，先从 [Python 官方网站](https://www.python.org/downloads/windows/) 安装 Python，勾选 **Add python.exe to PATH**，关闭并重新打开 PowerShell，运行 `python --version` 验证。若只有 `py` 可用，也可以使用 `py -3.12 -m venv .venv`。

### macOS / Linux

```bash
git clone https://github.com/chunyuhan0618-svg/Test-Agent-Skill-MCP.git
cd Test-Agent-Skill-MCP
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

本教学代码固定使用 MCP Python SDK **1.26.0** 的 `FastMCP` / `ClientSession` 接口。请先安装仓库指定版本；升级到其他主版本需要重新核对接口，不要仅复制旧代码后安装任意版本。

## 3. 先运行无需密钥的演示

```powershell
.\.venv\Scripts\python.exe main.py --text "お疲れ様です。ご確認をお願いいたします。" --source ja --target zh --demo --verbose
```

你会看到：

```text
[skill] selected=zh-ja
[mcp] initialized; discovered=lookup_term
```

然后输出 JSON：`selected_skill` 是 `zh-ja`，`mcp_result.found` 为 `true`，命中 `otsukaresama` 和 `review-request`。这是真实 MCP 查询结果，**不是模型翻译结果**。

Server 由程序自动启动和关闭，不用再开终端运行它。直接运行 `python mcp_server.py` 时，它会等待协议输入，看起来像“没反应”，这是正常现象。

## 4. 配置并运行真实翻译

PowerShell：

```powershell
Copy-Item .env.example .env
```

macOS / Linux：

```bash
cp .env.example .env
```

编辑 `.env`：

```dotenv
OPENAI_API_KEY=你的真实API密钥
OPENAI_MODEL=gpt-4.1-mini
```

模型名称是可替换的示例。使用自己账号中可用且支持 Responses API、function calling 的模型。正常模式会向 OpenAI 发送原文、选中的 Skill 和工具结果，并产生相应 API 用量；`store=False` 不等同于所有平台数据保留政策都被关闭。不要提交 `.env`。

```powershell
.\.venv\Scripts\python.exe main.py --text "お疲れ様です。ご確認をお願いいたします。" --source ja --target zh --explain zh --verbose
```

正常模式预期包含以下四部分，具体措辞由模型生成：

```text
译文：您好，麻烦您确认一下。
意思解释：礼貌地请对方查看或核实相关内容。
关键词与用法：解释职场寒暄及请求的礼貌程度。
术语参考：说明本次实际命中的词条及语境限制。
```

这段是说明性输出示意，不是已录制的线上模型执行结果。

## 5. 参数

| 参数 | 是否必填 | 说明 |
|---|---|---|
| `--text` | 是 | 原文，1～10000 个字符 |
| `--source` | 是 | `zh`、`ja`、`en` |
| `--target` | 是 | `zh`、`ja`、`en`，必须不同于源语言 |
| `--explain` | 否 | 解释语言，默认 `zh`，独立于翻译方向 |
| `--demo` | 否 | 只验证 Skill + 真实 MCP，不调用模型 |
| `--verbose` | 否 | 在 stderr 显示加载及调用日志，包含原文和查询结果 |

第一版明确指定源语言，避免短文本或纯汉字文本自动识别错误。`en → ja`、中文解释时依然加载 `en-ja`，不会加载 `zh-ja`。

## 6. Agent 如何使用 Skill 和 MCP

1. 校验请求，将源语言和目标语言组成一个无序集合。
2. 加载对应一个 `SKILL.md` 和共享 `common.md`。
3. 通过当前 Python 解释器启动 MCP Server 子进程，完成初始化并发现工具。
4. 将工具的名称、说明、JSON Schema 转换为 Responses API 的 function 定义。
5. 发送 Skill 指令和翻译请求。**首轮强制调用 `lookup_term`**，让教学过程一定能观察到 MCP。
6. 收到模型 `function_call` 后，校验工具名称和翻译方向，经 MCP 执行查询。
7. 用相同 `call_id` 回传 `function_call_output`，保留完整历史（包括推理项）。
8. 模型可以继续查询或生成答案；最多调用模型 5 轮，每次 API 请求允许一次 SDK 重试。

详细解释见 [代码导读](docs/walkthrough.md)，六向命令见 [运行示例](docs/examples.md)。

## 7. 验证

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

测试覆盖六向路由、真实 MCP 子进程查询、未命中、无效参数、工具结果回传、未知工具、方向错误、轮数限制、响应不完整、演示模式和缺少配置。模型输出由替身提供，不消耗 API；因此这些测试不证明线上模型可用性或翻译质量。实际翻译验收需要配置自己的密钥后运行正常模式。

还包含使用真实 OpenAI SDK、本地 HTTP 响应替身和真实 MCP 的契约测试，验证工具定义、模型响应解析和历史序列化。已执行结果见 [验证记录](docs/validation.md)。

## 8. 常见问题

| 问题 | 处理 |
|---|---|
| 提示缺少 `mcp` / `openai` | 使用安装依赖时的同一个虚拟环境解释器运行 |
| 演示成功，正常模式失败 | 检查 API 密钥、网络、模型名称和账号权限 |
| 401 / 429 / 模型不存在 | 分别检查认证、额度或速率限制、模型访问权限 |
| 术语未命中 | 正常情况；模型仍可翻译；小词表不是完整词典 |
| 首轮总是调用工具 | 教学设计；可将 `tool_choice` 改为 `auto` 观察自主查询 |
| 同语言输入报错 | 本例处理跨语言翻译；尚未实现同语言润色 |
| 日文输出乱码 | 使用支持 UTF-8 的终端；必要时用 `python -X utf8 main.py ...` |
| 出现 `IncompleteFieldDefinitionWarning: lifespan` | 本次依赖组合下 MCP 的设置模型触发该警告，演示和测试均通过；它不是术语查询失败 |

## 9. 官方参考

- [OpenAI function calling](https://developers.openai.com/api/docs/guides/function-calling)：本例工具调用及结果回传的接口依据。
- [MCP Python SDK 1.26.0](https://github.com/modelcontextprotocol/python-sdk/tree/v1.26.0)：本例固定版本的代码参考。
- [Agent Skills 格式](https://agentskills.io/specification)：`SKILL.md` 的基础组织方式。本项目自行实现路由和文本加载，不依赖客户端内置发现机制。
