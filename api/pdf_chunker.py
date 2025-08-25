# api/pdf_chunker.py
from pypdf import PdfReader
from langchain.schema import Document

def iter_pdf_chunks(pdf_path, chunk_chars=1200, overlap=200):
    reader = PdfReader(pdf_path)
    for page_num, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        i = 0
        while i < len(text):
            chunk = text[i:i+chunk_chars]
            yield Document(
                page_content=chunk,
                metadata={"source": pdf_path, "page": page_num}
            )
            i += max(chunk_chars - overlap, 1)

