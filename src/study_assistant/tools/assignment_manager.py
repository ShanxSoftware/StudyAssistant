# src\study_assistant\tools\assignment_manager.py
import uuid
from pathlib import Path
from pydantic import BaseModel, Field
from typing import Literal, List, Dict, Optional
from datetime import datetime, timedelta
from study_assistant.config import DB_PATH
from study_assistant.tools.pdf_reader import read_pdf
from study_assistant.tools.word_reader import read_docx
from xaihandler.memorystore import MemoryStore

class Subtask(BaseModel):
    description: str
    status: Literal["pending", "done"]
    estimated_hours: float = Field(default=0.0, ge=0)

class Assignment(BaseModel):
    assignment_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    subject_path: str
    due_date: datetime
    status: Literal["todo", "in_progress", "review", "completed"] = "todo"
    priority: int = Field(default=1, ge=1, le=5)
    subtasks: List[Subtask] = Field(default_factory=list)
    linked_docs: List[str] = Field(default_factory=list)
    progress_log: List[Dict] = Field(default_factory=list)
    estimated_grade: Optional[float] = Field(default=None, ge=0, le=100)
    actual_grade: Optional[float] = Field(default=None, ge=0, le=100)
    research_start: Optional[datetime] = None
    writing_start: Optional[datetime] = None
    proofing_start: Optional[datetime] = None
    difficulty_proxy: float = Field(default=1.0, ge=0)  # will be set at creation

    @property
    def word_count_proxy(self) -> int:
        # simple heuristic; no new deps
        return sum(s.estimated_hours * 300 for s in self.subtasks) or 1000

    @classmethod
    def allocate_timelines(cls, assignments: List["Assignment"]) -> None:
        if not assignments:
            return
        # sort by due_date (earliest first) – matches user spec
        assignments.sort(key=lambda a: a.due_date)
        total_proxy = sum(a.difficulty_proxy for a in assignments) or 1
        now = datetime.now()
        for a in assignments:
            total_days = (a.due_date - now).days
            if total_days < 6:
                continue  # safety buffer
            research_d = total_days // 2
            remaining = total_days - research_d - 6
            a.research_start = now
            a.writing_start = a.research_start + timedelta(days=research_d)
            a.proofing_start = a.writing_start + timedelta(
                days=int(remaining * (a.difficulty_proxy / total_proxy))
            )
            now = a.proofing_start  # chain next assignment after previous proofing

class AssignmentCreateSchema(BaseModel):
    """Exact mirror of Assignment for structured validation"""
    title: str
    subject_path: str
    due_date: datetime  # ISO string auto-parsed by Pydantic
    priority: int = Field(default=1, ge=1, le=5)
    subtasks: List[Subtask] = Field(default_factory=list)
    linked_docs: List[str] = Field(default_factory=list)
    estimated_grade: Optional[float] = Field(default=None, ge=0, le=100)
    difficulty_proxy: float = Field(default=1.0, ge=0)

def build_rubric_prompt(rubric_text: str, course_outline: str = "") -> str:
    # zero-cost template; reuses same prompt style as job_description
    return f"""Parse this assignment rubric and course outline into a structured plan.
Course outline: {course_outline}
Rubric: {rubric_text}

Return ONLY valid JSON matching AssignmentCreateSchema.
Apply Conscientiousness: include realistic subtask hours and difficulty_proxy based on word count + complexity."""

def _extract_rubric_text(rubric_input: str) -> str:
    suffix = Path(rubric_input).suffix.lower() if isinstance(rubric_input, str) else ""
    if suffix == ".pdf":
        extracted = read_pdf(rubric_input)
        return extracted.get("text", "") or extracted.get("content", "")
    elif suffix == ".docx":
        extracted = read_docx(rubric_input)
        return extracted.get("text", "") or extracted.get("content", "")
    return str(rubric_input).strip()

