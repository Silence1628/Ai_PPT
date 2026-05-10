import json
import re
import concurrent.futures
from pathlib import Path
from datetime import datetime
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


class WordChunkProcessor:
    """
    Process Word chunks through LLM and output JSON files.

    Workflow:
    Stage 1: Generate raw JSON (no length checking)
    Stage 2: Handled by separate Checker module (Word_Chunks/checker/)
    """

    def __init__(self, client: MiniMaxClient, output_dir: str = "output"):
        self.client = client
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

    def _cleanup_output(self):
        """Delete all task*.json files in output_dir to avoid naming conflicts."""
        for f in self.output_dir.glob("task*.json"):
            f.unlink()

    def process(self, chunks: list[dict], max_workers: int = 3) -> list[Path]:
        """
        Two-stage process:
        - Stage 1: Generate raw JSON (fast, no length checking)
        - Stage 2: Post-process each JSON file (length validation + correction)

        Args:
            chunks: List of 4 dicts from chunker, index 0=chunk1, 1-3=tasks
            max_workers: Max parallel thread workers for task processing (default 3)

        Returns:
            list[Path]: Paths to the 3 output task JSON files
        """
        if len(chunks) < 4:
            raise ValueError(f"Expected 4 chunks, got {len(chunks)}")

        self._cleanup_output()

        # Stage 1: Fast generation — no length checking
        print("[PROCESSOR] 开始 Stage 1: LLM 生成 JSON...")
        chunk1_data = self._process_chunk1(chunks[0])
        print("[PROCESSOR] Chunk1 素材提取完成，开始并行生成 Task JSON...")
        output_files = self._process_tasks_parallel(chunks[1:], chunk1_data, max_workers)

        return output_files

    def _process_chunk1(self, chunk: dict) -> dict:
        """Process chunk1, extract shared data for all task JSONs."""
        prompt = build_chunk1_prompt(chunk["content"])
        messages = [{"role": "user", "content": prompt}]
        response = self.client.chat(messages, temperature=0.7, reasoning_split=True, max_tokens=4000)

        json_str = self._extract_json(response)
        data = json.loads(json_str)
        validated = Chunk1Output(**data)
        return validated.model_dump()

    def _process_tasks_parallel(
        self, task_chunks: list[dict], chunk1_data: dict, max_workers: int
    ) -> list[Path]:
        """Process task chunks in parallel using ThreadPoolExecutor."""
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(self._process_task, chunk, i + 1, chunk1_data): i
                for i, chunk in enumerate(task_chunks)
            }
            results = [None] * len(task_chunks)
            for future in concurrent.futures.as_completed(futures):
                idx = futures[future]
                results[idx] = future.result() 
            return results

    def _process_task(self, chunk: dict, index: int, chunk1_data: dict) -> Path:
        """Stage 1: Generate raw task JSON without any length checking."""
        print(f"[PROCESSOR] 开始生成 Task {index}: {chunk['title'][:30]}...")
        prompt = build_task_prompt(chunk["title"], chunk["content"], chunk1_data)
        messages = [{"role": "user", "content": prompt}]

        MAX_RETRIES = 2
        data = None

        # 第一次调用 LLM
        response = self.client.chat(messages, temperature=0.7, reasoning_split=True, max_tokens=4000)

        for attempt in range(MAX_RETRIES + 1):
            if attempt > 0:
                print(f"[TASK {index}] JSON解析重试 ({attempt}/{MAX_RETRIES})...")
                response = self.client.chat(messages, temperature=0.7, reasoning_split=True, max_tokens=4000)

            json_str = self._extract_json(response)
            if not json_str:
                if attempt == MAX_RETRIES:
                    raise ValueError(f"Empty JSON response for task {index}")
                continue

            try:
                data = json.loads(json_str)
                break  # 解析成功，跳出重试循环
            except json.JSONDecodeError as e:
                if attempt == MAX_RETRIES:
                    print(f"[TASK {index}] JSON解析重试{MAX_RETRIES}次均失败，尝试修复...")
                    data = self._try_fix_json(json_str, index)
                    if data is None:
                        print(f"[TASK {index}] 修复失败，使用最小有效结构")
                        data = self._get_minimal_task_structure()
                    break
                else:
                    print(f"[TASK {index}] JSON解析失败: {e}，重试...")

        # Robustness: ensure all required top-level keys exist as dicts
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

        # Extract task_num from the title (e.g., "任务二 基于ollama..." → "二")
        task_num = self._extract_task_num_from_title(chunk["title"])
        task_name = self._extract_task_name_from_title(chunk["title"])

        # Normalize all catalog fields: task_num and task_name must be identical
        for cat_key in ["catalog_one", "catalog_two", "catalog_three",
                        "catalog_four", "catalog_five", "catalog_six"]:
            output_data[cat_key]["task_num"] = task_num
            output_data[cat_key]["task_name"] = task_name

        # Also normalize start and cover
        output_data["start"]["task_num"] = task_num
        output_data["start"]["task_name"] = task_name

        # Fill missing task_requirements from task_target fields
        output_data = self._fill_task_requirements_from_targets(output_data)

        # Reorder fields to exactly match test_input.json
        ordered_output = {k: output_data[k] for k in TASK_JSON_FIELD_ORDER if k in output_data}

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = self.output_dir / f"task{index}_{timestamp}.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(ordered_output, f, ensure_ascii=False, indent=2)

        print(f"[TASK {index}] Stage 1 完成: {output_path.name}")
        return output_path

    def _extract_task_num_from_title(self, title: str) -> str:
        """Extract task number from title like '任务二 AIGC...' → '二'"""
        match = re.search(r"任务([一二三四五六]+)", title)
        if match:
            return match.group(1)
        return title

    def _extract_task_name_from_title(self, title: str) -> str:
        """Extract task name from title like '任务二 AIGC...' → 'AIGC...'"""
        match = re.search(r"任务([一二三四五六]+)\s+(.+)", title)
        if match:
            return match.group(2).strip()
        return title

    def _is_placeholder(self, val: str) -> bool:
        """Check if a string is a meaningless placeholder (only '。' or empty)."""
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
        If description.task_requirements has fewer than 5 filled entries,
        fill the remaining slots with task_target fields (1→4) in order.
        task_target fields themselves remain unchanged.
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
        """返回最小有效 task JSON 结构（所有必要字段为空值）"""
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
        """尝试修复损坏的 JSON，提取有效字段返回默认值结构"""
        import traceback
        print(f"[TASK {index}] JSON修复: 原始长度={len(json_str)}")

        # 方案1：尝试只提取前半部分，看能否构成有效JSON
        try:
            # 找到最后一个完整对象的结束位置
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

        # 方案2：尝试用默认值补全缺失部分
        try:
            # 尝试补全常见的缺失逗号
            fixed = json_str

            # 尝试补全对象结尾
            if not fixed.strip().endswith('}'):
                fixed = fixed.rstrip(',') + '}'

            data = json.loads(fixed)
            print(f"[TASK {index}] JSON修复成功（补全方案），字段数: {len(data)}")
            return data
        except Exception as e:
            print(f"[TASK {index}] 补全方案也失败: {e}")

        # 方案3：返回最小有效结构，让后续流程能继续
        print(f"[TASK {index}] 所有修复方案失败，返回默认结构")
        return None

    def _extract_json(self, text: str) -> str:
        """Extract JSON string from LLM response.

        改进：提取后验证 JSON 是否完整，失败则渐进扩展搜索完整边界。
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

        # 验证：尝试解析提取的内容
        try:
            json.loads(extracted)
            return extracted  # 解析成功，返回完整 JSON
        except json.JSONDecodeError:
            pass

        # 解析失败，尝试渐进扩展（LLM 输出截断时，最后一个 } 可能不是真正的 JSON 结尾）
        base_end = text.rfind("}")
        if base_end == -1:
            return extracted  # 没有 }，无法扩展

        for extension in range(1, 20):
            extended = text[first_brace:base_end + extension]
            try:
                json.loads(extended)
                return extended
            except json.JSONDecodeError:
                continue

        # 所有扩展都失败，返回原提取内容让调用方处理
        return extracted