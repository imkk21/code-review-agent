import os
import json
import gc
from core.slack_client import SlackNotifier
from core.models import ReviewResult, ReviewComment, IssueCategory, Severity
from app import save_review_run

def test_slack_local_logging():
    log_file = "slack_notifications.log"
    # Ensure log file doesn't exist or we delete it first
    if os.path.exists(log_file):
        try:
            os.remove(log_file)
        except Exception:
            pass

    notifier = SlackNotifier()
    # Force webhook_url to be None for testing local fallback logging
    notifier.webhook_url = None
    
    result = notifier.send_critical_alert(
        file_path="mock_vulnerable.py",
        title="SQL Injection",
        category="security",
        severity="critical",
        explanation="Detected SQL Injection risk in db query."
    )
    
    # Assert it returns False because webhook is None
    assert result is False
    # Assert log file is created
    assert os.path.exists(log_file)
    
    # Read log
    with open(log_file, "r", encoding="utf-8") as f:
        line = f.readline()
        log_data = json.loads(line)
        
    assert "timestamp" in log_data
    blocks = log_data["payload"]["blocks"]
    assert blocks[0]["text"]["text"] == "🚨 High-Severity Review Alert"
    assert "mock_vulnerable.py" in blocks[1]["text"]["text"]
    
    # Cleanup log file
    del notifier
    gc.collect()
    try:
        os.remove(log_file)
    except Exception:
        pass

def test_history_ledger_save():
    history_file = "review_history.json"
    
    # Read existing history if any
    old_history = []
    if os.path.exists(history_file):
        try:
            with open(history_file, "r", encoding="utf-8") as f:
                old_history = json.load(f)
        except Exception:
            pass

    # Create a mock ReviewResult
    comment = ReviewComment(
        file_path="examples/vulnerable_code.py",
        start_line=5,
        end_line=5,
        category=IssueCategory.SECURITY,
        severity=Severity.CRITICAL,
        title="Hardcoded API Key",
        explanation="Testing history logs."
    )
    mock_result = ReviewResult(
        comments=[comment],
        summary="Test Run Summary"
    )
    
    # Run save
    save_review_run("examples/vulnerable_code.py", mock_result)
    
    # Verify it was written
    assert os.path.exists(history_file)
    with open(history_file, "r", encoding="utf-8") as f:
        new_history = json.load(f)
        
    assert len(new_history) == len(old_history) + 1
    last_entry = new_history[-1]
    assert last_entry["file_path"] == "examples/vulnerable_code.py"
    assert last_entry["issues_count"] == 1
    assert last_entry["categories"]["security"] == 1
    
    # Revert file to original state if needed, or leave it since it's the history database
    # In real tests, we keep it, but let's delete the newly added test entry to keep database clean
    new_history.pop()
    with open(history_file, "w", encoding="utf-8") as f:
        json.dump(new_history, f, indent=2)
