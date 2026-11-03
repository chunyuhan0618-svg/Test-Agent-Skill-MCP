# 逐文件代码导读

## English

Code walkthrough: main.py validates CLI options, agent.py orchestrates model/tool rounds, skill_router.py selects pair rules, and mcp_bridge.py connects mcp_server.py to the local glossary.

## 日本語

コードの解説です。main.py が CLI を受け、agent.py がモデルとツールを制御し、skill_router.py が規則を選び、mcp_bridge.py が mcp_server.py と用語集に接続します。

## 中文

代码导读：main.py 接收 CLI，agent.py 编排模型与工具循环，skill_router.py 选择规则，mcp_bridge.py 连接 mcp_server.py 及本地术语表。

---

## 1. 先区分四种东西

`agent.py` 是执行程序；`SKILL.md` 是指导模型的文字；`lookup_term` 是可执行工具；MCP 是程序访问该工具的协议。

同一个术语表可以服务三个 Skill。工具的输出提供证据或候选，最终译法仍由模型结合上下文判断。Skill 中写“先查术语”只是模型指令；本例还通过首轮 `tool_choice` 在接口层要求调用工具，便于教学观察。

## 2. main.py：接收参数并组合请求

```python
request = TranslationRequest(args.text, args.source, args.target, args.explain)
```

`TranslationRequest` 是一个 dataclass，用明确字段传递数据，避免混淆翻译目标与解释语言。CLI 限制语言选项，`validate()` 再校验文本长度、语言和方向，使直接从 Python 调用也接受同样检查。

`load_dotenv(ROOT / ".env")` 从项目路径加载配置；已有系统环境变量优先。Python 的异步入口使用 `asyncio.run()`，因为 MCP 通信和模型网络请求都使用异步接口。

正常输出进入 stdout；调用日志进入 stderr。这使你可以将最终结果重定向到文件：

```powershell
.\.venv\Scripts\python.exe main.py --text "Please follow up tomorrow." --source en --target zh --verbose > result.txt
```

`result.txt` 不会混入 Agent 的调试日志。`--verbose` 会展示原文和术语结果，使用真实敏感内容时应考虑日志去向。

## 3. skill_router.py：六个方向，三个 Skill

```python
SKILLS = {
    frozenset({"zh", "ja"}): "zh-ja",
    frozenset({"zh", "en"}): "zh-en",
    frozenset({"en", "ja"}): "en-ja",
}
```

`frozenset` 是不可变集合，可作字典键，且不关心元素顺序。所以 `zh → ja` 与 `ja → zh` 都选择 `zh-ja`。具体方向仍保留在请求里，模型据此选择 Skill 内的方向规则。

路由使用固定白名单，用户输入不能构造任意文件路径。每次只读共享规则和选中 Skill，不会把三个 Skill 全部塞进上下文。

```python
return name, common + "\n\n" + specific
```

返回技能名称便于记录日志；返回拼接后的文字供模型的 `instructions` 参数使用。本例不解析 YAML frontmatter：文件头作为普通文字一起传给模型。这是有意保留的最小实现，并非一个完整技能管理平台。

## 4. Skill：把语言组合特有的决策写出来

三个 Skill 都有 `name` 和 `description`，正文按翻译方向组织。

- `zh-ja`：日语敬语、主语省略、同形词、职场寒暄。
- `zh-en`：时态、冠词、单复数、情态词、习语。
- `en-ja`：语序、礼貌程度、和制英语、英文主语补足。

共享格式放在 `common.md`。如果想增加“给一个例句”，修改共享文件即可；如果只想让中日翻译附带假名读音，则修改 `zh-ja/SKILL.md`。这些修改影响模型指导，不改变模型权重。

`explain` 控制解释语言。例如 `source=en, target=ja, explain=zh`：译文是日文，解释是中文，选择的是 `en-ja`。

## 5. mcp_server.py：将知识查询暴露为工具

```python
@mcp.tool()
def lookup_term(query: str, source: Language, target: Language) -> dict:
```

装饰器将函数注册到 MCP Server。类型注解和 docstring 用于产生工具参数说明及 JSON Schema。`Literal["zh", "ja", "en"]` 限制语言值；Server SDK 负责根据参数结构校验输入。

查询先做 Unicode NFKC 和大小写归一化，然后判断原文是否包含某个源语言词条：

```python
if any(normalize(term) in normalized for term in entry["terms"][source]):
```

例如整句 `Please follow up tomorrow.` 包含词条 `follow up`，会命中。这里是简单子串匹配，可能有误命中，也不能理解变形、分词或同义表达；它的目的在于展示 MCP 调用，不是实现生产词典。

返回结构：

```json
{
  "found": true,
  "matches": [
    {
      "id": "follow-up",
      "source_terms": ["follow up", "follow-up"],
      "target_terms": ["跟进"],
      "note": "后续联系、追踪或处理……"
    }
  ]
}
```

