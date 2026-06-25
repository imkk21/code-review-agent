from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field

class IssueCategory(str, Enum):
    BUG = "bug"
    SECURITY = "security"
    PERFORMANCE = "performance"
    STYLE = "style"

class Severity(str, Enum):
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"

class CodeSuggestion(BaseModel):
    original_code: str = Field(description="The exact lines of code that need changes.")
    replacement_code: str = Field(description="The suggested replacement code. Write full, valid code snippets.")
    explanation: str = Field(description="Detailed explanation of why this replacement is better.")

class ReviewComment(BaseModel):
    file_path: str = Field(description="Path to the file being reviewed.")
    start_line: int = Field(description="Start line number of the issue (1-indexed).")
    end_line: int = Field(description="End line number of the issue (1-indexed).")
    category: IssueCategory = Field(description="Category of the issue.")
    severity: Severity = Field(description="Severity classification.")
    title: str = Field(description="A short, descriptive title for the issue.")
    explanation: str = Field(description="Explanation of the issue, potential risks, and design reasoning.")
    suggestion: Optional[CodeSuggestion] = Field(default=None, description="Optional drop-in code fix.")

class ReviewResult(BaseModel):
    comments: List[ReviewComment] = Field(default_factory=list, description="List of review comments.")
    summary: str = Field(description="Overall high-level summary of the code changes, quality, and recommendations.")

class CodeChunk(BaseModel):
    file_path: str = Field(description="Source file path.")
    content: str = Field(description="Content of the code chunk.")
    start_line: int = Field(description="Start line number in the source file.")
    end_line: int = Field(description="End line number in the source file.")
    chunk_type: str = Field(description="Type of chunk (e.g., function, class, module).")

class SearchResult(BaseModel):
    chunk: CodeChunk = Field(description="The retrieved code chunk.")
    similarity: float = Field(description="Cosine similarity score.")
