"""
Stage 3: LLM 理解+重构内容为 ~300字 PPT 段落

将 preprocessed JSON 中所有 chunk 按 H3 分组，每组送给 LLM 理解后
重新组织为约300字的独立段落，填充到对应 H4 chunk 的 sub_chunks。

输入：word_process/llm_input/perception/preprocessed/{project}/{section}/task*_*.json
输出：word_process/llm_output/perception_json/{project}/{section}/task*_*.json
"""
import json
import re
from collections import OrderedDict
from pathlib import Path
from typing import List, Optional

from LLM.client import LLMClient
from word_process.processor.prompts import (
    build_semantic_chunk_prompt,
    build_semantic_chunk_recursive_prompt,
)


class PerceptionSemanticChunker:
    """LLM 驱动的语义重构器（无 API key 时使用 fallback）"""

    def __init__(self, input_dir: Path, output_dir: Path,
                 llm_client: Optional[LLMClient] = None,
                 max_chars: int = 300, max_retries: int = 3):
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        self._llm_client = llm_client
        self._llm_client_attempted = False
        self.max_chars = max_chars
        self.max_retries = max_retries

    @property
    def llm_client(self):
        if self._llm_client is None and not self._llm_client_attempted:
            self._llm_client_attempted = True
            try:
                self._llm_client = LLMClient()
            except (ValueError, Exception):
                pass
        return self._llm_client

    def process(self, project_folder: Path) -> dict:
        project_name = project_folder.name
        results = {"project": project_name, "files": []}

        for section in ["knowledge", "task"]:
            section_dir = self.input_dir / project_name / section
            if not section_dir.exists():
                continue

            json_files = sorted(section_dir.glob("*.json"))
            for json_file in json_files:
                data = json.loads(json_file.read_text(encoding='utf-8'))
                processed = self._process_data(data)

                out_path = self.output_dir / project_name / section / json_file.name
                out_path.parent.mkdir(parents=True, exist_ok=True)
                out_path.write_text(json.dumps(processed, ensure_ascii=False, indent=2), encoding='utf-8')
                results["files"].append(str(out_path))

        return results

    def _process_data(self, data: dict) -> dict:
        """按 H3 分组后送给 LLM 重构"""
        chunks = data.get("chunks", [])
        result = {
            "task_num": data.get("task_num", ""),
            "task_title": data.get("task_title", ""),
            "section": data.get("section", ""),
            "chunks": []
        }

        # Group chunks by parent_title (H3)
        groups = OrderedDict()
        for chunk in chunks:
            parent = chunk.get("parent_title", "") or chunk.get("title", "")
            if parent not in groups:
                groups[parent] = []
            groups[parent].append(chunk)

        table_data = [{
            "title": c.get("title", ""),
            "content": c.get("content", ""),
            "code_blocks": c.get("code_blocks", []),
            "chart_refs": c.get("chart_refs", []),
            "h4_id": c.get("id", ""),
            "level": c.get("level", 4),
        } for c in chunks]

        # For each H3 group, call LLM to restructure all H4s together
        for parent_title, h4_chunks in groups.items():
            if self.llm_client is None:
                # Fallback: do simple sentence-based split per chunk
                for c in h4_chunks:
                    result["chunks"].append(self._fallback_chunk_output(c))
                continue

            # Build H4 content list for LLM
            h4_contents = [{"title": c["title"], "content": c["content"]}
                          for c in h4_chunks if c.get("content")]

            if not any(hc["content"] for hc in h4_contents):
                for c in h4_chunks:
                    result["chunks"].append(self._empty_chunk_output(c))
                continue

            # Call LLM with the group
            paragraphs_map = self._llm_restructure_group(parent_title, h4_contents)

            # Map LLM paragraphs back to H4 chunks
            for c in h4_chunks:
                h4_title = c["title"]
                paragraphs = paragraphs_map.get(h4_title, [])
                if not paragraphs:
                    # LLM didn't return paragraphs for this H4, fallback
                    sub_chunks = self._fallback_paragraphs(c.get("content", ""))
                else:
                    sub_chunks = self._paragraphs_to_sub_chunks(
                        paragraphs, c.get("code_blocks", []), c.get("chart_refs", [])
                    )
                result["chunks"].append({
                    "id": c.get("id", ""),
                    "title": c["title"],
                    "parent_title": c.get("parent_title", ""),
                    "level": c.get("level", 4),
                    "content_count": len(sub_chunks),
                    "sub_chunks": sub_chunks
                })

        return result

    def _llm_restructure_group(self, parent_title: str, h4_contents: list[dict]) -> dict:
        """调用 LLM 重构一个 H3 下所有 H4 的内容，返回 {h4_title: [paragraphs]}"""
        prompt = build_semantic_chunk_prompt(parent_title, h4_contents)
        messages = [{"role": "user", "content": prompt}]

        for attempt in range(self.max_retries):
            try:
                response = self.llm_client.chat(
                    messages=messages, temperature=0.3, max_tokens=8000
                )
                result = self._parse_json(response)
                if result and "h4_sections" in result:
                    # Map results: {title: paragraphs}
                    para_map = {}
                    for sec in result["h4_sections"]:
                        sec_title = sec.get("title", "")
                        paragraphs = sec.get("paragraphs", [])
                        # Try exact match, then fuzzy match
                        matched_title = self._match_h4_title(sec_title, h4_contents)
                        if matched_title:
                            para_map[matched_title] = paragraphs
                    return para_map
            except Exception as e:
                print(f"    [WARN] LLM restructure attempt {attempt + 1}: {e}")

        print(f"    [WARN] LLM restructure failed, using fallback")
        return {}

    def _match_h4_title(self, llm_title: str, h4_contents: list[dict]) -> str:
        """Match LLM-returned title back to original H4 title"""
        for h4 in h4_contents:
            if h4["title"] == llm_title:
                return h4["title"]
        # Fuzzy: check if one contains the other
        for h4 in h4_contents:
            if h4["title"] in llm_title or llm_title in h4["title"]:
                return h4["title"]
        # First few chars match
        for h4 in h4_contents:
            if h4["title"][:4] == llm_title[:4]:
                return h4["title"]
        return ""

    def _paragraphs_to_sub_chunks(self, paragraphs: list[str],
                                  code_blocks: list, chart_refs: list) -> list:
        """Convert LLM paragraphs to sub_chunks format"""
        sub_chunks = []
        for i, para in enumerate(paragraphs):
            # Recursively split overly long paragraphs
            if len(para) > self.max_chars * 3:
                sub_paras = self._llm_recursive_split(para)
                for sp in sub_paras:
                    i += 1
                    sub_chunks.append({
                        "chunk_index": len(sub_chunks) + 1,
                        "content": sp,
                        "code_blocks": [],
                        "chart_refs": []
                    })
            else:
                sub_chunks.append({
                    "chunk_index": i + 1,
                    "content": para,
                    "code_blocks": code_blocks if i == 0 else [],
                    "chart_refs": chart_refs if i == len(paragraphs) - 1 else []
                })
        return sub_chunks

    def _llm_recursive_split(self, text: str) -> list[str]:
        """递归拆分过长段落"""
        if self.llm_client is None:
            return self._fallback_paragraphs(text)

        prompt = build_semantic_chunk_recursive_prompt(text)
        messages = [{"role": "user", "content": prompt}]

        for attempt in range(self.max_retries):
            try:
                response = self.llm_client.chat(
                    messages=messages, temperature=0.3, max_tokens=4000
                )
                result = self._parse_json(response)
                if result and "paragraphs" in result:
                    return result["paragraphs"]
            except Exception:
                continue
        return self._fallback_paragraphs(text)

    def _empty_chunk_output(self, chunk: dict) -> dict:
        return {
            "id": chunk.get("id", ""),
            "title": chunk.get("title", ""),
            "parent_title": chunk.get("parent_title", ""),
            "level": chunk.get("level", 4),
            "content_count": 0,
            "sub_chunks": []
        }

    def _fallback_chunk_output(self, chunk: dict) -> dict:
        """Fallback: 单 chunk 按句子切分"""
        sub_chunks = self._fallback_paragraphs(chunk.get("content", ""))
        for i, sc in enumerate(sub_chunks):
            if i == 0:
                sc["code_blocks"] = chunk.get("code_blocks", [])
            if i == len(sub_chunks) - 1:
                sc["chart_refs"] = chunk.get("chart_refs", [])
        return {
            "id": chunk.get("id", ""),
            "title": chunk.get("title", ""),
            "parent_title": chunk.get("parent_title", ""),
            "level": chunk.get("level", 4),
            "content_count": len(sub_chunks),
            "sub_chunks": sub_chunks
        }

    def _fallback_paragraphs(self, text: str) -> list[dict]:
        """按段落/句子边界切分，返回 sub_chunk dict 列表"""
        if not text:
            return []
        if len(text) <= self.max_chars:
            return [{"chunk_index": 1, "content": text, "code_blocks": [], "chart_refs": []}]

        paragraphs = text.split("\n")
        raw = []
        current = ""
        for para in paragraphs:
            para = para.strip()
            if not para:
                if current:
                    raw.append(current)
                    current = ""
                continue
            if len(current) + len(para) + 1 <= self.max_chars:
                current += ("\n" if current else "") + para
            else:
                if current:
                    raw.append(current)
                current = para
        if current:
            raw.append(current)
        if not raw:
            raw = [text[:self.max_chars]]
        return [{"chunk_index": i + 1, "content": p, "code_blocks": [], "chart_refs": []}
                for i, p in enumerate(raw)]

    def _parse_json(self, response: str) -> dict:
        """从 LLM 响应解析 JSON"""
        text = response.strip()
        if "</think>" in text:
            text = text[text.find("</think>") + 7:].strip()
        if text.startswith("```json"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        first = text.find("{")
        last = text.rfind("}")
        if first != -1 and last != -1 and last > first:
            try:
                return json.loads(text[first:last + 1])
            except json.JSONDecodeError:
                pass
        # Regex fallback for paragraphs
        result = self._parse_json_regex(text)
        if result:
            return result
        raise ValueError("Failed to parse JSON")

    def _parse_json_regex(self, text: str) -> dict:
        """Regex fallback: 从 LLM 响应提取 paragraphs"""
        paragraphs = []
        pattern = re.compile(r'"paragraphs"\s*:\s*\[(.*?)\]', re.DOTALL)
        match = pattern.search(text)
        if match:
            content_match = re.findall(r'"([^"]*)"', match.group(1))
            paragraphs = [c for c in content_match if c.strip()]
        if paragraphs:
            return {"h4_sections": [{"title": "", "paragraphs": paragraphs}]}
        return {}


def main():
    from pathlib import Path
    PROJECT_ROOT = Path(__file__).parent.parent.parent
    input_dir = PROJECT_ROOT / "word_process" / "llm_input" / "perception" / "preprocessed"
    output_dir = PROJECT_ROOT / "word_process" / "llm_output" / "perception_json"
    chunker = PerceptionSemanticChunker(input_dir, output_dir)
    project_folders = [d for d in input_dir.iterdir() if d.is_dir() and d.name.startswith('项目')]
    for project_folder in sorted(project_folders):
        print(f"\n语义重构项目: {project_folder.name}")
        try:
            result = chunker.process(project_folder)
            print(f"  生成文件: {len(result['files'])}")
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"  错误: {e}")


if __name__ == "__main__":
    main()
