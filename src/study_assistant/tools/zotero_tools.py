#/src/study_assistant/tools/zotero_tools.py
from pyzotero import zotero
import requests
from pathlib import Path
import shutil
from typing import Dict, List
from xaihandler.memorystore import MemoryStore
from study_assistant.config import ZOTERO_LIBRARY_ID, ZOTERO_API_KEY, RESEARCH_LIBRARY, DB_PATH
from study_assistant.tools.common import get_doc_key, Chunked_Document

def ingest_verify_zotero_and_archive(file_path: str, subject_path: str = "general", move_file: bool = False) -> Dict:
    """Ingest → CrossRef verify → Zotero add → link in global_context → archive."""
    path = Path(file_path)
    doc_key = get_doc_key(path)
    store = MemoryStore(db_path=str(DB_PATH))
    
    # Step 1: Load stored document (DOI now reliably in metadata from read_pdf)
    try: 
        row = store.retrieve_global_value(key=doc_key)
        chunked_doc = Chunked_Document.model_validate_json(row)
        doi = chunked_doc.metadata.doi
    except Exception as e: 
        return {"status": f"Error loading document: {str(e)}"}

    # Step 2: CrossRef verify + Zotero create
    zot = zotero.Zotero(ZOTERO_LIBRARY_ID, 'user', ZOTERO_API_KEY)
    zotero_key = None
    if doi: # TODO: compare DOI extracted with DOI details and document details to avoid incorrect DOI attribution. 
        try: 
            r = requests.get(f"https://api.crossref.org/works/{doi}", timeout=5)
            if r.status_code == 200: 
                data = r.json()["message"]
                item = {
                    "title": data.get("title", [""])[0],
                    "DOI": doi, 
                    "authors": [f"{a.get('given', '')} {a.get('family', '')}".strip() for a in data.get("author", [])],
                    "date": data.get("issued", {}).get("date-parts", [[0]])[0][0]
                }
                zot.create_items([item])
                zotero_key = zot.items()[0]["key"] if zot.items() else None
        except Exception: 
            pass # graceful fallback

    # Step 3: Link in global_context
    if zotero_key: 
        store.upsert_global(
            key=f"link:zotero:{zotero_key}:doc_key", 
            value=doc_key,
            tags=["zotero_link", "crossref_verified"]
        )

    # Step 4: Archive
    target_dir = RESEARCH_LIBRARY / subject_path
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / path.name
    archived_url = f"file://{target_path}"

    if move_file:
        shutil.move(str(path), str(target_path))
    else:
        shutil.copy(str(path), str(target_path))

    return {
        "doi_extracted": doi,
        "zotero_key": zotero_key,
        "zotero_url": f"https://www.zotero.org/{ZOTERO_LIBRARY_ID}/items/{zotero_key}" if zotero_key else None,
        "archived_to": str(target_path), 
        "subject_path": subject_path,
        "archived_url": archived_url,
        "status": "complete"
    }