# v3.4.0：公开使用说明与三语协作指南

## English

Version 3.4 removed machine-specific paths, documented portable installation and startup, and added a trilingual AGENTS.md. Run web.py from the project root; MCP starts automatically.

## 日本語

3.4 では固定パスを除き、汎用のインストール・起動手順と3言語の AGENTS.md を追加しました。ルートで web.py を実行すると MCP も自動起動します。

## 中文

3.4 清理机器固定路径、补充可移植安装和启动步骤，并新增三语 AGENTS.md；从项目根目录启动 web.py，MCP 自动启动。

---

日期：2026-11-03（日本时间）。提交目标：`current-draft`。

## 安装并启动 Agent

完整的 Windows、macOS/Linux 安装命令见 [README：首次安装并启动 Agent](../README.md#v340首次安装并启动-agent)。项目可克隆到任意目录，不依赖固定磁盘位置。

完成安装后，从项目根目录运行：

```powershell
# Windows PowerShell
.\.venv\Scripts\python.exe web.py
```

```bash
# macOS / Linux
.venv/bin/python web.py
```

浏览器打开 http://127.0.0.1:8000 。选择源语言、输入原文、勾选对照组合，然后点击“开始对照翻译”，启动一次 Agent 任务。默认开启调试，需要点击“下一步”或“一步到底”；也可取消流程选项直接翻译。MCP 服务随任务自动启动，不需要单独运行。

免费模式无需模型和 API Key，但需要联网并向 MyMemory 发送原文。OpenAI 模式需要同时填写模型与 Key。停止网页服务按 Ctrl+C；再次使用时重新执行启动命令。CLI 的入口与演示、模型翻译命令见 README.md。

## 修改范围

- 清理所有受版本控制文件中的机器固定目录；命令使用项目相对路径。
- 安装指南面向所有使用者，移除针对旧安装阶段的读者称呼。
- 根目录新增标准文件名 `AGENTS.md`，含英文、日文、中文说明与共享命令；Windows 文件名大小写不影响读取。
- 更新 README.md、CHANGELOG.md 和页面版本标记为 v3.4.0，保留历史功能事实。
- 本版不改变翻译、Skill 路由或 MCP 协议实现。

## 验证

完整回归 41 项测试通过；命令行无密钥演示成功加载 zh-ja Skill，并通过真实 MCP 命中两个术语。网页入口返回 HTTP 200，页面显示 v3.4.0。所有受版本控制文件及新增文档的固定目录、旧读者称呼扫描通过，Markdown 相对文件链接检查通过，`git diff --check` 通过。测试使用本地模型响应替身，不证明线上模型权限、额度或翻译质量；本版验证不消耗线上模型 API。
