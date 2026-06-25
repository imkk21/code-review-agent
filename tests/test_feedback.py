import os
import json
import gc
from app import submit_feedback, save_review_run, FeedbackRequest
from core.models import ReviewResult, ReviewComment, IssueCategory, Severity
from core.rag_orchestrator import RAGOrchestrator
from core.reviewer import CodeReviewer

def test_feedback_ledger_persistence():
    ledger_file = "feedback_ledger.json"
    
    # Read existing feedback if any
    old_feedback = []
    if os.path.exists(ledger_file):
        try:
            with open(ledger_file, "r", encoding="utf-8") as f:
                old_feedback = json.load(f)
        except Exception:
            pass

    req = FeedbackRequest(
        file_path="mock_file.py",
        comment_title="Print Statement Debugging",
        code_snippet="print('debug info')",
        action_type="dismiss",
        explanation="Necessary print for console daemon."
    )
    
    # Submit feedback
    res = submit_feedback(req)
    assert res["status"] == "success"
    
    # Read ledger
    with open(ledger_file, "r", encoding="utf-8") as f:
        new_feedback = json.load(f)
        
    assert len(new_feedback) == len(old_feedback) + 1
    last_item = new_feedback[-1]
    assert last_item["comment_title"] == "Print Statement Debugging"
    assert last_item["action_type"] == "dismiss"
    
    # Cleanup ledger file (remove test entry)
    new_feedback.pop()
    with open(ledger_file, "w", encoding="utf-8") as f:
        json.dump(new_feedback, f, indent=2)

def test_feedback_context_retrieval_and_suppression():
    ledger_file = "feedback_ledger.json"
    temp_py_file = "temp_test_feedback.py"
    
    # 1. Setup temporary feedback ledger with a dismissed category
    test_feedback = [{
        "timestamp": "2026-06-24T12:00:00",
        "file_path": temp_py_file,
        "comment_title": "Print Statement Debugging",
        "code_snippet": "print(f'Starting process: {x}')",
        "action_type": "dismiss"
    }]
    with open(ledger_file, "w", encoding="utf-8") as f:
        json.dump(test_feedback, f, indent=2)

    # 2. Setup temporary file to review containing the print statement
    with open(temp_py_file, "w", encoding="utf-8") as f:
        f.write("\n\ndef run(x):\n    print(f'Starting process: {x}')\n")

    try:
        # 3. Retrieve relevant feedback context
        orchestrator = RAGOrchestrator(workspace_root=os.getcwd())
        dismissed_context = orchestrator.get_relevant_feedback(temp_py_file, added_lines=[4])
        
        assert len(dismissed_context) == 1
        assert dismissed_context[0]["comment_title"] == "Print Statement Debugging"
        
        # 4. Review the file and verify suppression works
        # The vulnerable code print statement would normally trigger STYLE-002 (Print Statement Debugging).
        # We assert that because of the dismissed feedback context, it is suppressed!
        from core.static_analysis import analyze_file
        static_findings = analyze_file("print(f'Starting process: {x}')", temp_py_file, [1])
        assert len(static_findings) == 1
        assert static_findings[0]["rule_name"] == "Print Statement Debugging"
        
        reviewer = CodeReviewer()
        review_result = reviewer.review_changes(
            temp_py_file, 
            "print(f'Starting process: {x}')", 
            [1], 
            static_findings, 
            rag_context=[], 
            dismissed_feedback=dismissed_context
        )
        
        # Output comments list should be empty because Print Statement Debugging was suppressed!
        assert len(review_result.comments) == 0
        # Allow natural language variations in summary (e.g. "dismissed by user", "suppressed", or "no action required")
        summary_lower = review_result.summary.lower()
        assert any(w in summary_lower for w in ["suppress", "dismiss", "no further action", "no recommendations"])
        
    finally:
        # Cleanup
        del orchestrator
        gc.collect()
        if os.path.exists(temp_py_file):
            os.remove(temp_py_file)
        if os.path.exists(ledger_file):
            os.remove(ledger_file)
            
        # Re-initialize empty ledger
        with open(ledger_file, "w", encoding="utf-8") as f:
            f.write("[]")
