# Edu_Agent — AI 驱动的教学 PPT 自动生成系统

## 项目简介

Edu_Agent 是一个 AI 驱动的教学 PPT 自动生成管线。输入一份教学用 Word 文档（.docx），系统会自动解析文档结构、提取教学内容、经由大语言模型（LLM）进行结构化重构，最终生成一套完整的、格式精美的教学 PowerPoint 演示文稿。

**核心价值**：将教师从繁琐的 PPT 制作中解放出来。一份结构良好的教案文档，一键即可转化为可直接用于课堂的演示课件。

---

## 整体架构

```
                      ┌─────────────────────────┐
                      │   input/*.docx           │
                      │   教学 Word 文档          │
                      └──────────┬──────────────┘
                                 │
                                 ▼
              ┌──────────────────────────────────────┐
              │         word_process/chunker          │
              │   Word → Markdown → 清洗 → 切分      │
              └──────────────────┬───────────────────┘
                                 │
                  ┌──────────────┴──────────────┐
                  │                             │
                  ▼                             ▼
     ┌────────────────────┐        ┌────────────────────┐
     │   Base 线（结构页）  │        │ Perception 线（内容页）│
     │                    │        │                    │
     │  封面、目录、任务描述 │        │  知识储备、任务实施    │
     │  能力目标、重难点     │        │  详细教学内容         │
     │  任务小结、拓展      │        │                    │
     └────────┬───────────┘        └────────┬───────────┘
              │                             │
              ▼                             ▼
     ┌────────────────────┐        ┌────────────────────┐
     │  LLM 提取 + 渲染    │        │  LLM 语义重构       │
     │  Base JSON → PPTX   │        │  AST → Chunk → PPTX │
     └────────┬───────────┘        └────────┬───────────┘
              │                             │
              └──────────────┬──────────────┘
                             │
                             ▼
              ┌──────────────────────────────────────┐
              │         scripts/integrate.py          │
              │   合并 Base PPTX + Perception PPTX    │
              └──────────────────┬───────────────────┘
                                 │
                                 ▼
                      ┌─────────────────────────┐
                      │   output/*.pptx          │
                      │   最终教学演示文稿        │
                      └─────────────────────────┘
```

系统的核心设计理念是**双线并行**：

- **Base 线**：处理 PPT 的结构性页面（封面、目录、任务描述、能力目标、重难点、小结、拓展）。这些页面格式固定，使用模板 + 占位符替换的方式生成。
- **Perception 线**：处理 PPT 的内容性页面（知识储备、任务实施）。这些页面内容动态变化，需要 LLM 先理解教材原文，再将内容重构为适合 PPT 展示的段落，最后通过单页模板组装成完整内容。

两条线独立处理后，由 Integrate 模块将内容页插入结构页的定位标记处，合并为最终 PPT。

---

## 技术栈

| 层级 | 技术 | 说明 |
|------|------|------|
| 语言 | Python >= 3.10 | 主开发语言 |
| LLM 提供商 | DeepSeek (deepseek-chat) / MiniMax (MiniMax-M2.7) | 通过 `.env` 切换 |
| LLM SDK | OpenAI Python SDK | 统一接口，兼容多厂商 |
| 数据校验 | Pydantic >= 2.0 | LLM 输出结构化验证 |
| Word 解析 | lxml + zipfile | 直接解析 .docx 内部 XML，绕过 python-docx 以处理文本框 |
| PPT 操作 | pywin32 (COM/OLE) | 通过 Windows COM 自动化驱动 PowerPoint 或 WPS |
| 环境管理 | python-dotenv | API Key 等敏感配置 |
| 运行环境 | Windows + PowerPoint/WPS | COM 自动化依赖 |

---

## 项目目录结构