查询未命中：`{"found": false, "matches": []}`。这与“工具执行失败”不同；未命中是正常的业务结果。

`mcp.run(transport="stdio")` 启动协议循环。不要在 Server 中使用普通 `print()` 打印日志，因为 stdout 已经承担协议通信。

## 6. mcp_bridge.py：真实的进程间通信

```python
params = StdioServerParameters(
    command=sys.executable,
    args=[str(ROOT / "mcp_server.py")],
    env={"PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"},
)
```

`sys.executable` 使用当前解释器，所以子进程与 Agent 使用同一虚拟环境。Server 路径是绝对路径，不依赖当前目录。这里也没有把 `.env` 或 API 密钥显式传给 Server；本地词表服务不需要密钥。

三个生命周期操作是：

1. `stdio_client()` 启动并连接子进程。
2. `ClientSession()` 建立协议会话。
3. `session.initialize()` 完成 MCP 初始化。

嵌套的 `async with` 保证任务结束和异常退出时释放会话及子进程。会话读操作设置 30 秒超时，查询另加 30 秒等待上限。

### MCP 工具怎样变成模型工具？

`session.list_tools()` 获取工具定义，其中参数字段叫 `inputSchema`。Responses API 使用 `parameters`，并要求标明 `type="function"`：

```python
{
    "type": "function",
    "name": tool.name,
    "description": tool.description or "",
    "parameters": tool.inputSchema,
    "strict": False,
}
```

本例只有简单参数类型。`strict=False` 避免直接把任意 MCP Schema 宣称为兼容 OpenAI 严格模式；工具执行前还有代码校验，Server 也会校验实际参数。复杂 Schema 的通用转换超出本例范围。

### 返回值怎样处理？

优先读取 `CallToolResult.structuredContent`。如果服务只返回文本，则读取文本并解析 JSON。`isError=true` 表示工具失败，转为异常；在模型循环里可回传为错误信息，让模型尝试纠正。

## 7. agent.py：模型与工具交替执行

正常模式先连接 MCP、发现工具，再建立 `AsyncOpenAI` 客户端。客户端超时为 60 秒，SDK 最多重试一次；模型循环最多 5 轮。这里的“轮”指一次模型请求，不是用户对话轮数。

### 第一次模型调用

```python
response = await client.responses.create(
    model=model,
    instructions=instructions,
    input=history,
    tools=tools,
    store=False,
    parallel_tool_calls=False,
    tool_choice={"type": "function", "name": "lookup_term"},
)
```

`instructions` 是共享规则与选中 Skill；`history` 以一个 JSON 格式用户请求开始。首轮要求模型选择查询参数并发出工具调用，后续轮改用 `tool_choice="auto"`。

### 模型不会直接执行 Python 函数

模型可能返回：

```json
{
  "type": "function_call",
  "name": "lookup_term",
  "call_id": "call_example",
  "arguments": "{\"query\":\"コンセント\",\"source\":\"ja\",\"target\":\"en\"}"
}
```

`arguments` 是 JSON 字符串，程序必须解析并检查：

- 工具名称必须是发现且允许的 `lookup_term`。
- 参数必须是包含 `query/source/target` 的对象。
- 查询方向必须与用户请求一致。

通过检查后，`session.call_tool()` 才经 MCP 发送给 Server。Agent 不直接导入 Server 函数作为工具使用。

### 回传工具结果

```python
history.append({
    "type": "function_call_output",
    "call_id": call.call_id,
    "output": json.dumps(result, ensure_ascii=False),
})
```

`call_id` 使模型知道这份数据对应哪次调用。代码先执行 `history.extend(response.output)`，保留模型完整输出，包括可能存在的推理项，然后才附加工具结果。

下一轮模型收到工具结果，继续查询或给出最终译文。只有没有待处理工具调用、响应完成且答案非空时，才交付答案。达到轮数上限会明确报错，不把未完成的中间文本当成结果。

## 8. Demo 和测试分别证明什么？

`--demo` 沿用路由、指令加载、MCP 初始化、工具发现及真实查询；它不进入模型循环，只输出诊断 JSON。因此 demo 成功证明本地链路可用，不代表 Skill 的语言指导已经由模型执行。

测试通过模型替身提供 `function_call` 和最终文本，以真实 MCP Server 完成中间查询。它验证参数适配、结果回传和停止条件；线上 API 的认证、模型权限、网络与翻译质量需要正常模式单独验证。

## 9. 可自行尝试的修改

1. 修改某个 Skill，比较相同文本的正常模式结果，观察语体和解释的变化。
2. 添加一个术语词条，先用 demo 确认命中，再运行真实翻译。
3. 将首轮强制 `tool_choice` 改为 `auto`，观察模型何时会自主查词。

修改 Skill 后无需训练模型；修改词表后无需修改 MCP 接口。二者分别控制方法与资料。
