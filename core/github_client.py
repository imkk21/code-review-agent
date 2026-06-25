import os
import json
import urllib.request
from datetime import datetime, timezone
from typing import Optional, Dict, Any

class GitHubClient:
    def __init__(self):
        self.app_id = os.environ.get("GITHUB_APP_ID")
        self.private_key = os.environ.get("GITHUB_PRIVATE_KEY")
        self.log_file = "github_comments.log"

    def post_inline_comment(self, repo: str, pr_number: int, commit_sha: str, file_path: str, start_line: int, end_line: int, body: str, suggestion: Optional[Dict[str, str]] = None) -> bool:
        """
        Posts a review comment to the specified lines in a pull request diff.
        Falls back to local file logging if App credentials are not configured.
        """
        # Format the comment body. Inject GitHub markdown suggestion if present
        comment_text = body
        if suggestion:
            comment_text += f"\n\n```suggestion\n{suggestion['replacement_code']}\n```"

        # Build payload for GitHub API: POST /repos/{owner}/{repo}/pulls/{pr_number}/comments
        payload: Dict[str, Any] = {
            "body": comment_text,
            "commit_id": commit_sha,
            "path": file_path,
            "line": end_line,
            "side": "RIGHT"
        }

        # If it's a multi-line comment, add start details
        if start_line < end_line:
            payload["start_line"] = start_line
            payload["start_side"] = "RIGHT"

        token = self._get_installation_token(repo)
        if not token:
            self._log_locally(repo, pr_number, payload)
            return False

        url = f"https://api.github.com/repos/{repo}/pulls/{pr_number}/comments"
        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode('utf-8'),
                headers={
                    'Accept': 'application/vnd.github.v3+json',
                    'Authorization': f'Bearer {token}',
                    'User-Agent': 'Antigravity-AI-Code-Review-Agent',
                    'Content-Type': 'application/json'
                },
                method='POST'
            )
            with urllib.request.urlopen(req) as response:
                return response.status == 201
        except Exception as e:
            print(f"Error posting comment to GitHub: {e}")
            self._log_locally(repo, pr_number, payload)
            return False

    def _get_installation_token(self, repo: str) -> Optional[str]:
        """
        Interacts with GitHub to fetch an installation access token.
        Returns None in mock mode if credentials are not configured.
        """
        if not self.app_id or not self.private_key:
            return None
            
        # Real GitHub App authentication requires generating a JWT signed with the private key
        # For this prototype's helper, we will return None to trigger local log fallbacks
        # unless GITHUB_TOKEN is directly provided for testing.
        return os.environ.get("GITHUB_TOKEN")

    def _log_locally(self, repo: str, pr_number: int, payload: dict):
        """
        Appends the mock GitHub review comment payload to a local log file for testing/development.
        """
        timestamp = datetime.now(timezone.utc).isoformat()
        log_entry = {
            "timestamp": timestamp,
            "repo": repo,
            "pr_number": pr_number,
            "payload": payload
        }
        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry) + "\n")
        except Exception as e:
            print(f"Failed to write mock GitHub comment log: {e}")
