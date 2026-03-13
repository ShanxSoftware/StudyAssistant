from pathlib import Path
from xaihandler import xAI_Handler
from xaihandler.personality import AgentPersonality, Archetype, AgentTrait, Trait
from study_assistant.config import XAI_API_KEY, XAI_API_MODEL, XAI_TIMEOUT, DB_PATH
from study_assistant.tools.common import get_doc_key, Chunk_Type, Chunked_Document, Document_Chunk, Document_Payload, Payload_Metadata
from study_assistant.tools.discovery import list_incoming_files, ListIncomingFilesParams
from study_assistant.tools.pdf_reader import read_pdf
from study_assistant.tools.word_reader import read_docx
from study_assistant.tools.list_incoming_pdfs import list_incoming_pdfs, list_incoming_docx
from pydantic import BaseModel, Field

def create_study_agent(name: str = "Bob") -> xAI_Handler:
    timeout = 3600
    try:
        timeout = int(XAI_TIMEOUT or 3600)
    except (ValueError, TypeError):
        pass  # logger.warning(...) later

    agent = xAI_Handler(
        api_key=XAI_API_KEY,
        model=XAI_API_MODEL,
        timeout=timeout,
        validate_connection=False,           # remove or make configurable later
        # budget=..., token limits, etc when ready
        max_client_tool_calls=50
    )

    agent.set_personality(
        AgentPersonality(
            name=name,
            gender="male",
            primary_archetype=Archetype.ANALYTICAL,
            primary_weight=0.7,
            secondary_archetype=Archetype.AMIABLE,
            secondary_weight=0.3,
            job_description=(
                "As a research and study assistant, your roles include maintaining the library "
                "of research articles, summarising, collating, and synthesising information, "
                "and finding new sources. Additionally, you help plan and proof assignments "
                "and provide exam preparation support."
                "CRITICAL RULE FOR EVERY DOCUMENT ANALYSIS:\n"
                "After you receive each chunk from the read_pdf tool, you MUST:\n"
                "1. Analyse the chunk for key facts, concepts, and relationships.\n"
                "2. Extract 3–6 precise triples in this exact format:\n"
                "   {\"subject\": \"short noun phrase\", \"predicate\": \"relationship verb\", \"object\": \"target\", \"confidence\": 0-100}\n"
                "3. Immediately call the store_global_context tool with a unique key (e.g. fact:doc_key:chunk_index:fact_number) and the JSON triple as value.\n"
                "4. Then continue to the next chunk.\n"
                "This builds a permanent, queryable knowledge graph for synthesis, assignment planning, and exam prep."
            ),
            traits=[
                AgentTrait(trait=Trait.PRECISION, intensity=70),
                AgentTrait(trait=Trait.CURIOSITY, intensity=30),
            ]
        )
    )

    agent.add_tool(name="list_incoming_files",
        description="List files in the incoming folder filtered by extension. If no parameter passed then tool defaults to .pdf and .docx",
        parameters=ListIncomingFilesParams,
        func=list_incoming_files)

    class read_text_parameters(BaseModel): 
        file_path: str = Field(..., description="Path to the File that is being read")
        chunk_index: int = Field(..., description="Index of the next chunk to retrieve")
        reset: bool = Field(..., description="If retrieving the earlier chunks again is a good idea set this to True to start from 0") # This might be depreciated soon

    agent.add_tool(name="read_pdf", 
        description="Converts a PDF into chunks, stores the entire chunked document into global_context, retrieves the next chunk for processing",
        parameters=read_text_parameters, 
        func=read_pdf) 
    
    agent.add_tool(name="read_docx", 
        description="Converts a Word Doucment into chunks, stores the entire chunked document into global_context, retrieves the next chunk for processing",
        parameters=read_text_parameters,
        func=read_docx) 
    
    return agent

    #TODO: Have a load from file function. 