```
Edu_Agent/
├── app.py                                 # 主入口，11 步全流程编排
├── intro.md                               # 本文档（项目详细介绍）
├── README.md                              # 简要说明与快速开始
├── pyproject.toml                         # Python 项目配置与依赖
├── .env / .env.example                    # LLM API Key 与厂商配置
│
├── input/                                 # 输入：Word .docx 源文件
├── output/                                # 输出：最终合并后的 PPTX
│
├── LLM/                                   # LLM 抽象层
│   ├── client.py                          # 多厂商 LLM 客户端（含重试、token 统计）
│   └── schemas.py                         # Pydantic 数据模型定义
│
├── prompts/                               # 集中管理的 LLM Prompt 模板
│   ├── extraction_prompt.py               # 提取项目共享素材（项目名/引导案例/思考问题）
│   ├── base_prompt.py                     # 生成任务 Base JSON（15 个 section 完整结构）
│   ├── fix_prompt.py                      # 单字段字数校正（超长压缩 / 不足扩充）
│   ├── compress_prompt.py                 # 同 section 多字段批量压缩
│   └── reconstruction_prompt.py           # LLM 理解教材内容，重构为 ~300 字 PPT 段落
│
├── word_process/                          # Word 处理管线（核心模块，代码量最大）
│   ├── chunker/                           # 文档分块：Word → Markdown → 清洗 → 切分
│   │   ├── word_to_markdown.py            # .docx XML 直接解析 → .md
│   │   ├── markdown_cleaner.py            # Markdown 数据清洗（7 条规则）
│   │   ├── project_splitter.py            # 项目 .md → before_task.md + taskN.md
│   │   └── task_splitter.py               # taskN.md → base/ + perception/
│   ├── processor/                         # LLM 处理与 Perception 管线
│   │   ├── markdown_processor.py          # LLM 提取 Base JSON（Stage 1）
│   │   ├── prompts.py                     # Prompt 构建胶水层（导入 prompts/ 模板）
│   │   ├── perception_splitter.py         # perception.md → knowledge.md + implementation.md
│   │   ├── perception_processor.py        # Markdown → H3/H4 AST 解析
│   │   ├── markdown_ast.py                # 嵌套 AST → 扁平化独立 chunk
│   │   └── perception_semantic_chunker.py # LLM 语义理解 + 重构段落（递归拆分）
│   ├── checker/                           # 质量保证：字段字数校验 + 修正
│   │   ├── FIELD_CONSTRAINTS.py           # 23 个字段的字数上下限定义
│   │   ├── validator.py                   # 检查 JSON 字段是否超限
│   │   └── corrector.py                   # 调用 LLM 修正超限字段（支持多轮重试）
│   ├── base_reference/                    # 参考样本 JSON（期望输出的结构示例）
│   ├── original/                          # 处理后的 Markdown 中间产物
│   ├── llm_input/perception/              # Perception 管线的输入数据
│   │   ├── markdown_cut/                  #   分割后的 knowledge.md / implementation.md
│   │   ├── original_markdown/             #   H3/H4 AST JSON
│   │   └── preprocessed/                  #   扁平化后的 chunk JSON
│   └── llm_output/                        # LLM 输出产物
│       ├── base_json/{项目}/               #   Base JSON（每任务一个文件）
│       └── perception_json/{项目}/         #   Perception JSON（LLM 重构后）
│
├── base_ppt/                              # Base PPT 渲染模块
│   ├── renderer/renderer.py               # PPTRenderer：模板 + JSON → PPTX（COM）
│   ├── templates/
│   │   ├── template.pptx                  # 16 页预设计母版（含占位符形状）
│   │   └── template_schema.json           # 页-形状-占位符映射关系
│   └── base_output/                       # 渲染后的 Base PPTX
│
├── perception_ppt/                        # Perception PPT 组装模块
│   ├── content_process/
│   │   ├── assemble.py                    # 单页模板 → temp PPTX（COM InsertFromFile）
│   │   ├── fill.py                        # 占位符文本替换（{{text:xxx}}）
│   │   └── template/                      # 单页 PPTX 模板库
│   │       ├── subcatelog/{1..6}/         #   子目录页模板（支持 1-6 个标题）
│   │       ├── knowledge/                 #   知识储备模板（10 种版式循环）
│   │       └── task/                      #   任务实施模板（2 种版式交替）
│   └── perception_output/                 # 组装并填充后的 temp PPTX
│
└── scripts/                               # 独立执行脚本
    ├── md_to_json.py                      # Markdown → Base JSON（含 LLM 调用 + 校验修正）
    ├── json_to_ppt.py                     # Base JSON → Base PPTX 渲染
    └── integrate.py                       # Base PPTX + Temp PPTX → 最终 PPTX
```

---

## 处理管线详解（11 步全流程）

整个管线由 `app.py` 统一编排，按顺序执行以下步骤：

### Step 0 — Word → Markdown

**模块**：`word_process/chunker/word_to_markdown.py`

使用 `zipfile` + `lxml` 直接解析 .docx 内部 XML 结构（`document.xml` + `styles.xml`），将 Word 文档转换为 Markdown 格式。

**为什么不用 python-docx**：标准库无法处理 Word 文本框中的内容，而教学文档中大量关键内容放置在文本框内。直接解析 XML 可以完整提取所有文本。

**识别逻辑**：
- 通过段落样式识别 Heading 1~5 层级
- 通过 `【情境导入】`、`【任务描述】`、`【知识储备】`、`【任务实施】` 等标记识别文档结构
- 自动识别代码块（样式名含"代码"）
- 按 Heading 1（项目）、Heading 2（任务）切分输出

**输出**：`word_process/original/{项目名}/{项目名}.md`

---

### Step 1 — 第一次数据清洗

**模块**：`word_process/chunker/markdown_cleaner.py`

对原始 Markdown 执行 7 条清洗规则：删除图表编号行（如 `图1-1-1`）、压缩多余空行、规整标题标点、标准化列表标记、删除行尾空格、统一文件结尾。

---

### Step 2 — 第一次切分（项目 → 任务）

**模块**：`word_process/chunker/project_splitter.py`

将项目 .md 按 `# before task` 和 `# 任务一/二/三` 标题切分为独立文件。

**输出**：`before_task.md`、`task1.md`、`task2.md`、`task3.md`...

---

### Step 3 — 第二次数据清洗

再次执行 `MarkdownCleaner`，清理切分后可能引入的格式问题。

---

### Step 4 — 第二次切分（任务 → Base + Perception）

**模块**：`word_process/chunker/task_splitter.py`

将每个 `taskN.md` 按 7 个章节标记拆分为 Base 和 Perception 两部分：

| Base 部分 | Perception 部分 |
|-----------|----------------|
| 【任务描述】 | 【知识储备】 |
| 【任务能力目标】 | 【任务实施】 |
| 【任务重难点】 | |
| 【任务小结】 | |
| 【任务拓展】 | |

**输出**：`base/taskN_base.md`、`perception/taskN_perception.md`

---

### Step 5 — Base JSON 生成（LLM 阶段）

