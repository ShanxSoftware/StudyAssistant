# src/study_assistant/tools/pdf_reader.py
from pathlib import Path
import hashlib
from enum import Enum
import fitz # PyMuPDF
from study_assistant.config import DATA_DIR, DB_PATH
from study_assistant.tools.common import get_doc_key, smart_chunk_document, Chunk_Type, Chunked_Document, Document_Chunk, Document_Payload, Payload_Metadata
from xaihandler.memorystore import MemoryStore
from typing import Dict, List, Optional
from pydantic import BaseModel, Field

def read_pdf(file_path: str | Path, chunk_index: int = 0, reset: bool = False) -> Dict: 
    path = Path(file_path)
    doc_key = get_doc_key(path)
    store = MemoryStore(db_path=str(DB_PATH))

    if reset or chunk_index == 0:
        # First call: extract + split into chunks, store persistently
        if not path.is_file() or path.suffix.lower() != ".pdf":
            doc_payload = Document_Payload(status=f"Error: Not a valid PDF: {file_path}")
            return doc_payload.model_dump()
        
        chunks = smart_chunk_document(path)
        payload_meta = Payload_Metadata(
            source_path=str(path),
            doc_key=doc_key, 
            total_chunks=len(chunks),
            total_tokens_est=sum(c.tokens_est for c in chunks),
            title=path.stem,
            chunks=chunks # stored for later retrieval 
        )
        chunked_doc = Chunked_Document(doc_key=doc_key, metadata=payload_meta, chunks=chunks)
        store.upsert_global(key=doc_key, value=chunked_doc.model_dump_json(), tags=[f"title: {path.stem}", f"path: {str(path)}"])
    # Return ONLY the requested chunk + progress
    try: 
        chunked_doc = Chunked_Document.model_validate_json(store.retrieve_global_value(key=doc_key) if store.retrieve_global_value(key=doc_key) else "")
    except Exception as e: 
        doc_payload = Document_Payload(status=f"Error: stored document corrupted. {str(e)}")
        return doc_payload.model_dump()
    
    if chunk_index >= chunked_doc.metadata.total_chunks:
        complete_payload = Document_Payload(doc_key=doc_key, progress="100%", status="complete")
        return complete_payload.model_dump()

    chunk = chunked_doc.chunks[chunk_index]
    doc_payload = Document_Payload(
        doc_key=doc_key,
        chunk_index=chunk_index, 
        total_chunks=chunked_doc.metadata.total_chunks,
        progress=f"{chunk_index + 1}/{chunked_doc.metadata.total_chunks}",
        chunk=chunk, 
        tokens_est=chunk.tokens_est,
        status="next_chunk"
    )
    return doc_payload.model_dump()