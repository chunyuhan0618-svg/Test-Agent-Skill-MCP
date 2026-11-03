# 六个方向的运行示例

## English

CLI examples cover all six directions across Chinese, Japanese and English. Run commands from the project root with the installed virtual environment. --demo checks MCP only; omit it for configured model translation.

## 日本語

CLI の例で中国語・日本語・英語の6方向を確認できます。プロジェクトルートで仮想環境の Python を使います。--demo は MCP 確認のみで、モデル設定後に外すと翻訳します。

## 中文

本文列出中日英六向 CLI 示例；从项目根目录使用虚拟环境 Python 运行，--demo 仅验证 MCP，配置模型并去掉该参数才执行模型翻译。

---

以下命令在已激活的虚拟环境中执行。Windows 也可把 `python` 替换为 `.\.venv\Scripts\python.exe`。正常模式需要 `.env`；在命令末尾添加 `--demo` 就只验证 Skill 和 MCP。

| 方向 | 应选 Skill | 测试重点 |
|---|---|---|
| zh → ja | zh-ja | 自然的职场请求 |
| ja → zh | zh-ja | 寒暄与礼貌程度 |
| zh → en | zh-en | 跟进的自然表达 |
| en → zh | zh-en | follow up 的含义 |
| en → ja | en-ja | 电源插座的对应表达 |
| ja → en | en-ja | 和制英语解释 |

## 中文 → 日文

```bash
python main.py --text "麻烦您确认一下。" --source zh --target ja --explain zh --verbose
```

观察 `selected=zh-ja`；整句查询能命中 `review-request`。正常翻译应保持礼貌请求，具体敬语形式取决于模型判断。

## 日文 → 中文

```bash
python main.py --text "お疲れ様です。ご確認をお願いいたします。" --source ja --target zh --explain zh --verbose
```

观察 `selected=zh-ja`；整句查询可命中两个词条。解释应说明寒暄不一定逐字译成“辛苦了”。

## 中文 → 英文

```bash
python main.py --text "请明天跟进这个问题。" --source zh --target en --explain zh --verbose
```

观察 `selected=zh-en`；整句查询能命中 `follow-up`。

## 英文 → 中文

```bash
python main.py --text "Could you follow up tomorrow?" --source en --target zh --explain zh --verbose
```

观察 `selected=zh-en`；解释应区分委婉请求和字面能力询问。

## 英文 → 日文，中文解释

```bash
python main.py --text "Where is the power outlet?" --source en --target ja --explain zh --verbose
```

观察 `selected=en-ja`，而不是 `zh-ja`；解释语言不参与 Skill 选择。

## 日文 → 英文，英文解释

```bash
python main.py --text "コンセントはどこですか。" --source ja --target en --explain en --verbose
```

观察 `selected=en-ja`；词条指出コンセント不能按字面译成 consent。

## 未命中的情况

```bash
python main.py --text "The sky is clear today." --source en --target zh --demo --verbose
```

预期 `found=false`、`matches=[]`。移除 `--demo` 后，模型应使用自己的语言能力继续翻译，并说明词表未命中。

## 无效方向

```bash
python main.py --text "hello" --source en --target en --demo
```

预期非零退出并提示源语言与目标语言不能相同。

## 如何读正常模式日志

```text
[skill] selected=en-ja
[mcp] initialized; discovered=lookup_term
[model] round=1
[mcp] call lookup_term ...
[mcp] result ...
[model] round=2
```

这是协议步骤的示意；实际查询词和轮数由模型决定。日志记录调用，不展示或要求模型输出隐藏推理过程。