**模块**：`scripts/md_to_json.py` + `word_process/processor/markdown_processor.py`

这一步在 `app.py` 中**默认跳过 LLM 调用**，检查已有输出。实际的 LLM 调用通过 `scripts/md_to_json.py` 单独执行。

**两阶段 LLM 处理**：

1. **Chunk1 提取**（Prompt: `extraction_prompt`）：从 `before_task.md` 提取项目级共享素材——项目名称（≤20字）、引导案例（200-220字）、3 个引导问题（各 ≤30字）。
2. **Task JSON 生成**（Prompt: `base_prompt`）：为每个任务生成包含 15 个 Section 的完整 JSON 结构：
   - `cover` — 封面
   - `introduction` — 引导案例 + 思考问题
   - `thinking` — 思考路径
   - `start` — 任务开始
   - `catalog_one` ~ `catalog_six` — 6 个目录项
   - `description` — 任务描述
   - `target` — 能力目标
   - `summary` — 任务小结
   - `key_difficulties_summary` — 重难点总结
   - `expansion` — 任务拓展

每个字段有明确的 mode（copy/summary/raw_copy）和字数上下限。

**校验与修正**：生成后由 `checker/` 子模块对所有字段做字数校验。超限字段调用 `compress_prompt` 或 `fix_prompt` 让 LLM 压缩/扩充，支持最多 2 轮修正。

**输出**：`word_process/llm_output/base_json/{项目名}/task{N}_base.json`

---

### Step 6 — 渲染 Base PPT

**模块**：`base_ppt/renderer/renderer.py`

加载 `template.pptx`（16 页预设计母版），根据 `template_schema.json` 中的页-形状-占位符映射关系，将 Base JSON 中的数据填充到对应形状中。

**关键机制**：
- 占位符格式：`{{text:field_name}}`，渲染时替换为实际文本
- `combine_fields`：支持多字段合并（如逐条拼接能力目标）
- `optional` 形状：数据为空时自动删除形状
- 字体、字号、对齐方式均由 schema 控制

**COM 操作流程**：`Dispatch PowerPoint → 打开模板 → 逐页逐形状填充 → 另存为 → 关闭`

**输出**：`base_ppt/base_output/1.{task_num}_{task_name}.pptx`

---

### Step 7 — Perception 流水线

**模块**：`word_process/processor/perception_splitter.py` + `perception_processor.py` + `markdown_ast.py`

三阶段处理：

**Stage 0 — 分割**：将 `taskN_perception.md` 在 `【知识储备】`/`【任务实施】` 边界拆分为 `knowledge.md` + `implementation.md`。

**Stage 1 — AST 解析**：将 Markdown 解析为 H3/H4 层级 AST（抽象语法树）。H3（`####`）为知识点主题，H4（`#####`）为叶子内容节点。识别代码块、图表引用，处理中文序号标题（如"一、"自动提升为 H3）。

**Stage 2 — 扁平化**：将嵌套 H3/H4 AST 展开为扁平 chunk 列表。每个 H4 子节点成为独立 chunk；H3 节点若无 H4 子节点则自身成为 chunk。

---

### Step 8 — Semantic Chunk（LLM 语义重构）

**模块**：`word_process/processor/perception_semantic_chunker.py`

同样在 `app.py` 中默认跳过 LLM，使用已有输出。

**核心逻辑**：将同一 H3 主题下的所有扁平化 chunk 组合，交由 LLM（Prompt: `reconstruction_prompt`）理解内容后，重新组织为约 300 字一组的 PPT 段落。超长段落会递归拆分（`reconstruction_prompt` 的 recursive 变体）。

**容错设计**：
- LLM 返回的标题可能与原文不完全一致 → 精确匹配 → 模糊包含 → 前 4 字匹配
- JSON 解析失败 → 标准解析 → 花括号提取 → 正则提取
- 无 LLM 客户端时 → 回退到纯按句子切分

**输出**：`word_process/llm_output/perception_json/{项目名}/{section}/task{N}_{section}.json`

---

### Step 9 — Assemble + Fill

**模块**：`perception_ppt/content_process/assemble.py` + `fill.py`

**Assemble（组装）**：读取 Perception JSON，将内容按 H3 主题分组，映射到单页模板：

- 知识储备：10 种版式（`page_1.pptx` ~ `page_10.pptx`）循环使用
- 任务实施：2 种版式（`page_1.pptx` ~ `page_2.pptx`）交替使用

每个 H3 段生成：`[子目录页] → [内容页1] → [内容页2] → ...` 的结构。通过 COM `InsertFromFile()` 将单页模板依次插入。

**Fill（填充）**：遍历组装好的 temp PPTX，将占位符替换为实际内容：
- `{{text:cate_num}}` → "03"（知识）或 "04"（任务）
- `{{text:replace}}` → "知识储备" 或 "任务实施"
- `{{text:point_N}}` → H3 标题
- `{{text:content}}` → 段落正文

---

### Step 11 — Integrate（最终整合）

**模块**：`scripts/integrate.py`

将 Perception temp PPTX 插入 Base PPTX 的对应位置，生成最终课件。

**流程**：打开 Base PPTX → 找到 `{{定位页}}` 标记幻灯片（知识储备和任务实施各一个占位页）→ 在标记位置后 `InsertFromFile` 插入 temp PPTX 的所有幻灯片 → 删除标记页 → 保存到 `output/`

**命名规则**：`output/1.{task_num}_{task_name}.pptx`

