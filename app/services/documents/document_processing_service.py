import io
import PyPDF2

def extract_text_from_bytes(content: bytes, mime_type: str) -> str:
    if mime_type == "application/pdf":
        text = ""
        try:
            reader = PyPDF2.PdfReader(io.BytesIO(content))
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        except Exception as e:
            text = f"[Error reading PDF: {e}]"
        return text
    elif mime_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        try:
            import docx
            doc = docx.Document(io.BytesIO(content))
            return "\n".join([p.text for p in doc.paragraphs])
        except Exception as e:
            return f"[Error reading DOCX: {e}]"
    elif mime_type == "text/plain":
        return content.decode("utf-8", errors="replace")
    else:
        return ""
