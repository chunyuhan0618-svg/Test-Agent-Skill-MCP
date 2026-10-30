# 第二版：本地独立运行的三栏网页

## 最新更新：模型与 Key 改为选填

默认选择“不指定模型 · 免费翻译”，Key 留空也可直接翻译。服务端在两项均已填写时调用原有 OpenAI Agent；任意一项留空时调用 `free_translation.py`。前端和后端都已移除必填限制。

免费模式使用 [MyMemory 官方 GET 接口](https://mymemory.translated.net/doc/spec.php)，无需认证。原文会发送到 MyMemory，仍然需要联网，并非离线本地模型。只使用查询接口，不调用提交翻译记忆的 `set` 或 `import` 接口，不传任何用户 Key 给免费服务。

根据 [官方额度说明](https://mymemory.translated.net/doc/usagelimits.php)，匿名免费用量目前为每天 5000 字符；服务额度和可用性由供应商控制。应用限制免费模式每次原文最多 1000 字符，每段最多 500 UTF-8 字节；三栏翻译会消耗多次译文查询用量，不保证每天可提交五次完整三栏任务。

免费模式仍按组合加载技能文件并通过真实 MCP 查询术语，但没有模型解释 Skill 指令。模型级的逐句意思、语气分析不会被伪造：页面明确标注机器译文，关键词和用法仅来自本地已命中的术语资料。未命中时说明暂无本地解释。

本次更新后 **28 项测试通过**，包括模型/Key 省略及部分填写、免费翻译六方向请求、UTF-8 分段、上游限额与无效响应、原文保留、免费模式不调用 OpenAI、同句目标语言候选筛选，以及真实 MCP 说明。浏览器留空模型和 Key 后，三组对照均真实返回结果；公开示例 Hello! 返回“您好！”及“こんにちは！”。免费服务质量低于大模型，可能出现不准确的固定表达或原文残留，不能将成功响应视为译文质量保证。下文的大模型调用结构说明仅适用于同时配置模型与 Key 的模式。

## 1. 需求与实现

| 需求 | 实现 |
|---|---|
| 独立网页版 | `python web.py` 启动，浏览器访问，不依赖 Codex |
| 三组同屏 | 中日、中英、日英固定按左、中、右排列；窄屏自动纵向排列 |
| 可选按钮 | 三个复选按钮默认全选；取消的栏位保留位置并标记未启用 |
| 模型下拉菜单 | GPT-4.1 mini、GPT-4.1、GPT-4o mini 预置项及自定义 ID |
| API Key 输入 | 选填密码框，支持显示/隐藏；仅当前页面与请求使用 |
| 含义解释 | 每栏输出两种语言、中文解释、关键词用法和术语参考 |

## 2. 安装及启动

已有初版：

```powershell
cd C:\AI-Study\Test-Agent-Skill-MCP
git pull --ff-only
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe web.py
```

首次安装：

```powershell
git clone https://github.com/chunyuhan0618-svg/Test-Agent-Skill-MCP.git
cd Test-Agent-Skill-MCP
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe web.py
```

打开 `http://127.0.0.1:8000`。启动过程不自动安装软件、不自动打开浏览器。macOS/Linux 可用 `.venv/bin/python web.py`。自定义端口：`python web.py --port 8002`。

直接输入原文、选择原文语言和组合即可免费运行。若需大模型分析，再填写 Key 并选择模型。网页与 CLI 配置分开：网页不读取 `.env` 的密钥，CLI 仍使用 `.env`；本次选填改动针对网页版，CLI 保留原有配置方式。

## 3. 新增文件

```text
web.py                  # Starlette 后端、输入校验、错误处理、本机启动
comparison.py           # 双语对照任务，复用已有模型工具循环
static/
  index.html            # 三栏工作台结构
  style.css             # 桌面三栏及手机单栏布局
  app.js                # 选择组合、请求、加载状态、结果渲染
tests/
  test_web.py           # API 与对照逻辑测试
  ui_fixture.py         # 无线上调用的界面测试服务
```

原有 `agent.py` 新增可选 `output_schema` 参数，CLI 不传该参数，所以继续输出自然语言文本。网页版传入 JSON Schema，从而把两种语言和解释放入稳定的页面区域。

## 4. 一次翻译怎样执行

```text
浏览器：一份原文 + 原文语言 + 模型 + API Key + 勾选组合
  ├─ 选中 zh-ja → POST /api/compare → zh-ja Skill → MCP → 两种语言与解释
  ├─ 选中 zh-en → POST /api/compare → zh-en Skill → MCP → 两种语言与解释
  └─ 选中 en-ja → POST /api/compare → en-ja Skill → MCP → 两种语言与解释
```

浏览器只遍历勾选项，各栏并行请求。同一栏在收到结果后立即显示；其他栏继续等待。某一栏失败不会抹掉已完成的栏位。全部取消后按钮禁用。运行过程中锁定输入及勾选项，避免结果与修改后的设置混淆。

每个请求只允许一个 `pair`，服务端没有默认“翻译所有栏”的分支。因此取消的组合不是仅隐藏结果，而是不会发起该栏翻译。

### 对照 Skill 与原文语言

`comparison.py` 使用 `PAIRS` 选择对应 Skill：

```python
PAIRS = {
    "zh-ja": ("zh", "ja"),
    "zh-en": ("zh", "en"),
    "en-ja": ("ja", "en"),
}
```

`en-ja` 保留初版技能文件名，但网页显示顺序是日文、英文。

如果原文是中文，日英栏仍加载 `en-ja`；额外的网页指令明确要求从中文原文直接生成日文与英文，并使用日英 Skill 分析二者的语气与用法。它是同一原文的双语生成任务，不是另一个中转翻译 Agent。

MCP 仍从原文语言查询术语，选择对照组合中的一个不同语言作为目标词条语言。小术语表只能提供参考，不保证每次命中，也不代表两种输出语言的全部术语都经过词典验证。

如果对照中某一语言就是原文语言，后端会用原文覆盖对应结果字段，保证原文逐字保留。

### 结构化输出

模型返回五个字符串字段：

```json
{
  "left": "左侧语言文本",
  "right": "右侧语言文本",
  "explanation": "中文意思解释",
  "keywords": "中文关键词和用法解释",
  "references": "实际命中的术语参考，或说明未命中"
}
```

`ComparisonResult.model_json_schema()` 生成结构，`run_model_loop()` 将它作为 Responses API `text.format` 发送；`model_validate_json()` 再校验返回内容。模型仍先执行原有工具循环，首轮查询 MCP，再生成最终 JSON。

接口随后附加 `pair`、`skill` 和语言代码，前端用 `textContent` 渲染，不将模型文本当作 HTML 执行。

## 5. 模型与 Key

大模型模式提供的是 OpenAI 模型选择；免费模式使用 MyMemory，不需要配置模型。未实现 Gemini、Claude 或第三方兼容模型接口。自定义项允许填写同一 OpenAI API 中自己有权限的模型 ID。

每个请求创建独立 OpenAI Client、MCP 会话。Key 不写入环境变量或共享全局变量，不在结果和错误信息中返回。错误响应使用固定提示，区分权限问题、额度限制、模型不支持及超时。

网页正常翻译会产生 API 用量。默认三栏分别运行 Agent，通常每栏至少需要工具调用前、后两次模型请求；相同语言的译文不跨栏缓存，以保留各自 Skill 的效果。减少勾选项可以减少调用。

API Key 随 POST 正文发送到本机后端，再由 SDK 用于请求 OpenAI。静态页面不引用第三方脚本或字体。默认只绑定 127.0.0.1，拒绝其他来源的浏览器请求；关闭缓存，限制正文大小。若未来要公开部署，需要另行设计 HTTPS、认证、并发和额度控制，本版的本机启动不涉及公开部署。

### HTTP 429：先区分额度与限速

- `insufficient_quota` / `billing_hard_limit_reached`：检查 [API Billing](https://platform.openai.com/settings/organization/billing/overview)、可用余额、Key 所属组织/项目和用量限制；等待或重复点击通常无效。
- `credit_balance_exhausted`：预付余额耗尽，检查 API Billing。
- `organization_spend_limit_exceeded` / `project_spend_limit_exceeded`：组织或项目消费上限已达到，核对对应设置。
- `organization_usage_limit_exceeded`：组织用量上限已达到，核对或申请提高限制。
- `rate_limit_exceeded` / `slow_down`：在 [Limits](https://platform.openai.com/settings/organization/limits) 查看限制，按服务端等待提示稍后重试，先只勾选一组并缩短原文。
- 未返回可识别代码：页面保留“无法确定”提示，不仅凭 429 就判断账户没余额。

原版合并了两种提示；更新后按 SDK 的错误 code/type 分类，绝不向页面回显原始错误、请求正文或 Key。分类回归测试使用真实 SDK 错误类型与模拟响应，不调用线上 API，也不能读取你的账户余额。

## 6. 验证

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

本次执行 **20 项测试全部通过**，覆盖初版 11 项和新版 9 项：

- 页面与静态文件可访问。
- 单个 API 请求仅执行对应组合。
- 三个组合分别加载自己的 Skill，包括第三语言输入。
- 无效输入、超长正文和跨来源请求不会调用 Agent。
- API Key 在校验对象表示及错误返回中被隐藏。
- 不同请求使用各自凭据。
- 初版真实 MCP 和 OpenAI SDK 本地契约测试继续通过。

前端 JavaScript 已通过 `node --check` 语法检查；Node 只用于开发验证，用户运行不需要安装。

浏览器手动验证：默认三组勾选、示例填充、原文语言同步、自定义模型输入、取消日英栏、全部取消禁用提交、只请求两栏、恢复三栏结果显示、失败提示与按钮恢复。390px 窄屏验证为单栏布局，无横向溢出；浏览器未记录脚本错误。结果展示使用下面的模拟服务，不代表线上译文质量验证。

### 无需真实 Key 的界面测试

```powershell
.\.venv\Scripts\python.exe tests/ui_fixture.py
```

打开 `http://127.0.0.1:8001`，输入任意测试字符串作为 Key，例如 `ui-test-only`。该服务返回明确标注的固定模拟译文，不调用模型或 MCP，不用于真实翻译。它只打印请求的组合 ID，方便确认取消勾选后没有对应请求。

自定义模型填写 `test-error` 可验证失败提示；真实服务 `web.py` 没有这个特殊行为。

当前环境仍未配置真实 API Key，因此没有进行 V2 线上翻译验收。已有测试证明本地服务、Skill 路由、MCP 与 SDK 适配可工作；正常翻译需由自己的账号配置后验证。