---

## AI 与 LLM 技术详解

Edu_Agent 的核心智能来源于大语言模型（LLM）。项目将 LLM 作为"内容理解引擎"嵌入处理管线，在三个关键环节调用 AI 能力，实现从非结构化文档到结构化 PPT 数据的智能转换。

### LLM 在项目中的角色

LLM 在本项目中不是简单的"文本生成器"，而是充当了三个不同的专业角色：

| 角色 | 应用场景 | 输入 | 输出 | 核心能力要求 |
|------|---------|------|------|------------|
| 信息提取器 | Base JSON 生成 | 原始教学 Markdown | 15 Section 结构化 JSON | 信息定位、摘要、改写 |
| 内容编辑 | Perception 语义重构 | H3/H4 知识点原文 | ~300 字 PPT 段落 | 语义理解、逻辑重组、流畅叙述 |
| 质量控制 | 字段字数修正 | 超限字段 + 约束条件 | 修正后文本 | 压缩/扩充、保持语义 |

---

### LLM 客户端层设计（LLM/client.py）

项目在 `LLM/client.py` 中构建了一个统一的 LLM 调用抽象层，屏蔽不同厂商 API 的差异：

```
                    ┌─────────────────────┐
                    │     LLMClient       │
                    │  (统一接口)          │
                    │                     │
                    │  chat()             │
                    │  chat_with_stats()  │
                    │  chat_stream()      │
                    └─────────┬───────────┘
                              │
              ┌───────────────┴───────────────┐
              │                               │
              ▼                               ▼
    ┌──────────────────┐          ┌──────────────────┐
    │    DeepSeek       │          │    MiniMax        │
    │  deepseek-chat    │          │  MiniMax-M2.7     │
    │                   │          │                   │
    │  base_url:        │          │  base_url:        │
    │  api.deepseek.com │          │  api.minimaxi.com │
    └──────────────────┘          └──────────────────┘
```

**设计要点**：

1. **OpenAI 兼容协议**：使用 `openai` Python SDK 作为底层 HTTP 客户端，两个厂商均提供 OpenAI 兼容的 API 端点（`/v1/chat/completions`），切换厂商时仅需更改 `base_url` 和 `api_key`，业务代码零修改。

2. **环境变量驱动切换**：
   ```bash
   LLM_PROVIDER=deepseek    # 或 minimax
   ```
   系统通过 `LLM_PROVIDER` 环境变量自动选择厂商配置，支持的厂商定义在 `PROVIDERS` 字典中，扩展新厂商只需添加一行配置。

3. **指数退避重试机制**：
   ```
   第 1 次失败 → 等待 1s (2^0)
   第 2 次失败 → 等待 2s (2^1)
   第 3 次失败 → 等待 4s (2^2)
   3 次全失败 → 抛出 RuntimeError
   ```
   自动处理 `RateLimitError`（限流）和 `APIError`（临时错误），最多重试 3 次。

4. **线程安全**：使用 `threading.Lock()` 保护 API 调用，确保多线程并发场景下的安全访问。

5. **Token 统计**：每次调用后记录 `prompt_tokens`、`completion_tokens`、`total_tokens`，通过 `last_usage` 属性暴露，用于成本跟踪和用量审计。

6. **MiniMax 专用支持**：MiniMax 模型支持 `reasoning_split` 参数，启用后响应中会包含 `reasoning_content`（思维链），可用于调试和解释模型推理过程。

---

### AI 应用场景一：结构化信息提取（Base JSON 生成）

这是 LLM 在本项目中最核心的应用。输入是一份 Markdown 格式的教学文档片段，输出是一个包含 15 个 Section、50+ 个字段的严格结构化 JSON。

**处理流程**：

```
before_task.md  ──▶ [Chunk1 LLM] ──▶ project_name
                    extraction_prompt   introduction_case
                                        guiding_problem1/2/3
                                              │
                   ┌──────────────────────────┘
                   ▼
taskN.md       ──▶ [Chunk2 LLM] ──▶ taskN_base.json
                    base_prompt         (15 sections, 50+ fields)
```

**两阶段设计**：

**阶段 1 — Chunk1 提取共享素材**（`prompts/extraction_prompt.py`）：

首先处理 "情境导入" 部分，提取项目级别的共享数据，后续所有任务的 JSON 都引用这些数据：

```
输入：Word 文档中【情境导入】部分的 Markdown 文本
  ↓ LLM 处理
输出：
  {
    "project_name": "智能体应用初探专项实战",
    "introduction_case": "某企业面临智能化转型，需要一个能自动分析
                          客户需求的智能客服系统...(200-220字完整案例)",
    "guiding_problem1": "如何设计一个能理解用户意图的智能体？",
    "guiding_problem2": "智能体与传统程序的根本区别是什么？",
    "guiding_problem3": "多智能体系统如何协同工作？"
  }
```

**阶段 2 — Task JSON 生成**（`prompts/base_prompt.py`）：

将 Chunk1 的共享数据注入 Task Prompt，连同任务章节的 Markdown 内容一起发送给 LLM，生成完整的任务 JSON。每个字段都被分配了特定的处理模式：

| 模式 | 含义 | 典型场景 | 示例字段 |
|------|------|---------|---------|
| `copy` | 直接复制原文，不做改写 | 不需要改动的标题/编号 | `task_num`、`task_name` |
| `summary` | 提炼/压缩原文核心意思 | 需要对多段内容做总结 | `guiding_problem`、`key_summary` |
| `raw_copy` | 选择性复制原文段落后截断 | 原文质量好只需长度控制 | `task_description`、`task_summary` |

