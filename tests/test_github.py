import os
import json
import hmac
import hashlib
import gc
from core.security import verify_signature
from core.github_client import GitHubClient

def test_signature_verification():
    payload = b'{"action": "opened", "pull_request": {"number": 1}}'
    secret = "my_secret_token"
    
    # Compute valid signature
    mac = hmac.new(secret.encode('utf-8'), msg=payload, digestmod=hashlib.sha256)
    valid_sig = f"sha256={mac.hexdigest()}"
    
    # Assert verification matches
    assert verify_signature(payload, valid_sig, secret) is True
    
    # Assert invalid signatures fail
    assert verify_signature(payload, "sha256=invalidhash", secret) is False
    assert verify_signature(payload, "sha1=invalidprefix", secret) is False
    assert verify_signature(payload, None, secret) is False
    assert verify_signature(payload, valid_sig, "") is False

def test_github_client_local_logging():
    log_file = "github_comments.log"
    if os.path.exists(log_file):
        try:
            os.remove(log_file)
        except Exception:
            pass
            
    client = GitHubClient()
    # Force credentials to None
    client.app_id = None
    client.private_key = None
    
    result = client.post_inline_comment(
        repo="owner/repo",
        pr_number=5,
        commit_sha="a1b2c3d4",
        file_path="src/main.py",
        start_line=10,
        end_line=12,
        body="Improve this function.",
        suggestion={"replacement_code": "def run():\n    pass"}
    )
    
    # Assert it logs locally and returns False
    assert result is False
    assert os.path.exists(log_file)
    
    # Read log
    with open(log_file, "r", encoding="utf-8") as f:
        line = f.readline()
        log_data = json.loads(line)
        
    assert log_data["repo"] == "owner/repo"
    assert log_data["pr_number"] == 5
    payload = log_data["payload"]
    assert payload["commit_id"] == "a1b2c3d4"
    assert payload["path"] == "src/main.py"
    assert payload["line"] == 12
    assert payload["start_line"] == 10
    assert "```suggestion" in payload["body"]
    
    # Clean up
    del client
    gc.collect()
    try:
        os.remove(log_file)
    except Exception:
        pass
