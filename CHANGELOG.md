# 版本记录

本项目采用以下版本号记录已确认的开发阶段。所有阶段日期均为 **2026-10-30（日本时间）**。当前功能版本：**v2.1.0**。

表中的链接指向各阶段完成时的不可变代码提交。本文件是版本说明，不代表已创建同名 Git 标签或正式 GitHub Release；文档维护提交也不会改变上述功能版本对应的代码提交。

| 版本 | 名称 | 主要变化 | 验证结果 | 对应代码提交 |
|---|---|---|---|---|
| v2.1.0 | 免费翻译版 | 模型与 API Key 改为选填，默认免费翻译 | 28 项测试通过 | [f858aa9](https://github.com/chunyuhan0618-svg/Test-Agent-Skill-MCP/commit/f858aa9bbd1461b33fbe8347bb97337b68ac9a4d) |
| v2.0.1 | 错误提示修正版 | 区分余额、消费/用量上限与请求限速 | 10 项网页相关测试通过 | [aa0b05d](https://github.com/chunyuhan0618-svg/Test-Agent-Skill-MCP/commit/aa0b05df0c233fa18c44f9543c3801706dad681a) |
| v2.0.0 | 网页版 | 三栏对照、组合勾选、模型选择与 Key 输入 | 20 项测试通过 | [dab1e10](https://github.com/chunyuhan0618-svg/Test-Agent-Skill-MCP/commit/dab1e10c020f77103a67226f37515a18886d2da3) |
| v1.0.0 | 命令行版 | 一个 Agent、三个双向 Skill、真实 MCP 术语查询 | 11 项测试通过 | [2fc5751](https://github.com/chunyuhan0618-svg/Test-Agent-Skill-MCP/commit/2fc5751ea45c93ee2fa294e4d0d645b572f06f07) |

## v2.1.0 — 免费翻译版

日期：2026-10-30。对应提交：[f858aa9](https://github.com/chunyuhan0618-svg/Test-Agent-Skill-MCP/commit/f858aa9bbd1461b33fbe8347bb97337b68ac9a4d)。

- 网页中的大语言模型与 API Key 均改为选填，默认“不指定模型 · 免费翻译”。
- 未指定模型或未填写 Key 时，通过 MyMemory 免费联网翻译；两项均填写时使用原有 OpenAI Agent。
- 保留中日、中英、日英三组对照及勾选功能；取消的组合不发起翻译。
- 免费模式通过真实 MCP 查询本地术语，提供已命中的关键词和用法资料；不伪造大模型逐句分析。
- 增加 UTF-8 字节分段、多句拆分、免费服务错误处理，以及原文回显时的同句目标语言候选筛选。
- 验证：28 项测试通过；浏览器在模型和 Key 留空时完成三栏真实翻译。

限制：免费模式需要联网，原文会发送至 MyMemory；每次原文最多 1000 字符，并受供应商每日额度和可用性限制。免费译文质量不等同于大模型；未配置线上 OpenAI Key 进行大模型翻译验收。

## v2.0.1 — 错误提示修正版

日期：2026-10-30。对应提交：[aa0b05d](https://github.com/chunyuhan0618-svg/Test-Agent-Skill-MCP/commit/aa0b05df0c233fa18c44f9543c3801706dad681a)。

- 拆分原先合并显示的 HTTP 429 提示。
- 根据 SDK 错误 code/type，区分余额耗尽、额度不足、组织/项目消费上限、组织用量上限和请求限速。
- 为各类错误提供对应检查步骤；未知代码明确提示无法确定原因。
- 不向页面回显原始错误正文、原文或 API Key；兼容 MCP 生命周期产生的异常组。
- 验证：10 项网页相关测试通过，包括真实 SDK 错误类型的模拟响应测试；未读取用户账户余额或消耗线上 API。

## v2.0.0 — 网页版

日期：2026-10-30。对应提交：[dab1e10](https://github.com/chunyuhan0618-svg/Test-Agent-Skill-MCP/commit/dab1e10c020f77103a67226f37515a18886d2da3)。

- 增加可本地独立启动的 Python 网页应用，使用浏览器访问。
- 同一页面左、中、右分别显示中日、中英、日英对照，窄屏自动纵向排列。
- 三组默认全选，可取消任意组合；每栏独立请求、显示状态及错误。
- 增加 OpenAI 模型下拉框、自定义模型 ID 和 API Key 输入框。
- 复用原有 Agent 工具循环、三个 Skill 和 MCP 服务，增加结构化双语输出。
- API Key 仅用于当前页面及请求，不保存到文件或浏览器存储；保留初版 CLI。
- 验证：20 项测试通过；浏览器验证勾选、禁用、三栏结果、错误恢复和窄屏布局。结果展示使用明确标注的模拟译文，未进行线上大模型翻译验收。

## v1.0.0 — 命令行版

日期：2026-10-30。对应提交：[2fc5751](https://github.com/chunyuhan0618-svg/Test-Agent-Skill-MCP/commit/2fc5751ea45c93ee2fa294e4d0d645b572f06f07)。

- 实现中日英翻译命令行 Agent，支持六个翻译方向和意思解释。
- 将中日、中英、英日分别组织为三个双向 Skill，根据语言组合路由。
- 使用真实 MCP stdio 子进程提供本地术语查询。
- 实现 OpenAI Responses function calling 循环及工具结果回传。
- 提供无需 Key 的诊断演示模式；该模式验证 Skill 加载与 MCP，不生成翻译。
- 增加中文安装说明、逐文件代码教程与六向运行示例。
- 验证：11 项测试通过；三个 Skill 格式检查通过；真实 MCP 通信及 SDK 本地请求/响应适配通过，未调用线上大模型。