**Prompt 中的字段级指令**：

Project 的 Prompt 采用了"逐字段指令"的设计模式。每个字段在 Prompt 中都带有明确的模式标注和字数限制，例如：

```
"introduction_case": "copy模式，直接复制chunk1提取的项目名称，15-20字"
"task_description": "raw_copy模式，从【任务分析】提取任务描述部分，
                     1-110字"
"key_summary1": "summary模式，跨三块内容总结关键点，1-20字
                （必须以分号结尾）"
```

这种设计的好处是：LLM 在输出每个字段时都有明确的规则指引，减少了开放式生成带来的格式不一致问题。

**Post-Processing（后处理）**：

LLM 返回 JSON 后，代码层面还会执行额外的规则化处理：
- `task_summary` 字段不用 LLM 输出，直接从原文 `【任务小结】` 段落提取后按句子边界截断（`_extract_task_summary` + `_truncate_at_sentence`），避免 LLM 对小结内容的意外改写
- `task_requirements` 不足 5 条时，从 `task_targets` 中填充（`_fill_task_requirements_from_targets`）
- 所有 `catalog_*` 的 `task_num` 和 `task_name` 统一标准化
- 输出 JSON 按预设的字段顺序（`TASK_JSON_FIELD_ORDER`）重排列

---

### AI 应用场景二：语义理解与内容重构（Perception Semantic Chunk）

这是 LLM 在本项目中最具挑战性的应用。教材原文是长篇幅的叙述性文本，不适合直接放入 PPT 页面。LLM 需要先"读懂"教材内容的逻辑结构，然后将每个知识点的内容重构为适合 PPT 展示的独立段落（约 300 字/段）。

**处理流程**：

```
preprocessed JSON
(H3主题下多个H4 chunk，每个含原始content)
  │
  │  按 H3 父标题分组
  ▼
┌─────────────────────────────────────────────┐
│  H3: "智能体的定义与特征"                      │
│  ├── H4-1: "智能体的定义" (原文 800 字)         │
│  ├── H4-2: "智能体的核心特征" (原文 1200 字)     │
│  └── H4-3: "智能体与传统软件的区别" (原文 600 字) │
└─────────────────────────────────────────────┘
  │
  │  整组发送给 LLM
  ▼
┌─────────────────────────────────────────────┐
│  LLM 语义理解 + 重构                           │
│  (reconstruction_prompt)                     │
│                                              │
│  1. 理解每个 H4 讲的是什么知识点                 │
│  2. 分析 H4 之间的逻辑关系（递进/并列/对比）       │
│  3. 保留所有关键概念、定义、例子                  │
│  4. 用连贯叙述重组为 ~300 字的 PPT 段落           │
│  5. 删除"如图X-X-X所示"等图表指向语句            │
└─────────────────────────────────────────────┘
  │
  ▼
{
  "h4_sections": [
    {
      "title": "智能体的定义",
      "paragraphs": [
        "智能体（Agent）是指能够通过传感器感知环境...（~300字）",
        "从结构上看，智能体由感知模块、决策模块...（~300字）"
      ]
    },
    {
      "title": "智能体的核心特征",
      "paragraphs": [
        "智能体具有四个核心特征：自主性...（~300字）",
        "反应性是指智能体能对环境变化做出...（~300字）",
        "社会性是多个智能体协作的基础...（~300字）"
      ]
    },
    ...
  ]
}
```

**关键设计决策**：

1. **按 H3 分组而非逐 H4 处理**：将同一 H3 主题下的所有 H4 一起发送给 LLM，让 LLM 理解完整的上下文，把握知识点之间的逻辑关系。如果每个 H4 独立处理，LLM 会丢失整体视角，导致段落之间缺乏连贯性。

2. **低温度参数（temperature=0.3）**：与 Base JSON 生成使用 0.7 不同，这里使用更低的值。因为内容重构的目标是"忠实复述"教材的知识点，而非创造性改写，低温度可以降低 LLM "发挥"的空间，减少信息遗漏风险。

3. **递归拆分**：LLM 首轮输出后，单个段落如果仍超过 900 字（`max_chars × 3`），会触发递归 LLM 调用——以该段落为输入，调用 `reconstruction_prompt` 的递归变体，要求 LLM 在语义完整处再次拆分为多个 300 字段落。

4. **无 LLM 时的降级策略**：当环境没有配置 API Key 时，系统回退到纯规则的分段策略——先按空行切段，累积拼接至 300 字上限后输出，确保管线不会因缺少 LLM 而中断。

**标题回映射机制**：

LLM 返回的 H4 标题可能与原文不完全一致（LLM 会自然地调整措辞）。系统设计了三级匹配策略：

```
精确匹配 → 原文标题与 LLM 返回完全相同
    ↓ 失败
包含匹配 → 一个标题包含在另一个中
    ↓ 失败
前4字匹配 → 取两者前 4 个字符比较
    ↓ 失败
回退 → 该 H4 用句子切分的 fallback 结果
```

---

### AI 应用场景三：字段字数校正（Checker）

Base JSON 生成后，需要对所有字段进行字数合规检查。每个字段都定义在 `FIELD_CONSTRAINTS.py` 中，有严格的 min/max 字符限制。这是因为 PPT 页面的文本框有固定的可视面积，超长文本会导致溢出或被迫缩小字号。

