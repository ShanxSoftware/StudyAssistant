# src/study_assistant/tools/discovery.py

from pathlib import Path
from typing import Union, List, Optional
from pydantic import BaseModel, Field
from study_assistant.config import INCOMING_FOLDER

class ListIncomingFilesParams(BaseModel):
    extensions: Optional[Union[str, List[str]]] = Field(default=None, description="Single extension (e.g. '.pdf') or list of extensions (e.g. ['.pdf', '.docx', '.png']). Omit (None) to return all supported document types.")

def list_incoming_files(extensions: Union[str, List[str], None] = None) -> dict:
    """DOC COMMENT"""
    folder = Path(INCOMING_FOLDER)
    files = []

    # Normalise input to a list
    if extensions is None: 
        extensions = [".pdf", ".docx"] # default 
    elif isinstance(extensions, str): 
        extensions = [extensions]
    
    for ext in extensions: 
        ext = ext.lower() if ext.startswith('.') else f".{ext.lower()}"
        files.extend(list(folder.glob(f"*{ext}")))

    return {
        "files": [str(p) for p in files],
        "count": len(files),
        "filtered_by": extensions,
        "message": "Use aany of these full paths with read_pdf, read_docx, or future image tools."
    }