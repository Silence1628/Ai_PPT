"""
SemanticChunker - 基于 LLM 的语义文本切分器

功能：
- 读取 markdown 文件，调用 LLM 进行语义切分
- 将切分结果填充到对应的 JSON 结构中
- 支持递归切分处理超长内容
"""

import json
import re
from pathlib import Path
from typing import Optional

from LLM.client import MiniMaxClient
from Word_Chunks.processor.prompts import (
    build_semantic_chunk_prompt,
    build_semantic_chunk_recursive_prompt
)


class SemanticChunker:
    """
    LLM 驱动的语义文本切分器

    流程：
    1. 读取 markdown 文件和对应的 JSON 结构
    2. 对每个 heading 下的 content 调用 LLM 语义切分
    3. 将切分结果填充到 JSON 的 content_chunks 字段
    4. 输出到 padding_content 目录
    """

    def __init__(self, llm_client: Optional[MiniMaxClient] = None, max_retries: int = 3):
        self.llm_client = llm_client or MiniMaxClient()
        self.max_retries = max_retries

    def chunk_from_markdown(self, markdown_dir: Path, json_dir: Path, output_dir: Path, max_chars: int):
        """
        读取 markdown 文件，调用 LLM 切分，填充到 JSON 并输出。

        Args:
            markdown_dir: markdown 文件所在目录
            json_dir: JSON 结构文件所在目录（chunks=[]）
            output_dir: 输出目录（padding_content）
            max_chars: 每个 chunk 的最大字符数
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # 遍历 markdown 文件
        for md_file in sorted(markdown_dir.glob("*.md")):
            json_file = json_dir / md_file.with_suffix(".json").name

            if not json_file.exists():
                print(f"  [WARN] JSON not found for {md_file.name}, skipping")
                continue

            print(f"  [SemanticChunker] Processing {md_file.name}")

            # 解析 markdown 内容
            segments_content = self._parse_markdown(md_file)

            # 读取 JSON 结构
            with open(json_file, "r", encoding="utf-8") as f:
                json_data = json.load(f)

            # 对每个 segment 进行语义切分
            for seg in json_data.get("segments", []):
                heading = seg.get("heading", "")
                content = segments_content.get(heading, "")

                if not content:
                    seg["content_chunks"] = []
                    seg["heading_chunk_count"] = 0
                    continue

                # 调用 LLM 切分
                chunks = self._llm_chunk(content, max_chars)
                seg["content_chunks"] = [
                    {"chunk_index": i + 1, "content": chunk}
                    for i, chunk in enumerate(chunks)
                ]
                seg["heading_chunk_count"] = len(chunks)

            # 添加 schema_name
            json_data["schema_name"] = json_file.stem.replace("task", "").replace("_knowledge", "").replace("_implementation", "")

            # 输出到 padding_content
            output_file = output_dir / json_file.name
            if output_file.exists():
                output_file.unlink()
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(json_data, f, ensure_ascii=False, indent=2)

            print(f"    → {output_file.name}")

    def _parse_markdown(self, md_file: Path) -> dict:
        """
        解析 markdown 文件，返回 {heading: content} 的字典。
        """
        with open(md_file, "r", encoding="utf-8") as f:
            content = f.read()

        segments = {}
        current_heading = None
        current_content = []

        for line in content.split("\n"):
            line = line.strip()
            if not line:
                continue

            # 检测二级标题（## 开头）
            if line.startswith("## "):
                # 保存上一个 heading 的内容
                if current_heading:
                    segments[current_heading] = "\n".join(current_content).strip()

                current_heading = line[3:].strip()
                current_content = []
            elif current_heading:
                current_content.append(line)

        # 保存最后一个 heading
        if current_heading:
            segments[current_heading] = "\n".join(current_content).strip()

        return segments

    def _llm_chunk(self, text: str, max_chars: int) -> list[str]:
        """
        调用 LLM 进行语义切分。
        """
        if not text:
            return []

        # 如果文本本身就小于 max_chars，直接返回
        if len(text) <= max_chars:
            return [text]

        prompt = build_semantic_chunk_prompt(text, max_chars)
        messages = [{"role": "user", "content": prompt}]

        for attempt in range(self.max_retries):
            try:
                response = self.llm_client.chat(
                    messages=messages,
                    temperature=0.3,
                    max_tokens=4000
                )

                result = self._parse_json_response(response)
                if result and "chunks" in result:
                    chunks = [c.get("content", c) if isinstance(c, dict) else c for c in result["chunks"]]
                    # 递归检查是否有 chunk 仍超限
                    chunks = self._recursive_split(chunks, max_chars)
                    return chunks

            except Exception as e:
                print(f"    [WARN] LLM chunking attempt {attempt + 1} failed: {e}")
                continue

        # 重试全部失败后，使用 fallback
        print(f"    [WARN] LLM chunking failed, using fallback")
        return self._fallback_chunk(text, max_chars)

    def _recursive_split(self, chunks: list[str], max_chars: int) -> list[str]:
        """
        递归检查并切分超限的 chunks。
        """
        result = []
        for chunk in chunks:
            while len(chunk) > max_chars:
                # 需要进一步切分
                sub_chunks = self._llm_recursive_chunk(chunk, max_chars)
                if sub_chunks:
                    result.extend(sub_chunks)
                    break
                else:
                    # fallback 硬切分
                    result.append(chunk[:max_chars])
                    chunk = chunk[max_chars:]
            else:
                if chunk:
                    result.append(chunk)
        return result

    def _llm_recursive_chunk(self, text: str, max_chars: int) -> list[str]:
        """
        对超限文本进行递归切分。
        """
        prompt = build_semantic_chunk_recursive_prompt(text, len(text), max_chars)
        messages = [{"role": "user", "content": prompt}]

        for attempt in range(self.max_retries):
            try:
                response = self.llm_client.chat(
                    messages=messages,
                    temperature=0.3,
                    max_tokens=4000
                )

                result = self._parse_json_response(response)
                if result and "chunks" in result:
                    return [c.get("content", c) if isinstance(c, dict) else c for c in result["chunks"]]

            except Exception:
                continue

        return []

    def _parse_json_response(self, response: str) -> dict:
        """
        从 LLM 响应中解析 JSON。
        处理 </think> 思考标签和 markdown 代码块包装。
        支持两种格式：
        1. LLM 直接输出完整 JSON
        2. LLM 先输出截断的 JSON（用...表示），然后继续思考，最后输出完整 JSON
        """
        text = response.strip()

        # 去掉 </think> 思考标签（如果有）
        if "</think>" in text:
            # 如果有 </think>，优先找 </think> 之后的 JSON
            thought_end = text.find("</think>")
            after_thought = text[thought_end + 7:].strip()
            if after_thought.startswith("{"):
                text = after_thought
            else:
                # 去找 <filepath> 之后的 {
                next_brace = after_thought.find("{")
                if next_brace != -1:
                    text = after_thought[next_brace:]

        # 去掉可能的 markdown 代码块包装
        if text.startswith("```json"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]

        text = text.strip()

        # 尝试直接解析
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # 尝试在文本中查找 JSON 对象
        # 找最后一个 { 开始，确保匹配到完整的 JSON
        first_brace = text.find("{")
        last_brace = text.rfind("}")

        if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
            candidate = text[first_brace:last_brace + 1]
            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                pass

        raise ValueError(f"Failed to parse JSON from LLM response")

    def _fallback_chunk(self, text: str, max_chars: int) -> list[str]:
        """
        Fallback: 当 LLM 失败时使用的硬切分，尽量在段落或句子边界切分。
        """
        # 先按段落分割
        paragraphs = text.split("\n\n")
        chunks = []
        current_chunk = ""

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            if len(current_chunk) + len(para) + 2 <= max_chars:
                current_chunk += ("\n\n" if current_chunk else "") + para
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                # 如果单个段落本身就超限
                if len(para) > max_chars:
                    # 在句子边界切分
                    sentences = re.split(r'([。！？])', para)
                    for i in range(0, len(sentences) - 1, 2):
                        sent = sentences[i] + (sentences[i + 1] if i + 1 < len(sentences) else "")
                        if len(current_chunk) + len(sent) <= max_chars:
                            current_chunk += ("\n\n" if current_chunk else "") + sent
                        else:
                            if current_chunk:
                                chunks.append(current_chunk)
                            current_chunk = sent
                else:
                    current_chunk = para

        if current_chunk:
            chunks.append(current_chunk)

        return chunks if chunks else [text[:max_chars]]