# tool functions – drop-in for existing registry
def create_assignment_plan(rubric_input: str, course_outline: Optional[str] = None, extra_attachments: Optional[List[str]] = None) -> Dict:
    from study_assistant.agents import create_study_agent
    mgr = AssignmentManager(db_path=DB_PATH)  # reuse same db_path
    # budget guard already enforced by calling agent
    
    assistant = create_study_agent(name="Bob")
    rubric_text = _extract_rubric_text(rubric_input=rubric_input)
    parsed_dict = assistant.chat(
        message=build_rubric_prompt(
            rubric_text=rubric_text, 
            course_outline=course_outline or ""
            ),
        response_model=AssignmentCreateSchema
    )
    
    assignment = Assignment.model_validate(parsed_dict)
    assignment.difficulty_proxy = assignment.word_count_proxy
    assignment.linked_docs.extend(extra_attachments or [])

    open_assignments = mgr.list_open()
    Assignment.allocate_timelines([assignment] + open_assignments)
    mgr._save(assignment)
    return assignment.model_dump()  # JSON for agent parser

def update_milestone(assignment_id: str, task_name: str, words_written: int, actual_grade: Optional[float] = None) -> Dict:
    mgr = AssignmentManager(db_path=DB_PATH)
    assignment = mgr._load(assignment_id=assignment_id)

    assignment.progress_log.append({
        "timestamp": datetime.now().isoformat(),
        "task_name": task_name, # placeholder; in real call this would be passed from tool args
        "words_written": words_written
    })
    mgr._save(assignment)

    result = mgr.check_milestone(assignment_id, words_written, task_name)
    if actual_grade is not None:
        mgr.record_actual_grade(assignment_id, actual_grade)
    return result  # {"met": bool, "advice": list[str]}

class AssignmentManager:
    def __init__(self, db_path: str):  # reuse same db_path from core memory
        self.db = MemoryStore(str(DB_PATH))  # existing WAL helper

    def check_milestone(self, assignment_id: str, target_words: int, task_name: str) -> dict:
        """Deterministic, zero-AI comparison against the latest progress_log entry."""

        # Simple latest-first scan - reuses the same list iteration pattern as job_list filtering 
        assignment = self._load(assignment_id)
        met = False
        latest_words = 0
        for entry in reversed(assignment.progress_log): # most recent first
            if entry.get("task_name") == task_name: 
                latest_words = entry.get("words_written", 0)
                met = latest_words >= target_words
                break
        
        if met:
            advice = ["Milestone met - move to next subtask", "Great consistency!"]
        else: 
            advice = [
                "Keep going - you need more words on this task", 
                "Reference your linked_docs or Zotero entries for citations", 
                f"Current progress: {latest_words} / {target_words}  words"
            ]
        
        return {"met": met, "advice": advice}

    def record_actual_grade(self, assignment_id: str, grade: float) -> None:
        # WAL update + variance
        assignment = self._load(assignment_id)
        assignment.actual_grade = grade
        self._save(assignment)

    def list_open(self) -> List[Assignment]:
        """Reuses global_context scan – same pattern as job_list / global_context injection."""
        open_assignments = []
        # Use the library's existing global retrieval (adjust method name if your MemoryStore exposes list_global or search_by_tag)
        all_entries = self.db.get_all_global() if hasattr(self.db, "get_all_global") else []  # fallback to your actual method
        for entry in all_entries:
            if entry.get("key", "").startswith("assignment:"):
                ass = Assignment.model_validate_json(entry["value"])
                if ass.status != "completed":
                    open_assignments.append(ass)
        # Optional fast path using tags if your MemoryStore supports it:
        # results = self.db.search_global_context(tags=["type:assignment"])
        # then filter status
        return open_assignments
    
    def _save(self, assignment: Assignment):
        """WAL-safe global_context upsert – exact match to Zotero linking pattern."""
        key = f"assignment:{assignment.assignment_id}"
        value = assignment.model_dump_json()
        tags = [
            "type:assignment",                                   # quick type filter
            f"subject:{assignment.subject_path.replace('/', ':')}",  # path-safe
            f"due:{assignment.due_date.strftime('%Y-%m-%d')}",      # sortable date
            f"status:{assignment.status}",
            f"priority:{assignment.priority}"
        ]
        self.db.upsert_global(key, value, tags)

    def _load(self, assignment_id: str) -> Assignment:
        """Mirror existing global get pattern."""
        key = f"assignment:{assignment_id}"
        entry = self.db.get_global(key)  # or self.db.search_global_context(key=key) if method differs
        if not entry:
            raise KeyError(f"Assignment {assignment_id} not found")
        data = Assignment.model_validate_json(entry["value"])
        return Assignment.model_validate(data)