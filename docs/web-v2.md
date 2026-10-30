# 第二版：本地独立运行的三栏网页

## 1. 需求与实现

| 需求 | 实现 |
|---|---|
| 独立网页版 | `python web.py` 启动，浏览器访问，不依赖 Codex |
| 三组同屏 | 中日、中英、日英固定按左、中、右排列；窄屏自动纵向排列 |
| 可选按钮 | 三个复选按钮默认全选；取消的栏位保留位置并标记未启用 |
| 模型下拉菜单 | GPT-4.1 mini、GPT-4.1、GPT-4o mini 预置项及自定义 ID |
| API Key 输入 | 密码框，支持显示/隐藏；仅当前页面与请求使用 |
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

输入 API Key、选择模型、原文语言和组合，即可运行。网页与 CLI 配置分开：网页不读取 `.env` 的密钥，CLI 仍使用 `.env`。

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

本版提供的是 OpenAI 模型选择，不是多个供应商切换；未实现 Gemini、Claude 或第三方兼容接口。自定义项允许填写同一 OpenAI API 中自己有权限的模型 ID。

每个请求创建独立 OpenAI Client、MCP 会话。Key 不写入环境变量或共享全局变量，不在结果和错误信息中返回。错误响应使用固定提示，区分权限问题、额度限制、模型不支持及超时。

网页正常翻译会产生 API 用量。默认三栏分别运行 Agent，通常每栏至少需要工具调用前、后两次模型请求；相同语言的译文不跨栏缓存，以保留各自 Skill 的效果。减少勾选项可以减少调用。

API Key 随 POST 正文发送到本机后端，再由 SDK 用于请求 OpenAI。静态页面不引用第三方脚本或字体。默认只绑定 127.0.0.1，拒绝其他来源的浏览器请求；关闭缓存，限制正文大小。若未来要公开部署，需要另行设计 HTTPS、认证、并发和额度控制，本版的本机启动不涉及公开部署。

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
