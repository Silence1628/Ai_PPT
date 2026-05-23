# Edu_Agent

AI-driven education PPT generation pipeline. 从 Word 文档自动生成教学 PPT。

## 项目概述

```
Word (.docx)
  → word_process（chunker/processor）→ Markdown + JSON
  → base_ppt（renderer）              → Base PPT（封面/目录/任务描述等）
  → perception_ppt（assemble/fill）   → Temp PPT（知识储备+任务实施）
  → integrate                         → 最终 PPT
```

## 目录结构

```
Edu_Agent/
├── app.py                             # 主入口
├── .env / .env.example                # LLM API Key 配置
├── pyproject.toml
│
├── input/                             # Word .docx 源文件
├── output/                            # 最终 PPT 输出
│
├── prompts/                           # LLM Prompt 模板
│   ├── extraction_prompt.py           # 提取共享素材
│   ├── base_prompt.py                 # 生成 Base JSON
│   ├── fix_prompt.py                  # 单字段校正
│   ├── reconstruction_prompt.py       # LLM 语义重构段落
│   └── compress_prompt.py             # 超长字段批量压缩
│
├── LLM/                               # LLM 调用层
│   ├── client.py                      # MiniMax / DeepSeek 双厂商
│   └── schemas.py                     # Pydantic 数据模型
│
├── word_process/                      # Word 处理管线
│   ├── chunker/                       # .docx → .md 转换 + 切分 + 清洗
│   │   ├── word_to_markdown.py
│   │   ├── project_splitter.py
│   │   ├── task_splitter.py
│   │   └── markdown_cleaner.py
│   ├── processor/                     # LLM 处理 + perception 管线
│   │   ├── markdown_processor.py      # Base JSON 生成
│   │   ├── prompts.py                 # Prompt 构建函数（导入自 prompts/）
│   │   ├── perception_splitter.py     # perception 分割
│   │   ├── perception_processor.py    # H3/H4 AST 解析
│   │   ├── markdown_ast.py            # 扁平化 chunk
│   │   └── perception_semantic_chunker.py  # LLM 语义重构
│   ├── checker/                       # 字段字数校验+修正
│   │   ├── validator.py
│   │   ├── corrector.py
│   │   └── FIELD_CONSTRAINTS.py
│   ├── llm_input/perception/          # 中间数据
│   └── llm_output/
│       ├── base_json/{项目}/           # Base JSON
│       └── perception_json/{项目}/     # Perception JSON（LLM 重构后）
│
├── base_ppt/                          # Base PPT 渲染
│   ├── renderer/renderer.py           # PPTRenderer（COM）
│   ├── templates/                     # template.pptx + schema
│   └── base_output/                   # 渲染后的 base PPTX
│
├── perception_ppt/                    # Perception PPT 组装
│   ├── content_process/
│   │   ├── assemble.py                # padding → temp PPTX
│   │   ├── fill.py                    # 占位符填充
│   │   └── template/                  # 单页模板
│   │       ├── subcatelog/{2..6}/
│   │       ├── knowledge/knowledge_single/
│   │       └── task/implementation_single/
│   └── perception_output/             # 组装后的 temp PPTX
│
└── scripts/                           # 独立脚本
    ├── md_to_json.py                  # Markdown → Base JSON（含 LLM）
    ├── json_to_ppt.py                 # JSON → Base PPTX
    └── integrate.py                   # Temp PPT + Base PPT → 最终 PPT
```

## 快速开始

### 1. 配置

```bash
cp .env.example .env
# 编辑 .env：设置 LLM_PROVIDER=deepseek 和 DEEPSEEK_API_KEY=sk-xxx
```

### 2. 安装依赖

```bash
pip install python-dotenv openai pydantic pywin32 lxml
```

### 3. 放入 Word 文件

将 `.docx` 放入 `input/` 目录。

### 4. 运行

```bash
python app.py
```

首次运行会调用 LLM（Base JSON + Perception Semantic Chunk），后续运行自动跳过 LLM 步骤使用已有输出。

## Pipeline 步骤

| Step | 说明 | LLM / Prompt |
|------|------|-------------|
| 0 | Word → Markdown | - |
| 1 | 第一次数据清洗 | - |
| 2 | 第一次切分（项目 → task） | - |
| 3 | 第二次数据清洗 | - |
| 4 | 第二次切分（task → base + perception） | - |
| 5 | Base JSON 生成 | `extraction_prompt` + `base_prompt` |
| 6 | 渲染 Base PPT | - |
| 7 | Perception 流水线（分割/AST/扁平化） | - |
| 8 | Semantic Chunk（LLM 理解+重构段落） | `reconstruction_prompt` |
| 9 | Assemble + Fill（temp PPTX） | - |
| 10 | Integrate（合并为最终 PPT） | - |
| checker | 字段校验+修正 | `fix_prompt` + `compress_prompt` |

## LLM 配置

支持 MiniMax 和 DeepSeek，通过 `.env` 切换：

```bash
LLM_PROVIDER=deepseek          # 或 minimax
DEEPSEEK_API_KEY=sk-xxx        # DeepSeek
OPENAI_API_KEY=sk-xxx          # MiniMax
```

## Prompt 管理

所有 LLM Prompt 集中在 [`prompts/`](prompts/) 目录，按功能命名：

| 文件 | 用途 |
|------|------|
| `extraction_prompt.py` | 从项目介绍提取共享素材（项目名+引导案例+思考问题） |
| `base_prompt.py` | 从任务章节生成完整 Base JSON（15 个 section） |
| `fix_prompt.py` | 单字段字数校正（压缩/扩充） |
| `reconstruction_prompt.py` | 理解教材内容后重构为 ~300 字 PPT 段落 |
| `compress_prompt.py` | 同一 section 多字段批量压缩 |

## LLM 配置

支持 MiniMax 和 DeepSeek，通过 `.env` 切换：

```bash
LLM_PROVIDER=deepseek          # 或 minimax
DEEPSEEK_API_KEY=sk-xxx        # DeepSeek
OPENAI_API_KEY=sk-xxx          # MiniMax
```

## 环境要求

- Python >= 3.10
- Windows + PowerPoint（用于 PPT COM 渲染）
- DeepSeek 或 MiniMax API Key