**处理流程**：

```
taskN_base.json
  │
  ▼
┌─────────────────────────────┐
│   validate_lengths()        │
│   逐字段检查字数              │
│   vs FIELD_CONSTRAINTS      │
└──────────┬──────────────────┘
           │
     ┌─────┴─────┐
     │           │
  全部合规     有超限字段
     │           │
     ▼           ▼
  直接返回  ┌─────────────────────────────────┐
           │  Corrector.correct()              │
           │                                   │
           │  1. 按 section 分组               │
           │  2. 同 section 多字段 → 一个 Prompt │
           │  3. 调用 LLM 批量修正              │
           │  4. 应用修正 → 重新 validate       │
           │  5. 仍有问题 → 再修正（最多2轮）     │
           └─────────────────────────────────┘
```

**Prompt 策略差异**：

两个 Prompt 文件对应两种修正粒度：

| Prompt | 适用场景 | 策略 |
|--------|---------|------|
| `compress_prompt.py` | 同一 section 内多个字段超长 | 批量压缩：给出所有字段的约束表和当前值，LLM 一次性返回全部修正结果 |
| `fix_prompt.py` | 单个字段需要修正 | 精准修正：提供压缩技巧（删除修饰词、合并同义表达、简称替换）和扩充技巧（添加连接词、补充限定语）|

**压缩技巧 Prompt 示例**（`fix_prompt.py` 中的核心指令）：

```
压缩技巧（字数超限时使用）：
1. 删除冗余修饰词（的、了、在）
2. 合并重复或相近的表达
3. 使用更简短的同义词替换
4. 删除举例说明，保留核心定义
5. 删除重复说明的内容
```

---

### JSON 解析与容错机制

LLM 以自然语言方式输出，即使 Prompt 明确要求"只输出 JSON"，实际响应仍可能出现格式问题。项目在三个级别的模块中实现了分层容错：

**Base JSON 生成层**（`markdown_processor.py`）：

```
LLM 响应
  │
  ▼
_extract_json(): 移除 ```json``` wrapper → 找第一个 { 和最后一个 }
  │
  ├── 标准解析成功 → 返回 JSON
  │
  ├── 失败 → 渐进扩展（从最后一个 } 向后扩展 1-20 字符尝试）
  │     │
  │     ├── 成功 → 返回 JSON (LLM 输出被截断但后面是空白)
  │     └── 失败 → 触发 LLM 重试（最多 2 次）
  │
  └── 2 次重试均失败:
        ├── _try_fix_json(): 找第一个深度归零的 }（截断修复）
        ├── 补全缺失的末尾 }
        └── 仍失败 → _get_minimal_task_structure()（返回空结构保证管线不崩溃）
```

**Semantic Chunk 层**（`perception_semantic_chunker.py`）：

```
LLM 响应
  │
  ▼
_parse_json():
  ├── 去除 </think> XML 标签（MiniMax reasoning 输出特征）
  ├── 去除 ```json ``` wrapper
  ├── 标准 json.loads()
  ├── 花括号提取（text[first_brace:last_brace+1]）
  └── 正则提取（正则匹配 "paragraphs" 数组内容）
```

**Checker 层**（`corrector.py`）：

```
LLM 响应
  │
  ▼
_extract_corrections():
  ├── 去除 </think> 标签
  ├── 去除 ```json ``` wrapper
  ├── 标准 json.loads()
  └── 花括号提取
```

---

### Prompt 工程体系

项目将 Prompt 视为"代码"，纳入版本管理，与业务逻辑分离。5 个 Prompt 文件集中在 `prompts/` 目录。

#### Prompt 设计原则

1. **角色设定前置**：每个 Prompt 开头都有角色声明（如"你是一个教育PPT内容提取助手"），帮助 LLM 建立正确的行为模式。

2. **结构化输出约束**：所有 Prompt 都要求 JSON 格式输出，并在 Prompt 中包含期望的 JSON Schema 定义。字段级别的约束（模式、字数限制）与字段定义绑定，让 LLM 在输出时就能自我检查。

3. **内容来源标注**：Prompt 中明确标注输入内容的来源位置（如 `【任务描述】`、`【任务能力目标】`），帮助 LLM 定位原文。

4. **共享数据注入**：Chunk1 提取的共享素材（项目名、引导案例、思考问题）通过变量注入方式传递到 Task Prompt 中，避免 LLM 重复提取产生不一致。

5. **负面指令**：每个 Prompt 末尾都有"只输出JSON，不要其他文字"的硬约束，减少 LLM 附带的解释性文字。

#### Prompt 胶水层

`word_process/processor/prompts.py` 是连接 Prompt 模板和业务代码的胶水层，提供系列构建函数：

```
prompts/*.py (模板)         prompts.py (构建函数)          调用方
────────────────────────────────────────────────────────────────
extraction_prompt.py  →  build_chunk1_prompt(content)  →  markdown_processor
base_prompt.py        →  build_task_prompt(title,       →  markdown_processor
                           content, chunk1_data)
fix_prompt.py         →  build_correct_field_prompt(    →  corrector
                           section, field, ...)
compress_prompt.py    →  (直接 .format() 调用)           →  corrector
reconstruction_prompt →  build_semantic_chunk_prompt(   →  perception_semantic
                           parent_title, h4_contents)       _chunker
```

---

### Token 管理与成本控制

