import os
import json
from datetime import datetime
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, HTTPException, Request, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from core.diff_parser import parse_diff
from core.static_analysis import analyze_file
from core.reviewer import CodeReviewer
from core.models import ReviewResult
from core.rag_orchestrator import RAGOrchestrator
from core.slack_client import SlackNotifier
from core.security import verify_signature
from core.github_client import GitHubClient
from core.config import load_env

# Load environment variables from .env file
load_env()

app = FastAPI(
    title="Apex AI",
    description="FastAPI endpoints representing Apex AI analysis, webhook ingestion, dashboard, and feedback loops.",
    version="1.0.0"
)

# Enable CORS for DevSync frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize reviewer
reviewer = CodeReviewer()
history_file = "review_history.json"
feedback_file = "feedback_ledger.json"

class ReviewRequest(BaseModel):
    file_path: str
    model_name: Optional[str] = "gemini-3.1-flash-lite"

class CodeReviewRequest(BaseModel):
    code: str
    file_path: str
    model_name: Optional[str] = "gemini-3.1-flash-lite"

class FeedbackRequest(BaseModel):
    file_path: str
    comment_title: str
    code_snippet: str
    action_type: str  # "accept" or "dismiss"
    explanation: Optional[str] = None

def save_review_run(file_path: str, result: ReviewResult):
    """
    Appends review results to the local review_history.json ledger and dispatches Slack alerts for critical findings.
    """
    cat_counts = {"bug": 0, "security": 0, "performance": 0, "style": 0}
    for c in result.comments:
        cat = c.category.value if hasattr(c.category, 'value') else str(c.category)
        if cat in cat_counts:
            cat_counts[cat] += 1
            
    comments_list = []
    for c in result.comments:
        c_dict = json.loads(c.model_dump_json())
        comments_list.append(c_dict)

    entry = {
        "timestamp": datetime.now().isoformat(),
        "file_path": file_path,
        "issues_count": len(result.comments),
        "categories": cat_counts,
        "comments": comments_list,
        "summary": result.summary
    }

    history = []
    if os.path.exists(history_file):
        try:
            with open(history_file, "r", encoding="utf-8") as f:
                history = json.load(f)
        except Exception:
            history = []
            
    history.append(entry)
    
    try:
        with open(history_file, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2)
    except Exception as e:
        print(f"Failed to save review history: {e}")

    # Dispatch Slack alerts for critical findings
    notifier = SlackNotifier()
    for c in result.comments:
        sev = c.severity.value if hasattr(c.severity, 'value') else str(c.severity)
        if sev.lower() == "critical":
            fix_str = c.suggestion.replacement_code if c.suggestion else None
            cat = c.category.value if hasattr(c.category, 'value') else str(c.category)
            notifier.send_critical_alert(
                file_path=c.file_path,
                title=c.title,
                category=cat,
                severity=sev,
                explanation=c.explanation,
                suggestion=fix_str
            )

@app.get("/")
def read_root():
    return {
        "status": "healthy",
        "agent": "Apex AI",
        "gemini_api_configured": bool(os.environ.get("GEMINI_API_KEY")),
        "slack_api_configured": bool(os.environ.get("SLACK_WEBHOOK_URL")),
        "github_webhook_secret_configured": bool(os.environ.get("GITHUB_WEBHOOK_SECRET")),
        "message": "Send POST requests to /review-file or /webhook to test code reviews. Access the dashboard at /dashboard"
    }

@app.get("/dashboard", response_class=HTMLResponse)
def get_dashboard():
    """
    Serves the beautiful dark-themed SPA dashboard page.
    """
    template_path = os.path.join("templates", "dashboard.html")
    if not os.path.exists(template_path):
        raise HTTPException(status_code=404, detail="Dashboard template not found.")
        
    with open(template_path, "r", encoding="utf-8") as f:
        html_content = f.read()
    return HTMLResponse(content=html_content, status_code=200)

