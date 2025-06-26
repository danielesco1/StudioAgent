import fitz  # PyMuPDF: pip install pymupdf
from typing import List
import re
def load_pdf_text(path: str) -> str:
    """Read all pages from a PDF and return full plain text."""
    doc = fitz.open(path)
    text = []
    for page in doc:
        text.append(page.get_text())
    return "\n".join(text)

def split_by_bullets(text: str) -> List[str]:
    """
    Grab each bullet entry (• ….) up to its terminating period:
    - [\s\S]+?  — matches anything (including newlines) but non-greedy
    - \.        — up through the first period
    - (?=\s*•|\s*$) — stop right before the next bullet marker or end of text
    """
    pattern = r"•\s*([\s\S]+?\.)(?=\s*•|\s*$)"
    raw = re.findall(pattern, text)
    # collapse internal whitespace (line wraps → single spaces)
    return [re.sub(r"\s+", " ", entry).strip() for entry in raw]

def chunk_for_rag_bullets(text: str) -> List[str]:
    """
    RAG chunks = one city-bullet per chunk.
    """
    return split_by_bullets(text)