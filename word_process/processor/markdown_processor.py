"""
MarkdownChunkProcessor - Markdown 转 JSON 处理器

参考 Ai_PPT/Word_Chunks/processor/processor.py 的两阶段架构：
- Stage 1: 批量生成所有字段（无字数限制 prompt）
- Stage 2: 由外部 check_and_correct() 修正超长字段

输入：
- 项目文件夹下的 md 文件（项目名.md, before_task.md, task1.md 等）

输出：
- word_process/llm_output/base_json/task{N}.json
"""
import json
import re
import time
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).parent.parent.parent.resolve()

from LLM.client import MiniMaxClient
from LLM.schemas import Chunk1Output, TaskOutput
from .prompts import build_chunk1_prompt, build_task_prompt


# Exact field order matching test_input.json
TASK_JSON_FIELD_ORDER = [
    "cover",
    "introduction",
    "thinking",
    "start",
    "catalog_one",
    "description",
    "catalog_two",
    "target",
    "catalog_three",
    "catalog_four",
    "catalog_five",
    "summary",
    "key_difficulties_summary",
    "catalog_six",
    "expansion",
]


class MarkdownChunkProcessor:
    """
    处理 Markdown 文件，输出 JSON 文件。

    Workflow:
    Stage 1: 生成原始 JSON（无字数限制）
    Stage 2: 由外部 check_and_correct() 处理（见 word_process/checker/）
    """

    def __init__(self, client: MiniMaxClient, output_dir: str = None):
        self.client = client
        if output_dir is None:
            output_dir = PROJECT_ROOT / "word_process" / "llm_output" / "base_json"
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.total_tokens = 0

    def process(self, project_folder: Path) -> list[Path]:
        """
        处理一个项目文件夹，生成多个 task JSON 文件。

        Args:
            project_folder: 项目文件夹路径，如 PROJECT_ROOT / "word_process" / "original" / "项目一   智能体应用初探专项实战"

        Returns:
            list[Path]: 生成的 task JSON 文件路径列表
        """
        # 1. 找项目 md 文件（项目名.md）
        md_files = list(project_folder.glob("*.md"))
        project_md = None
        for f in md_files:
            if f.name.startswith('项目') and f.name.endswith('.md'):
                project_md = f
                break

        if not project_md:
            raise FileNotFoundError(f"未找到项目 md 文件: {project_folder}")

        # 2. 找 task md 文件（task1.md, task2.md, task3.md）
        task_files = []
        for f in sorted(md_files):
            if re.match(r'^task\d+\.md$', f.name):
                task_files.append(f)

        if not task_files:
            raise FileNotFoundError(f"未找到 task md 文件: {project_folder}")

        print(f"[PROCESSOR] 项目: {project_folder.name}")
        print(f"[PROCESSOR] 项目md: {project_md.name}")
        print(f"[PROCESSOR] 任务数量: {len(task_files)}")

        self._current_project_name = project_folder.name
        self.total_tokens = 0

        # Stage 1: 处理 chunk1（项目介绍+引导案例）
        print("[PROCESSOR] 开始 Stage 1: LLM 生成 JSON...")
        chunk1_start = time.time()
        chunk1_data = self._process_chunk1(project_md)
        chunk1_elapsed = time.time() - chunk1_start
        print(f"[PROCESSOR] Chunk1 素材提取完成，耗时 {chunk1_elapsed:.1f}s")

        # Stage 2: 串行生成 Task JSON
        print("[PROCESSOR] 开始串行生成 Task JSON（{}个任务）...".format(len(task_files)))
        output_files = self._process_tasks_serial(task_files, chunk1_data)

        return output_files

    def _process_chunk1(self, project_md: Path) -> dict:
        """处理 chunk1，提取共享数据"""
        start_time = time.time()
        content = project_md.read_text(encoding='utf-8')
        prompt = build_chunk1_prompt(content)
        messages = [{"role": "user", "content": prompt}]
        result = self.client.chat_with_stats(messages, temperature=0.7, reasoning_split=True, max_tokens=4000)

        self._track_tokens(result.get("usage"))
        json_str = self._extract_json(result["content"])
        data = json.loads(json_str)
        validated = Chunk1Output(**data)
        elapsed = time.time() - start_time
        print(f"[CHUNK1] 完成，耗时 {elapsed:.1f}s，tokens: {self._format_tokens(result.get('usage'))}")
        return validated.model_dump()

    def _process_tasks_serial(self, task_files: list[Path], chunk1_data: dict) -> list[Path]:
        """串行处理多个 task md 文件"""
        results = []
        for i, task_file in enumerate(task_files, 1):
            output_path = self._process_task(task_file, i, chunk1_data)
            results.append(output_path)
        return results

    def _process_task(self, task_md: Path, index: int, chunk1_data: dict) -> Path:
        """Stage 1: 生成原始 task JSON（无字数检查）"""
        start_time = time.time()
        print(f"[PROCESSOR] 开始生成 Task {index}: {task_md.name}...")
        content = task_md.read_text(encoding='utf-8')

        # 从文件名提取 task 编号和标题
        title = self._extract_title_from_filename(task_md.name, content)

        prompt = build_task_prompt(title, content, chunk1_data)
        messages = [{"role": "user", "content": prompt}]

        MAX_RETRIES = 2
        data = None
        total_task_tokens = 0

        result = self.client.chat_with_stats(messages, temperature=0.7, reasoning_split=True, max_tokens=4000)
        total_task_tokens += self._get_tokens(result.get("usage"))
        response = result["content"]

        for attempt in range(MAX_RETRIES + 1):
            if attempt > 0:
                print(f"[TASK {index}] JSON解析重试 ({attempt}/{MAX_RETRIES})...")
                result = self.client.chat_with_stats(messages, temperature=0.7, reasoning_split=True, max_tokens=4000)
                total_task_tokens += self._get_tokens(result.get("usage"))
                response = result["content"]

            json_str = self._extract_json(response)
            if not json_str:
                if attempt == MAX_RETRIES:
                    raise ValueError(f"Empty JSON response for task {index}")
                continue

            try:
                data = json.loads(json_str)
                break
            except json.JSONDecodeError as e:
                if attempt == MAX_RETRIES:
                    print(f"[TASK {index}] JSON解析失败: {e}，尝试修复...")
                    data = self._try_fix_json(json_str, index)
                    if data is None:
                        print(f"[TASK {index}] 修复失败，使用最小有效结构")
                        data = self._get_minimal_task_structure()
                    break
                else:
                    print(f"[TASK {index}] JSON解析失败: {e}，重试...")

        # 确保所有 required sections 存在
        required_sections = [
            "cover", "introduction", "thinking", "start",
            "catalog_one", "catalog_two", "catalog_three",
            "catalog_four", "catalog_five", "catalog_six",
            "description", "target", "summary",
            "key_difficulties_summary", "expansion",
        ]
        for section in required_sections:
            if section not in data:
                data[section] = {}
            elif not isinstance(data[section], dict):
                data[section] = {}

        validated = TaskOutput(**data)
        output_data = validated.model_dump()

        # 从标题提取 task_num 和 task_name
        task_num = self._extract_task_num_from_title(title)
        task_name = self._extract_task_name_from_title(title)

        # 标准化所有 catalog 字段
        for cat_key in ["catalog_one", "catalog_two", "catalog_three",
                        "catalog_four", "catalog_five", "catalog_six"]:
            output_data[cat_key]["task_num"] = task_num
            output_data[cat_key]["task_name"] = task_name

        # 标准化 start 和 cover
        output_data["start"]["task_num"] = task_num
        output_data["start"]["task_name"] = task_name

        # 填充缺失的 task_requirements
        output_data = self._fill_task_requirements_from_targets(output_data)

        # 用原文直接覆盖 task_summary（不需要 LLM 处理，避免压缩改写）
        original_summary = self._extract_task_summary(content)
        if original_summary:
            output_data.setdefault("summary", {})["task_summary"] = self._truncate_at_sentence(original_summary, 140)

        # 按 field order 重排列
        ordered_output = {k: output_data[k] for k in TASK_JSON_FIELD_ORDER if k in output_data}

        out_subdir = self.output_dir / self._current_project_name
        out_subdir.mkdir(parents=True, exist_ok=True)
        output_path = out_subdir / f"task{index}_base.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(ordered_output, f, ensure_ascii=False, indent=2)

        elapsed = time.time() - start_time
        print(f"[TASK {index}] Stage 1 完成: {output_path.name}，耗时 {elapsed:.1f}s，tokens: {total_task_tokens}")
        self.total_tokens += total_task_tokens
        return output_path

    @staticmethod
    def _truncate_at_sentence(text: str, max_len: int) -> str:
        """按句子边界截断文本，不超过 max_len"""
        if len(text) <= max_len:
            return text
        # 在 max_len 范围内找最后一个句尾标点
        cut = max_len
        for sep in ['。', '？', '！', '；', '\n']:
            pos = text[:max_len].rfind(sep)
            if pos > cut // 2:  # 至少保留一半
                cut = pos + 1
                break
        return text[:cut]

    def _extract_task_summary(self, content: str) -> str:
        """从 markdown 的【任务小结】段落提取原文（不经过 LLM）"""
        idx = content.find('【任务小结】')
        if idx < 0:
            return ""
        after = content[idx:]
        lines = after.split('\n')
        summary_parts = []
        for line in lines[1:]:
            stripped = line.strip()
            if stripped.startswith('##') or stripped.startswith('###') or stripped.startswith('【'):
                break
            if stripped:
                summary_parts.append(stripped)
            elif summary_parts:
                break
        return '\n'.join(summary_parts)

    def _extract_title_from_filename(self, filename: str, content: str) -> str:
        """从 task md 文件名和内容提取标题"""
        # 文件名如 task1.md，提取出 task1
        stem = Path(filename).stem  # e.g. "task1"
        # 尝试从内容第一行提取标题（### 任务一 xxx）
        first_line = content.split('\n')[0].strip() if content else ""
        if first_line.startswith('#'):
            return first_line.lstrip('#').strip()
        return stem

    def _extract_task_num_from_title(self, title: str) -> str:
        """从标题提取任务编号，如 '任务二 AIGC...' → '二'"""
        match = re.search(r'任务([一二三四五六\d]+)', title)
        if match:
            return match.group(1)
        return title

    def _extract_task_name_from_title(self, title: str) -> str:
        """从标题提取任务名称，如 '任务二 AIGC...' → 'AIGC...'"""
        match = re.search(r'任务([一二三四五六\d]+)\s+(.+)', title)
        if match:
            return match.group(2).strip()
        return title

    def _is_placeholder(self, val: str) -> bool:
        """检查是否是无意义的占位符"""
        if not isinstance(val, str):
            return True
        stripped = val.strip()
        if stripped == "":
            return True
        if stripped.replace("。", "") == "":
            return True
        return False

    def _fill_task_requirements_from_targets(self, output_data: dict) -> dict:
        """
        如果 description.task_requirements 少于5条，从 task_target 字段补充。
        """
        req_fields = [f"task_requirements{i}" for i in range(1, 6)]
        target_fields = [f"task_target{i}" for i in range(1, 5)]

        filled_count = 0
        for f in req_fields:
            val = output_data.get("description", {}).get(f, "")
            if not self._is_placeholder(val):
                filled_count += 1

        if filled_count >= 5:
            return output_data

        available_targets = []
        for f in target_fields:
            val = output_data.get("target", {}).get(f, "")
            if not self._is_placeholder(val):
                available_targets.append(val)

        slots_needed = 5 - filled_count
        for i, val in enumerate(available_targets[:slots_needed]):
            for f in req_fields:
                current = output_data.get("description", {}).get(f, "")
                if self._is_placeholder(current):
                    output_data.setdefault("description", {})[f] = val
                    break

        return output_data

    def _get_minimal_task_structure(self) -> dict:
        """返回最小有效 task JSON 结构"""
        return {
            "cover": {},
            "introduction": {},
            "thinking": {},
            "start": {},
            "catalog_one": {},
            "catalog_two": {},
            "catalog_three": {},
            "catalog_four": {},
            "catalog_five": {},
            "catalog_six": {},
            "description": {
                "task_description": "",
                "task_requirements1": "",
                "task_requirements2": "",
                "task_requirements3": "",
                "task_requirements4": "",
                "task_requirements5": "",
            },
            "target": {
                "task_target1": "",
                "task_target2": "",
                "task_target3": "",
                "task_target4": "",
                "task_focus": "",
                "task_difficulty": "",
            },
            "summary": {"task_summary": ""},
            "key_difficulties_summary": {
                "key_summary1": "",
                "key_summary2": "",
                "key_summary3": "",
                "difficulties_summary1": "",
                "difficulties_summary2": "",
                "difficulties_summary3": "",
            },
            "expansion": {"skill_practice": "", "solving_ideas": ""},
        }

    def _try_fix_json(self, json_str: str, index: int) -> dict | None:
        """尝试修复损坏的 JSON"""
        print(f"[TASK {index}] JSON修复: 原始长度={len(json_str)}")

        # 方案1：找最后一个 depth=0 的 }
        try:
            last_valid_pos = 0
            depth = 0
            in_string = False
            escape_next = False

            for i, c in enumerate(json_str):
                if escape_next:
                    escape_next = False
                    continue
                if c == '\\' and in_string:
                    escape_next = True
                    continue
                if c == '"':
                    in_string = not in_string
                    continue
                if in_string:
                    continue
                if c == '{':
                    depth += 1
                elif c == '}':
                    depth -= 1
                    if depth == 0:
                        last_valid_pos = i + 1
                        break

            if last_valid_pos > 0:
                fixed = json_str[:last_valid_pos]
                data = json.loads(fixed)
                print(f"[TASK {index}] JSON修复成功（截取方案），字段数: {len(data)}")
                return data
        except Exception as e:
            print(f"[TASK {index}] 截取方案失败: {e}")

        # 方案2：补全缺失
        try:
            fixed = json_str
            if not fixed.strip().endswith('}'):
                fixed = fixed.rstrip(',') + '}'
            data = json.loads(fixed)
            print(f"[TASK {index}] JSON修复成功（补全方案），字段数: {len(data)}")
            return data
        except Exception as e:
            print(f"[TASK {index}] 补全方案也失败: {e}")

        return None

    def _extract_json(self, text: str) -> str:
        """
        从 LLM 响应中提取 JSON 字符串。

        使用边界法：找第一个 { 和最后一个 }，渐进扩展验证。
        """
        text = text.strip()
        if text.startswith("```"):
            text = re.sub(r"^```json\s*", "", text)
            text = re.sub(r"\s*```$", "", text)
        text = text.strip()

        first_brace = text.find("{")
        last_brace = text.rfind("}")
        if first_brace == -1 or last_brace == -1 or last_brace <= first_brace:
            return text

        extracted = text[first_brace:last_brace + 1]

        # 验证 JSON 是否完整
        try:
            json.loads(extracted)
            return extracted
        except json.JSONDecodeError:
            pass

        # 渐进扩展（应对 LLM 输出截断）
        base_end = text.rfind("}")
        if base_end == -1:
            return extracted

        for extension in range(1, 20):
            extended = text[first_brace:base_end + extension]
            try:
                json.loads(extended)
                return extended
            except json.JSONDecodeError:
                continue

        return extracted

    def _track_tokens(self, usage: dict):
        """跟踪 token 使用"""
        if usage:
            self.total_tokens += usage.get("total_tokens", 0)

    def _get_tokens(self, usage: dict) -> int:
        """从 usage dict 获取 token 数"""
        if usage:
            return usage.get("total_tokens", 0)
        return 0

    def _format_tokens(self, usage: dict) -> str:
        """格式化 token 使用信息"""
        if not usage:
            return "N/A"
        return f"prompt={usage.get('prompt_tokens', 0)}, completion={usage.get('completion_tokens', 0)}, total={usage.get('total_tokens', 0)}"