@app.get("/api/list-examples")
def list_workspace_files():
    """
    Lists reviewable python files in the workspace, excluding virtual envs and caches.
    """
    python_files = []
    exclude_dirs = {".git", "venv", ".venv", "__pycache__", ".pytest_cache", ".agents", ".gemini", "scratch"}
    
    for root, dirs, files in os.walk("."):
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        for file in files:
            if file.endswith(".py"):
                rel_path = os.path.relpath(os.path.join(root, file), ".")
                rel_path = rel_path.replace("\\", "/")
                python_files.append(rel_path)
                
    return {"files": sorted(python_files)}

@app.get("/api/file-content")
def get_file_content(file_path: str):
    """
    Returns the raw content of a workspace file for inline display.
    """
    normalized_path = os.path.normpath(file_path)
    if normalized_path.startswith("..") or os.path.isabs(normalized_path):
        abs_path = os.path.abspath(normalized_path)
        cwd = os.path.abspath(os.getcwd())
        if not abs_path.startswith(cwd):
            raise HTTPException(status_code=403, detail="Access denied to files outside the workspace.")
            
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail=f"File '{file_path}' not found.")
        
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return {"content": f.read()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/history")
def get_history():
    """
    Returns the compiled list of historical review runs.
    """
    if not os.path.exists(history_file):
        return []
    try:
        with open(history_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read history database: {e}")

@app.get("/api/feedback")
def get_feedback():
    """
    Returns the compiled list of historical user feedback signals.
    """
    if not os.path.exists(feedback_file):
        return []
    try:
        with open(feedback_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read feedback database: {e}")

@app.post("/api/feedback")
def submit_feedback(payload: FeedbackRequest):
    """
    Saves user feedback accept/dismiss inputs to help suppresses false positives in future runs.
    """
    history = []
    if os.path.exists(feedback_file):
        try:
            with open(feedback_file, "r", encoding="utf-8") as f:
                history = json.load(f)
        except Exception:
            history = []

    # Check for duplicate feedback to update it, or append new
    duplicate_found = False
    for item in history:
        if (item.get("file_path") == payload.file_path and 
            item.get("comment_title") == payload.comment_title and
            item.get("code_snippet") == payload.code_snippet):
            item["action_type"] = payload.action_type
            item["timestamp"] = datetime.now().isoformat()
            item["explanation"] = payload.explanation
            duplicate_found = True
            break

    if not duplicate_found:
        history.append({
            "timestamp": datetime.now().isoformat(),
            "file_path": payload.file_path,
            "comment_title": payload.comment_title,
            "code_snippet": payload.code_snippet,
            "action_type": payload.action_type,
            "explanation": payload.explanation
        })

    try:
        with open(feedback_file, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2)
        return {"status": "success", "message": f"Recorded feedback '{payload.action_type}' for '{payload.comment_title}'"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save developer feedback: {e}")

@app.post("/api/review-code", response_model=ReviewResult)
def review_code_snippet(payload: CodeReviewRequest):
    """
    Reviews a raw code snippet directly without reading from disk.
    """
    try:
        lines_count = len(payload.code.splitlines())
        added_lines = list(range(1, lines_count + 1))
        
        static_findings = analyze_file(payload.code, payload.file_path, added_lines)
        
        try:
            orchestrator = RAGOrchestrator(workspace_root=os.getcwd())
            rag_context = orchestrator.get_context_for_changes(payload.file_path, added_lines)
            dismissed_feedback = orchestrator.get_relevant_feedback(payload.file_path, added_lines)
        except Exception:
            rag_context = []
            dismissed_feedback = []
            
        file_reviewer = CodeReviewer(model_name=payload.model_name)
        result = file_reviewer.review_changes(
            payload.file_path, payload.code, added_lines, static_findings,
            rag_context=rag_context, dismissed_feedback=dismissed_feedback
        )
        
        save_review_run(payload.file_path, result)
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/review-file", response_model=ReviewResult)
def review_single_file(payload: ReviewRequest):
    """
    Reviews a local file by simulating that all lines are added/modified.
    """
    if not os.path.exists(payload.file_path):
        raise HTTPException(status_code=404, detail=f"File '{payload.file_path}' not found.")
        
    try:
        with open(payload.file_path, "r", encoding="utf-8") as f:
            content = f.read()
            
        lines_count = len(content.splitlines())
        added_lines = list(range(1, lines_count + 1))
        
        # Analyze using local static rules
        static_findings = analyze_file(content, payload.file_path, added_lines)
        
        # Query RAG codebase context & feedback context
        orchestrator = RAGOrchestrator(workspace_root=os.getcwd())
        rag_context = orchestrator.get_context_for_changes(payload.file_path, added_lines)
        dismissed_feedback = orchestrator.get_relevant_feedback(payload.file_path, added_lines)
        
        # Query LLM (falls back to mock if API key is not configured)
        file_reviewer = CodeReviewer(model_name=payload.model_name)
        result = file_reviewer.review_changes(
            payload.file_path, content, added_lines, static_findings, rag_context=rag_context, dismissed_feedback=dismissed_feedback
        )
        
        # Log to ledger and dispatch Slack alert
        save_review_run(payload.file_path, result)
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/webhook", response_model=ReviewResult)
async def handle_webhook(request: Request, x_hub_signature_256: Optional[str] = Header(None)):
    """
    Handles a GitHub pull request webhook trigger.
    Verifies payload signature and post comments directly back to the pull request.
    """
    body_bytes = await request.body()
    webhook_secret = os.environ.get("GITHUB_WEBHOOK_SECRET")
    
    if webhook_secret:
        if not x_hub_signature_256 or not verify_signature(body_bytes, x_hub_signature_256, webhook_secret):
            raise HTTPException(status_code=401, detail="Invalid webhook signature.")
            
    try:
        payload_dict = json.loads(body_bytes)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload.")

    repo = payload_dict.get("repository", {})
    if isinstance(repo, dict):
        repo_name = repo.get("full_name")
    else:
        repo_name = repo
        
    pr = payload_dict.get("pull_request", {})
    if isinstance(pr, dict):
        pr_number = pr.get("number")
        head_sha = pr.get("head", {}).get("sha", "mock-sha")
        diff_text = payload_dict.get("diff_content", "")
    else:
        pr_number = payload_dict.get("pull_request_id")
        head_sha = "mock-sha"
        diff_text = payload_dict.get("diff_content", "")

    if not diff_text or not diff_text.strip():
        diff_text = payload_dict.get("diff_content", "")
        
    if not diff_text or not diff_text.strip():
        raise HTTPException(status_code=400, detail="Diff content is missing or empty.")

    try:
        file_changes = parse_diff(diff_text)
        all_comments = []
        summaries = []
        
        file_reviewer = CodeReviewer()
        orchestrator = RAGOrchestrator(workspace_root=os.getcwd())
        github_client = GitHubClient()
        
        for fc in file_changes:
            file_path = fc["file_path"]
            if not file_path or fc["is_deleted"]:
                continue
                
            content = ""
            if os.path.exists(file_path):
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
            
            static_findings = analyze_file(content, file_path, fc["added_lines"]) if content else []
            rag_context = orchestrator.get_context_for_changes(file_path, fc["added_lines"]) if content else []
            dismissed_feedback = orchestrator.get_relevant_feedback(file_path, fc["added_lines"]) if content else []
            
            review_result = file_reviewer.review_changes(
                file_path, content, fc["added_lines"], static_findings, rag_context=rag_context, dismissed_feedback=dismissed_feedback
            )
            
            # Post inline comments back to GitHub App REST client
            for comment in review_result.comments:
                fix_dict = None
                if comment.suggestion:
                    fix_dict = {
                        "original_code": comment.suggestion.original_code,
                        "replacement_code": comment.suggestion.replacement_code
                    }
                github_client.post_inline_comment(
                    repo=repo_name,
                    pr_number=pr_number,
                    commit_sha=head_sha,
                    file_path=comment.file_path,
                    start_line=comment.start_line,
                    end_line=comment.end_line,
                    body=comment.explanation,
                    suggestion=fix_dict
                )
                
            all_comments.extend(review_result.comments)
            summaries.append(review_result.summary)
            
        combined_summary = (
            f"### Webhook Review Report for PR #{pr_number} in {repo_name}\n\n" +
            "\n\n".join(summaries)
        )
        
        final_result = ReviewResult(comments=all_comments, summary=combined_summary)
        save_review_run(f"PR #{pr_number} ({repo_name})", final_result)
        
        return final_result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="127.0.0.1", port=8081, reload=True)
