# Edu_Agent

AI-driven education PPT generation pipeline.

## 项目概述

Edu_Agent 是一个从 Word 文档自动生成教学 PPT 的工具链。工作流程：

```
Word 文档 → Word_Chunks → JSON → PPT_Framework → PPT 文件
```

## 目录结构

```
Edu_Agent/
├── run_pipeline.py              # 主入口（一键运行）
├── pyproject.toml               # 项目依赖配置
├── .env.example                 # 环境变量模板
├── .env                         # API Key 配置（不提交 git）
├── .gitignore                   # Git 忽略配置
│
├── LLM/                         # LLM 调用层
│   ├── __init__.py
│   ├── client.py                 # MiniMax API 客户端
│   └── schemas.py                # Pydantic 数据模型
│
├── Word_Chunks/                 # Word 文档处理模块
│   ├── __init__.py
│   ├── chunker/                  # Word 切割功能
│   │   ├── __init__.py
│   │   └── chunker.py
│   ├── processor/                # LLM 处理功能
│   │   ├── __init__.py
│   │   ├── processor.py
│   │   └── prompts.py
│   ├── checker/                  # 字数检查与修正
│   │   ├── __init__.py
│   │   ├── validator.py
│   │   ├── corrector.py
│   │   └── FIELD_CONSTRAINTS.py
│   ├── example/                  # Word 源文件目录
│   └── json_output/              # JSON 输出目录
│
└── PPT_Framework/               # PPT 生成模块
    ├── __init__.py
    ├── examples/                 # 示例数据
    ├── ppt_output/              # PPT 输出目录
    ├── renderer/                 # PPT 渲染器
    ├── schemas/                  # PPT 数据模型
    └── templates/               # PPT 模板
```

## 快速开始

### 1. 环境配置

```bash
# 克隆项目后，创建 .env 文件（从模板复制）
cp .env.example .env

# 编辑 .env，填入你的 MiniMax API Key
# MiniMax Token Plan 使用 OPENAI_API_KEY 环境变量名

# 安装依赖（推荐使用虚拟环境）
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

pip install -e .
# 或直接安装依赖
pip install python-docx python-dotenv openai pydantic
```

### 2. 准备 Word 文件

将 `.docx` 文件放入 `Word_Chunks/example/` 目录，程序会自动识别。

### 3. 运行

```bash
# 完整流程（Word → JSON → PPT）
python run_pipeline.py

# 仅渲染（已有 JSON 文件时跳过 Word 处理）
python run_pipeline.py --render-only
```

## 核心模块

### LLM

统一封装 MiniMax API（OpenAI SDK 兼容模式）。

**主要类**：`MiniMaxClient`

```python
from LLM.client import MiniMaxClient

client = MiniMaxClient()
response = client.chat([{"role": "user", "content": "Hello"}])
```

### Word_Chunks

Word 文档切割 + LLM 处理，输出 JSON 文件。

**处理流程**：
1. `WordChunker` 按标题切割 Word 文档
2. `WordChunkProcessor` 并行调用 LLM 生成 JSON
3. `Checker` 检查并修正字数超长字段（精确字段替换）

**Token Plan 注意**：
- Starter 套餐：600 次请求/5 小时
- Plus：1500 次/5 小时
- Max：4500 次/5 小时

### PPT_Framework

接收 JSON 数据，渲染生成 PPT 文件。

**主要类**：`PPTRenderer`

```python
from PPT_Framework.renderer import PPTRenderer

renderer = PPTRenderer(
    template_path="templates/template.pptx",
    schema_path="templates/template_schema.json"
)
renderer.render(data, "output.pptx")
```

## 环境要求

- Python >= 3.10
- MiniMax Token Plan API Key
- Windows（PPT_Framework 使用 win32com COM 自动化）
- WPS 或 Microsoft PowerPoint

## 依赖

| 包 | 版本 | 用途 |
|----|------|------|
| python-docx | >=1.1.0 | Word 文档读取 |
| python-dotenv | >=1.0.0 | 环境变量加载 |
| openai | >=1.0.0 | MiniMax API 调用 |
| pydantic | >=2.0.0 | 数据验证 |

## 部署检查清单

- [ ] Python >= 3.10 已安装
- [ ] 虚拟环境已创建并激活
- [ ] `.env` 文件已创建，填入有效的 `OPENAI_API_KEY`
- [ ] Word 文件已放入 `Word_Chunks/example/` 目录
- [ ] WPS 或 PowerPoint 已安装（用于 PPT 渲染）

## 常见问题

**Q: 运行报错 "找不到 Word 文件"**
A: 确保 `Word_Chunks/example/` 目录中有 `.docx` 或 `.doc` 文件，且只有一个

**Q: Checker 阶段报错 "LLM 输出无法解析"**
A: LLM 返回格式可能异常，程序会自动保留原字段继续执行

**Q: PPT 渲染失败**
A: 确保已安装 WPS 或 PowerPoint，且模板文件 `template.pptx` 存在
