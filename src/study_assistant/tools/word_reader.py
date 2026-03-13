# src/study_assistant/tools/word_reader.py
from pathlib import Path
import hashlib
from enum import Enum
from docx import Document
from study_assistant.config import DB_PATH
from study_assistant.tools.common import smart_chunk_document
from xaihandler.memorystore import MemoryStore
from typing import Optional
from pydantic import BaseModel, Field

# Reuse your existing models (import them)
from study_assistant.tools.common import get_doc_key, Chunk_Type, Chunked_Document, Document_Chunk, Document_Payload, Payload_Metadata

def read_docx(
        file_path: str | Path, 
        chunk_index: int = 0, 
        reset: bool = False
) -> dict: 
    path = Path(file_path)
    doc_key = get_doc_key(path)
    store = MemoryStore(db_path=str(DB_PATH))

    if reset or chunk_index == 0: 
        if not path.is_file() or path.suffix.lower() != ".docx":
            error_payload = Document_Payload(status=f"Error: Not a valid Word Document: - {file_path}")
            return error_payload.model_dump()
        
        chunks = smart_chunk_document(file_path=path)
        doc = Document(path)

        payload_meta = Payload_Metadata(
            source_path=str(path), 
            doc_key=doc_key,
            total_chunks=len(chunks),
            total_tokens_est=sum(c.tokens_est for c in chunks), 
            title=doc.core_properties.title or path.stem,
            chunks=chunks
        )
        chunked_doc = Chunked_Document(doc_key=doc_key, metadata=payload_meta, chunks=chunks)
        store.upsert_global(key=doc_key, value=chunked_doc.model_dump_json(), tags=["document", "docx"])

    # Retrieval logic (identical to pdf_reader)
    try:
        row = store.retrieve_global_value(key=doc_key)
        if not row: 
            raise ValueError("Document not found in global_context") 
        chunked_doc = Chunked_Document.model_validate_json(row)
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