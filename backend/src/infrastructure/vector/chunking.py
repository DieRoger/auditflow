"""Semantic Chunking — 文档切分为可检索的语义块

简单实现：按页 + 自然段落边界切分，保持语义完整性。
不引入 langchain 等重依赖。
"""

import uuid
from dataclasses import dataclass, field


@dataclass
class Chunk:
    """文档切分后的语义块"""
    chunk_id: str
    page_number: int
    chunk_index: int  # 页面内的序号
    text: str
    token_count: int
    metadata: dict = field(default_factory=dict)


def estimate_tokens(text: str) -> int:
    """粗略估算 token 数（英文：~4 chars/token，中文：~1.5 chars/token）"""
    # 简单估算：按空格分词 + 中文单独计数
    char_count = len(text)
    # 粗略：中文字符每个约 1.5 token，英文约 0.25 token/char
    chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
    english_chars = char_count - chinese_chars
    return int(chinese_chars / 1.5 + english_chars / 4)


def chunk_text(
    text: str,
    page_number: int,
    source_id: str,
    max_tokens: int = 500,
    overlap_tokens: int = 50,
) -> list[Chunk]:
    """将文本切分为语义块

    策略：
    1. 按 \n\n（段落）切分
    2. 合并短段落直到接近 max_tokens
    3. 相邻 chunk 之间有 overlap_tokens 的重叠
    """
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    if not paragraphs:
        return []

    chunks: list[Chunk] = []
    current_texts: list[str] = []
    current_tokens = 0
    chunk_index = 0

    for para in paragraphs:
        para_tokens = estimate_tokens(para)

        if current_tokens + para_tokens > max_tokens and current_texts:
            # 完成当前 chunk
            chunk_text_content = "\n\n".join(current_texts)
            chunks.append(Chunk(
                chunk_id=str(uuid.uuid4()),
                page_number=page_number,
                chunk_index=chunk_index,
                text=chunk_text_content,
                token_count=current_tokens,
                metadata={"source_id": source_id, "page": page_number},
            ))
            chunk_index += 1

            # 重叠：保留最后一段作为下一个 chunk 的开头
            if overlap_tokens > 0 and len(current_texts) >= 2:
                current_texts = current_texts[-1:]
                current_tokens = estimate_tokens(current_texts[0])
            else:
                current_texts = []
                current_tokens = 0

        current_texts.append(para)
        current_tokens += para_tokens

    # 最后一个 chunk
    if current_texts:
        chunk_text_content = "\n\n".join(current_texts)
        chunks.append(Chunk(
            chunk_id=str(uuid.uuid4()),
            page_number=page_number,
            chunk_index=chunk_index,
            text=chunk_text_content,
            token_count=current_tokens,
            metadata={"source_id": source_id, "page": page_number},
        ))

    return chunks


def chunk_document(
    page_texts: list[tuple[int, str]],  # [(page_number, text), ...]
    source_id: str,
    max_tokens: int = 500,
) -> list[Chunk]:
    """对整篇文档的所有页面进行切分"""
    all_chunks: list[Chunk] = []
    for page_num, text in page_texts:
        if text.strip():
            all_chunks.extend(chunk_text(text, page_num, source_id, max_tokens))
    return all_chunks