项目在多个层面考虑了 LLM 调用的成本：

1. **LLM 调用与 PPT 渲染分离**：`app.py` 默认跳过 LLM 步骤（Step 5、Step 8），仅检查和复用已有输出。LLM 调用通过 `scripts/md_to_json.py` 和执行 `PerceptionSemanticChunker` 单独进行。这意味着：
   - 调整 PPT 版式、字体、配色时无需重新调用 LLM（零成本迭代）
   - LLM 输出可人工审核后再进入渲染管线
   - 同一份 LLM 输出可复用于多种 PPT 模板

2. **Token 用量追踪**：`LLMClient.chat_with_stats()` 返回每次调用的详细 token 统计，`MarkdownChunkProcessor` 在内存中累积总量，打印日志时输出每次调用的 token 消耗。

3. **串行而非并行 LLM 调用**：Task JSON 之间不存在依赖关系，理论上可以并行处理。但项目采用串行策略，避免并发请求触发 API 限流，也便于逐任务追踪输出质量。

4. **降级回退策略**：
   - 无 API Key → `PerceptionSemanticChunker` 使用纯句子切分
   - LLM 返回损坏 JSON → 多次重试 + 多种修复策略
   - 最终回退到最小有效结构（保证管线不中断）

---

## 设计决策与关键模式

### 1. 为什么使用 COM 而不是 python-pptx？

python-pptx 只能创建新元素，无法精确复现预设计模板的视觉效果（渐变、阴影、复杂排版）。通过 COM 打开已在 PowerPoint 中精调好的 `.pptx` 模板文件，仅替换其中的占位符文本，可以保留设计师调整的所有视觉效果。代价是必须运行在 Windows 环境且需要安装 PowerPoint 或 WPS。

### 2. 双线并行架构

将 PPT 页面分为"结构页"（格式固定、文本量小）和"内容页"（格式多样、文本量大）两条线独立处理：

- **Base 线**的输出质量依赖 LLM 的信息提取和摘要能力
- **Perception 线**的输出质量依赖 LLM 的语义理解和段落重构能力

两条线使用不同的 Prompt、不同的 LLM 参数、不同的模板体系，可以独立调试和优化。

### 3. LLM 两步策略

在 `app.py` 中，LLM 调用步骤（Step 5 和 Step 8）默认**跳过**，直接使用已有输出。实际的 LLM 调用通过 `scripts/md_to_json.py` 单独执行。这样设计的好处：

- 调试 PPT 渲染/组装时不需要重复调用 LLM（节省时间和费用）
- LLM 输出可以人工检查后再进入后续步骤
- 可以多次调整渲染参数而不重新生成 JSON

### 4. 模板驱动的 PPT 生成

Base PPT 使用 `template.pptx`（母版）+ `template_schema.json`（映射关系）的方式。新增或修改页面布局只需调整 schema JSON，无需改代码。Perception PPT 使用单页模板库，通过循环/交替选择模板来产生视觉变化，避免重复单调。

### 5. 字段字数校验体系

Base JSON 的 23 个字段都有严格的字数上下限（定义在 `FIELD_CONSTRAINTS.py`）。这是因为 PPT 页面的文本框有固定的可视面积，超长文本会导致溢出或被迫缩小字号。校验分为三个层次：

1. **Pydantic Schema**：类型级别的约束
2. **Validator**：运行时的字数检查
3. **Corrector**：LLM 驱动的自动修正（分组批量压缩，支持多轮重试）

### 6. 多厂商 LLM 支持

`LLM/client.py` 将 DeepSeek 和 MiniMax 封装为统一的 OpenAI 兼容接口。切换厂商只需修改 `.env` 中的 `LLM_PROVIDER` 变量。客户端内置：
- 指数退避自动重试（处理限流和临时错误）
- MiniMax `reasoning_split` 专用响应解析
- 线程安全的 token 用量统计

---

## 数据流全景

```
input/《智能体开发与应用》实训指导书.docx
    │
    │  [Step 0] XML 直接解析
    ▼
word_process/original/项目一 智能体开发与应用/
  ├── 项目一 智能体开发与应用.md
  │
    │  [Step 1-4] 清洗 + 切分
    ▼
  ├── before_task.md              # 项目导入部分
  ├── task1.md                    # 任务一：初识智能体
  ├── task2.md                    # 任务二：...
  ├── base/
  │   ├── task1_base.md           # 任务描述、目标、重难点、小结、拓展
  │   ├── task2_base.md
  ├── perception/
  │   ├── task1_perception.md     # 知识储备 + 任务实施
  │   ├── task2_perception.md
  │
    │  ┌─────────────────────────────────────────┐
    │  │           [Base 线]                      │
    │  │                                          │
    │  │  [md_to_json.py] LLM 提取                │
    │  │  base/task1_base.md ──▶ llm_output/      │
    │  │                        base_json/        │
    │  │                        项目一/            │
    │  │                          task1_base.json  │
    │  │                          task2_base.json  │
    │  │                                          │
    │  │  [checker] 字数校验 + LLM 修正            │
    │  │                                          │
    │  │  [PPTRenderer]                           │
    │  │  base_json + template.pptx               │
    │  │       ──▶ base_ppt/base_output/          │
    │  │            1.1_初识智能体.pptx             │
    │  │                                          │
    │  └─────────────────────────────────────────┘
    │
    │  ┌─────────────────────────────────────────┐
    │  │           [Perception 线]                │
    │  │                                          │
    │  │  [PerceptionSplitter]                    │
    │  │  perception/task1_perception.md          │
    │  │       ──▶ markdown_cut/                  │
    │  │            knowledge.md                   │
    │  │            implementation.md              │
    │  │                                          │
    │  │  [PerceptionProcessor] H3/H4 AST 解析    │
    │  │       ──▶ original_markdown/             │
    │  │            task1_knowledge.json           │
    │  │                                          │
    │  │  [MarkdownASTProcessor] 扁平化            │
    │  │       ──▶ preprocessed/                  │
    │  │            task1_knowledge.json           │
    │  │                                          │
    │  │  [PerceptionSemanticChunker] LLM 重构     │
    │  │       ──▶ perception_json/               │
    │  │            项目一/knowledge/              │
    │  │              task1_knowledge.json         │
    │  │            项目一/task/                   │
    │  │              task1_implementation.json    │
    │  │                                          │
    │  │  [AssembleProcessor] 模板组装             │
    │  │  [FillProcessor] 占位符填充              │
    │  │       ──▶ perception_output/             │
    │  │            knowledge/task1_knowledge.pptx │
    │  │            task/task1_implementation.pptx │
    │  │                                          │
    │  └─────────────────────────────────────────┘
    │
    │  [Step 11] IntegrateProcessor 合并
    ▼
output/1.1_初识智能体.pptx     ← 最终课件
```

