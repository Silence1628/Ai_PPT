"""
Stage 3: LLM 语义切分（~300字/段落）

将 preprocessed JSON 中每个 chunk 的 content 按语义切分为 sub_chunks，
每个 sub_chunk 约 300 字符，优先保持语义完整。

输入：word_process/llm_input/perception/preprocessed/{project}/{section}/task*_*.json
输出：word_process/llm_output/perception_json/{project}/{section}/task*_*.json
"""
import json
import re
from pathlib import Path
from typing import List, Optional

from LLM.client import LLMClient
from word_process.processor.prompts import (
    build_semantic_chunk_prompt,
    build_semantic_chunk_recursive_prompt,
)


class PerceptionSemanticChunker:
    """LLM 驱动的语义切分器（无 API key 时自动使用 fallback 规则切分）"""

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
        """延迟初始化 LLM 客户端，避免无 API key 时直接报错"""
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
                processed = self._chunk_data(data, project_name)

                out_path = self.output_dir / project_name / section / json_file.name
                out_path.parent.mkdir(parents=True, exist_ok=True)
                out_path.write_text(json.dumps(processed, ensure_ascii=False, indent=2), encoding='utf-8')
                results["files"].append(str(out_path))

        return results

    def _chunk_data(self, data: dict, project_name: str) -> dict:
        """对 data 中所有 chunk 执行语义切分"""
        result = {
            "task_num": data.get("task_num", ""),
            "task_title": data.get("task_title", ""),
            "section": data.get("section", ""),
            "chunks": []
        }

        for chunk in data.get("chunks", []):
            sub_chunks = self._semantic_split(chunk)
            result["chunks"].append({
                "id": chunk.get("id", ""),
                "title": chunk.get("title", ""),
                "parent_title": chunk.get("parent_title", ""),
                "level": chunk.get("level", 4),
                "content_count": len(sub_chunks),
                "sub_chunks": sub_chunks
            })

        return result

    def _semantic_split(self, chunk: dict) -> list:
        """对单个 chunk 的 content 进行语义切分"""
        content = chunk.get("content", "")
        code_blocks = chunk.get("code_blocks", [])
        chart_refs = chunk.get("chart_refs", [])

        if not content:
            return []

        # 短文本直接返回
        if len(content) <= self.max_chars:
            return [{
                "chunk_index": 1,
                "content": content,
                "code_blocks": code_blocks,
                "chart_refs": chart_refs
            }]

        # 调用 LLM 切分
        chunks_text = self._llm_chunk(content)
        sub_chunks = []
        for i, ct in enumerate(chunks_text):
            sub_chunks.append({
                "chunk_index": i + 1,
                "content": ct,
                "code_blocks": code_blocks if i == 0 else [],
                "chart_refs": chart_refs if i == len(chunks_text) - 1 else []
            })

        return sub_chunks

    def _llm_chunk(self, text: str) -> list[str]:
        """调用 LLM 切分（无客户端时直接用 fallback）"""
        if self.llm_client is None:
            return self._fallback_chunk(text)

        prompt = build_semantic_chunk_prompt(text, self.max_chars)
        messages = [{"role": "user", "content": prompt}]

        for attempt in range(self.max_retries):
            try:
                response = self.llm_client.chat(
                    messages=messages, temperature=0.3, max_tokens=4000
                )
                result = self._parse_json(response)
                if result and "chunks" in result:
                    chunks = [
                        c.get("content", c) if isinstance(c, dict) else c
                        for c in result["chunks"]
                    ]
                    chunks = self._recursive_split(chunks)
                    return chunks
            except Exception as e:
                print(f"    [WARN] LLM chunk attempt {attempt + 1}: {e}")

        print(f"    [WARN] LLM chunking failed, using fallback")
        return self._fallback_chunk(text)

    def _recursive_split(self, chunks: list[str]) -> list[str]:
        """递归切分超限 chunk"""
        result = []
        for chunk in chunks:
            if len(chunk) <= self.max_chars:
                result.append(chunk)
                continue

            # 尝试 LLM 递归
            sub = self._llm_recursive(chunk)
            if sub:
                result.extend(sub)
            else:
                result.extend(self._fallback_chunk(chunk))
        return result

    def _llm_recursive(self, text: str) -> list[str]:
        """对超限文本递归 LLM 切分"""
        if self.llm_client is None:
            return []

        prompt = build_semantic_chunk_recursive_prompt(text, len(text), self.max_chars)
        messages = [{"role": "user", "content": prompt}]

        for attempt in range(self.max_retries):
            try:
                response = self.llm_client.chat(
                    messages=messages, temperature=0.3, max_tokens=4000
                )
                result = self._parse_json(response)
                if result and "chunks" in result:
                    return [
                        c.get("content", c) if isinstance(c, dict) else c
                        for c in result["chunks"]
                    ]
            except Exception:
                continue
        return []

    def _parse_json(self, response: str) -> dict:
        """从 LLM 响应解析 JSON，增强容错处理中文引号等问题"""
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

        # 策略1: 直接解析
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # 策略2: 提取 {} 之间的内容
        first = text.find("{")
        last = text.rfind("}")
        if first != -1 and last != -1 and last > first:
            candidate = text[first:last + 1]
            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                pass

        # 策略3: regex 提取 chunks（容错中文引号等 JSON 非法字符）
        result = self._parse_json_regex(text)
        if result:
            return result

        raise ValueError("Failed to parse JSON")

    def _parse_json_regex(self, text: str) -> dict:
        """Regex fallback: 从可能包含非法字符的响应中提取 chunk 内容"""
        # 匹配 "content": "..." 或 "content": '...' 的内容部分
        # 考虑中间的转义符，直到遇到 ", <whitespace>"boundary" 或 "}] 结束
        chunks = []
        # 找每个 "content": " 开头
        pattern = re.compile(
            r'"content"\s*:\s*"((?:(?!",\s*"(?:boundary|chunk_index)").)*)"',
            re.DOTALL
        )
        for match in pattern.finditer(text):
            content = match.group(1)
            # 处理转义
            content = content.replace('\\"', '"').replace('\\n', '\n').replace('\\\\', '\\')
            if content.strip():
                chunks.append({"content": content})

        if chunks:
            return {"chunks": chunks}
        return {}

    def _fallback_chunk(self, text: str) -> list[str]:
        """Fallback: 按段落/句子边界硬切分"""
        paragraphs = text.split("\n")
        chunks = []
        current = ""

        for para in paragraphs:
            para = para.strip()
            if not para:
                if current:
                    chunks.append(current)
                    current = ""
                continue

            if len(current) + len(para) + 1 <= self.max_chars:
                current += ("\n" if current else "") + para
            else:
                if current:
                    chunks.append(current)
                if len(para) > self.max_chars:
                    # 句子边界切分
                    sub = self._split_by_sentence(para)
                    chunks.extend(sub)
                else:
                    current = para

        if current:
            chunks.append(current)
        return chunks if chunks else [text[:self.max_chars]]

    def _split_by_sentence(self, text: str) -> list[str]:
        """按句子边界切分长段落"""
        result = []
        current = ""
        sentences = re.split(r'([。！？；])', text)

        for i in range(0, len(sentences)):
            seg = sentences[i]
            if len(current) + len(seg) <= self.max_chars:
                current += seg
            else:
                if current:
                    result.append(current)
                current = seg

        if current:
            result.append(current)
        return result if result else [text[:self.max_chars]]


def main():
    from pathlib import Path

    PROJECT_ROOT = Path(__file__).parent.parent.parent
    input_dir = PROJECT_ROOT / "word_process" / "llm_input" / "perception" / "preprocessed"
    output_dir = PROJECT_ROOT / "word_process" / "llm_output" / "perception_json"

    chunker = PerceptionSemanticChunker(input_dir, output_dir)

    project_folders = [d for d in input_dir.iterdir() if d.is_dir() and d.name.startswith('项目')]
    for project_folder in sorted(project_folders):
        print(f"\n语义切分项目: {project_folder.name}")
        try:
            result = chunker.process(project_folder)
            print(f"  生成文件: {len(result['files'])}")
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"  错误: {e}")


if __name__ == "__main__":
    main()