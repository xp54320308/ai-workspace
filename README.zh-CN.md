# AI Workspace

面向本地资料整理与知识检索的 Python 工具箱，包含原有的 Ollama/ChromaDB RAG 管道，以及从实际项目工作中提炼的离线工具。

[English](README.md) · [离线工具说明](docs/offline-tools.md) · [来源与整理范围](docs/provenance.md) · [历史分支能力](docs/branches.md)

## 不安装模型也能运行的功能

需要 Python 3.10 或更高版本。下面四个工具只使用 Python 标准库，不需要 API Key、Ollama、LangChain 或数据库服务。

| 命令 | 实际用途 |
| --- | --- |
| catalog | 按日期/项目目录统计文件元数据，排除常见依赖目录、凭据文件、链接和 Windows 目录联接 |
| extract-docx | 按正文顺序提取 Word 段落与表格，保留段落/表格定位编号 |
| search | 对 UTF-8 Markdown/文本做中英文 BM25 检索，支持端口号和英文技术词 |
| check-links | 离线检查 Markdown 行内文件/图片链接，定位缺失文件和越出知识库的路径 |

~~~powershell
python -m workspace_tools catalog examples --depth 1
python -m workspace_tools search examples/knowledge-base "知识库迁移"
python -m workspace_tools search examples/knowledge-base "11434"
python -m workspace_tools check-links .
~~~

生成并提取一份完全合成的 Word 示例：

~~~powershell
python examples/make_sample_docx.py tmp/demo.docx
python -m workspace_tools extract-docx tmp/demo.docx --format json
~~~

输出可通过 --output 保存为 UTF-8 文件。工具拒绝覆盖已有输出；重复演示时使用新的文件名。

项目盘点只统计元数据，不会上传资料，也不代表这些文件均由你原创。目录名仍可能暴露工作内容，盘点报告默认应留在本机。

## 使用 RAG 管道

完整依赖安装、配置和模型启动见 [英文入门](docs/getting-started.md)。配置值由环境变量覆盖 config.yaml，再回退到默认值。

~~~powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item config.example.yaml config.yaml
ollama pull nomic-embed-text
ollama pull qwen2.5:14b
python run_rag.py rebuild
python run_rag.py query "这个知识库包含什么内容？"
~~~

当前主线默认模型仍是配置模板中的示例；可在 models.chat 或 RAG_CHAT_MODEL 中填写本地已安装模型。离线工具的运行不依赖这个选择。

Word 导入现在与离线提取工具共用正文提取逻辑，表格里的信息也会进入 RAG 输入。输出是正文文本，不是保持版式的 Word/PDF 渲染；扫描件、图片、页眉页脚、脚注和批注不在此解析范围内。

## 测试

~~~powershell
python -m pip install -r requirements-test.txt
python -m unittest discover -s tests -v
python -m workspace_tools check-links .
~~~

测试使用临时目录和合成数据，覆盖配置隔离、小数温度覆盖、Skill 持久化/删除、文档顺序、中文/数字检索及链接检查。符号链接测试在系统没有创建权限时会跳过。

仓库新增 GitHub Actions，配置 Windows/Linux 与 Python 3.10/3.12 的测试矩阵。是否通过以实际 Actions 运行结果为准。离线测试通过不代表真实模型、向量库和完整 RAG 管道已完成端到端验收。

## 其他分支

此前的高级 RAG 实验位于 rag-optimization，代理工作流位于 master。它们不是本次新编写的功能，也未在本次运行中整体重新验收；见 [分支说明](docs/branches.md)。从这些分支整合代码时应逐项处理依赖、API 和数据边界。

## 协作与许可

[贡献指南](CONTRIBUTING.md) · [维护说明](docs/maintainer-guide.md) · [变更记录](CHANGELOG.md) · [MIT 许可](LICENSE)

请提交通用代码、合成示例和复现说明；保留第三方来源说明。真实工作资料、个人对话、账号配置和向量库应留在本地。