---

## 快速开始

### 环境要求

- Windows 操作系统
- 已安装 Microsoft PowerPoint 或 WPS Office
- Python >= 3.10
- DeepSeek 或 MiniMax API Key

### 安装与配置

```bash
# 1. 安装依赖
pip install python-dotenv openai pydantic pywin32 lxml

# 2. 配置 LLM
cp .env.example .env
# 编辑 .env，设置：
#   LLM_PROVIDER=deepseek
#   DEEPSEEK_API_KEY=sk-你的密钥

# 3. 放入 Word 文档到 input/ 目录
```

### 运行

```bash
# 全流程执行（首次需先运行 LLM 步骤）
python app.py

# 单独执行 LLM Base JSON 生成（首次或需要重新生成时）
python scripts/md_to_json.py

# 单独执行 Base PPT 渲染
python scripts/json_to_ppt.py
```

### 执行顺序说明

首次运行完整流程：
1. `python scripts/md_to_json.py` — LLM 生成 Base JSON + 校验修正
2. （手动运行 `perception_semantic_chunker.py` 生成 Perception JSON）
3. `python app.py` — 执行全流程（自动跳过 Step 5 和 Step 8 的 LLM 调用）

后续调整 PPT 渲染效果时只需重复步骤 3，无需重新调用 LLM。

---

## Prompt 快速参考

> 详细的 Prompt 工程体系、指令设计、JSON 容错机制等内容请见上一节「AI 与 LLM 技术详解」。

所有 Prompt 文件集中在 `prompts/` 目录，与业务代码分离，通过 `word_process/processor/prompts.py` 胶水层注入变量：

| Prompt 文件 | AI 应用场景 | 核心指令 |
|------------|-----------|---------|
| `extraction_prompt.py` | 共享素材提取 | 提取项目名称（copy模式，15-20字）、引导案例（summary模式，200-220字）、3个引导问题（summary模式，1-30字） |
| `base_prompt.py` | 任务结构化提取 | 按 copy/summary/raw_copy 三种模式，从任务章节生成 15 Section + 50+ 字段的完整 JSON，每个字段有独立字数约束 |
| `reconstruction_prompt.py` | 教学内容语义重构 | 理解 H3/H4 知识点后重组为 ~300 字 PPT 段落，保留所有关键概念，删除图表指向语句，递归拆分超长段落 |
| `fix_prompt.py` | 单字段精准修正 | 提供 5 条压缩技巧 + 3 条扩充技巧，LLM 在保持语义前提下调整文本至目标字数 |
| `compress_prompt.py` | 同 Section 批量压缩 | 输入约束表 + 字段详情，LLM 一次性返回所有超限字段的修正值

---

## 依赖关系图

```
app.py
 ├── word_process.chunker.word_to_markdown        (Step 0)
 ├── word_process.chunker.markdown_cleaner         (Step 1, 3)
 ├── word_process.chunker.project_splitter         (Step 2)
 ├── word_process.chunker.task_splitter            (Step 4)
 ├── word_process.processor.markdown_processor      (Step 5, via scripts/md_to_json.py)
 │   ├── LLM.client
 │   ├── LLM.schemas
 │   ├── prompts.extraction_prompt
 │   ├── prompts.base_prompt
 │   └── word_process.checker (validator + corrector)
 ├── base_ppt.renderer.renderer                    (Step 6)
 │   └── pywin32 (COM)
 ├── word_process.processor.perception_splitter    (Step 7)
 ├── word_process.processor.perception_processor   (Step 7)
 ├── word_process.processor.markdown_ast           (Step 7)
 ├── word_process.processor.perception_semantic_chunker (Step 8)
 │   ├── LLM.client
 │   └── prompts.reconstruction_prompt
 ├── perception_ppt.content_process.assemble       (Step 9)
 │   └── pywin32 (COM)
 ├── perception_ppt.content_process.fill           (Step 9)
 │   └── pywin32 (COM)
 └── scripts.integrate                             (Step 11)
     └── pywin32 (COM)
```
