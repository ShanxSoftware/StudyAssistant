from pathlib import Path
from xaihandler import xAI_Handler
from xaihandler.personality import AgentPersonality, Archetype, AgentTrait, Trait
from study_assistant.config import XAI_API_KEY, XAI_API_MODEL, XAI_TIMEOUT, DB_PATH
from study_assistant.tools.common import get_doc_key, Chunk_Type, Chunked_Document, Document_Chunk, Document_Payload, Payload_Metadata
from study_assistant.tools.discovery import list_incoming_files, ListIncomingFilesParams
from study_assistant.tools.pdf_reader import read_pdf
from study_assistant.tools.word_reader import read_docx
from study_assistant.tools.web_search_augment import search_augment, web_search_augment, SearchEngine, SearchResult, WebSearchAugmentResponse
from study_assistant.tools.zotero_tools import ingest_verify_zotero_and_archive
from study_assistant.tools.assignment_manager import create_assignment_plan, update_milestone
from pydantic import BaseModel, Field
from typing import Dict, List, Optional

_MAIN_BOB = None

def create_study_agent(name: str = "Bob") -> xAI_Handler:
    global _MAIN_BOB
    if _MAIN_BOB is not None: 
        return _MAIN_BOB
    
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
        max_client_tool_calls=50, 
        db_path=DB_PATH
    )

    agent.set_budget(9000000000000)

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
                "and provide exam preparation support.\n\n"
                "CRITICAL RULES:\n"
                "1. When the user asks to analyse or ingest documents, FIRST call list_incoming_files to discover ALL files in incoming.\n"
                "2. Process EVERY file automatically (PDF or DOCX) using read_pdf or read_docx.\n"
                "3. After ALL chunks are processed, decide the full hierarchical subject path (e.g. psychology/theories/transactional_model_of_stress_and_coping) "
                "   and call ingest_verify_zotero_and_archive with the correct file_path, subject_path, and move_file=True for autonomous mode. After a file is archived use the archived_url when discussing it.\n"
                "4. Always return the zotero_key and archived_path visibly in your final response so the user can verify.\n\n"
                "5. Research Workflow (web_search and knowledge graph enrichment):\n"
                "   - Round 1: ALWAYS start with parallel search_global_context calls for existing triples and relationships.\n"
                "   - If more sources are needed, call web_search with a precise academic query in the same round.\n"
                "   - Prioritise academic value (journal > website, recency, seminal works, study type, authority).\n"
                "   - In your final response, for EVERY result you mention or cite:\n"
                "     • Include the exact title\n"
                "     • Include the full URL as a clickable markdown link [Title](URL) or plain URL\n"
                "     • Quote the most relevant snippet (≤ 2 sentences)\n"
                "     • State the source/engine\n"
                "   - Example output format:\n"
                "     [xAI Web Search] Title: \"Quantum Entanglement Explained\"\n"
                "     https://arxiv.org/abs/1234.5678\n"
                "     Snippet: \"...\"\n"
                "   - If the user needs to cite, remind them to verify the live link before using it in an assignment.\n"
                "   - Results are automatically saved to the knowledge graph by the wrapper (URL as key + basic summary/tags).\n"
                "     Use store_web_research_link (or equivalent) only when you want to add rich conceptual relationships.\n\n"
                "6. Knowledge-Graph Triple Extraction. Do this for EVERY ingested document, "
                "but also consider creating triples for high-value results from web_search "
                "and for information obtained in user prompts.\n"
                "   - After you receive each chunk from read_pdf or read_docx, you MUST:\n"
                "     1. Analyse the chunk for key facts, concepts, and relationships.\n"
                "     2. Extract 3–6 precise triples in this exact format:\n"
                "        {\"subject\": \"short noun phrase\", \"predicate\": \"relationship verb\", \"object\": \"target\", \"confidence\": 0-100}\n"
                "     3. Immediately call store_global_context (or store_web_research_link for web results) with a unique key (e.g. fact:doc_key:chunk_index:fact_number) and the JSON triple(s) as value.\n"
                "     4. Then continue to the next chunk.\n"
                "   - This builds a permanent, queryable knowledge graph for synthesis, assignment planning, and exam prep."
                "   - When a web_search topic overlaps with previously ingested documents (visible in global_context), explicitly bridge the new sources to existing triples and findings (e.g. 'This 2015 oxytocin study complements the Dog Owner Relationship Scale results in the security-officer dissertation')."
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
        description="Converts a PDF into chunks, stores the entire chunked document into global_context, retrieves the next chunk for processing. When all chunks are processed and tripples created, call ingest_verify_zotero_and_archive to add to zotero and archive the document.",
        parameters=read_text_parameters, 
        func=read_pdf) 
    
    agent.add_tool(name="read_docx", 
        description="Converts a Word Doucment into chunks, stores the entire chunked document into global_context, retrieves the next chunk for processing. When all chunks are processed and tripples created, call ingest_verify_zotero_and_archive to add to zotero and archive the document.",
        parameters=read_text_parameters,
        func=read_docx) 
    class IngestZoteroParams(BaseModel):
        file_path: str = Field(..., description="Full path to the document - before move/copy")
        subject_path: str = Field(..., description="Full hierarchical path decided by Agent (e.g. psychology/scales/relationships)")
        move_file: bool = Field(False, description="True = move from incoming, False = copy")

    agent.add_tool(
        name="ingest_verify_zotero_and_archive",
        description="Full ingest pipeline. Agent decides the multi-level subject_path.",
        parameters=IngestZoteroParams,
        func=ingest_verify_zotero_and_archive
    )

    class CreateAssignmentPlanParams(BaseModel):
        rubric_input: str = Field(..., description="String containing the rubric information, for the assignment")
        course_outline: Optional[str] = Field(default=None, description="Overarching course outline")
        extra_attachments: Optional[List[str]] = Field(default=None, description="List of Paths to related documents")

    agent.add_tool(
        name="create_assignment_plan",
        description="Determine a plan to complete the assignment to a high standard within the available timeframe",
        parameters=CreateAssignmentPlanParams,
        func=create_assignment_plan
    )

    class UpdateMilestoneParams(BaseModel):
        assignment_id: str = Field(..., description="ID of the assignment being updated")
        task_name: str = Field(..., description="Specific subtask or section (e.g. 'Task 1 trauma counselling')")
        words_written: int = Field(..., description="Number of words written on this specific task today")
        actual_grade: Optional[float] = Field(default=None, description="After the assignment has been graded submit the actual result")

    agent.add_tool(
        name="update_milestone",
        description="Updates the current progress on a specific task or the actual received grade",
        parameters=UpdateMilestoneParams,
        func=update_milestone
    )
    
    _MAIN_BOB = agent
    return agent

    #TODO: Have a load from file function. 