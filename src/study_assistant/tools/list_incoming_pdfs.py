# ./src/study_assistant/tools/list_incoming_pdf.py
from pathlib import Path
from study_assistant.config import INCOMING_FOLDER

def list_incoming_pdfs() -> dict:
    """Returns list of PDFs in the watched folder so the agent can choose one."""
    files = [str(p) for p in Path(INCOMING_FOLDER).glob("*.pdf")]
    return {
        "available_pdfs": files, 
        "count": len(files),
        "message": "Use one of these paths with read_pdf tool"
    }

def list_incoming_docx() -> dict:
    """Returns list of DOCXs in the watched folder so the agent can choose one."""
    files = [str(p) for p in Path(INCOMING_FOLDER).glob("*.docx")]
    return {
        "available_docx": files, 
        "count": len(files),
        "message": "Use one of these paths with read_pdf tool"
    }