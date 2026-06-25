import os
import json
from typing import List, Dict, Any, Optional
from core.models import ReviewResult, ReviewComment, IssueCategory, Severity, CodeSuggestion

# We will try to import the genai client from the new google-genai SDK
try:
    from google import genai
    from google.genai import types
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False

class CodeReviewer:
    def __init__(self, model_name: str = "gemini-3.1-flash-lite"):
        self.model_name = model_name
        self.api_key = os.environ.get("GEMINI_API_KEY")
        self.client = None
        
        if GENAI_AVAILABLE and self.api_key:
            try:
                self.client = genai.Client(api_key=self.api_key)
            except Exception as e:
                print(f"Warning: Failed to initialize Gemini Client: {e}")

    def review_changes(self, file_path: str, file_content: str, added_lines: List[int], static_findings: List[Dict[str, Any]], rag_context: List[SearchResult] = None, dismissed_feedback: List[dict] = None) -> ReviewResult:
        """
        Orchestrates the code review for a file using LLM + Static Analysis hints + RAG Context + Dismissed Feedback.
        """
        if not added_lines:
            return ReviewResult(
                comments=[],
                summary=f"No lines were added or modified in `{file_path}`."
            )

        # Format inputs for the prompt (group static findings to prevent model distraction/token bloat)
        findings_str = ""
        if static_findings:
            findings_str = "\nStatic Analysis Warnings detected on the changed lines:\n"
            grouped_findings = {}
            for f in static_findings:
                key = (f["rule_name"], f["message"], f["severity"])
                if key not in grouped_findings:
                    grouped_findings[key] = []
                grouped_findings[key].append(f["line"])
            
            for (rule_name, message, severity), lines in grouped_findings.items():
                lines.sort()
                if len(lines) == 1:
                    lines_str = f"Line {lines[0]}"
                else:
                    lines_str = f"Lines {', '.join(map(str, lines))}"
                findings_str += f"- {lines_str}: [{rule_name}] {message} (Severity: {severity})\n"

        # Format RAG context
        rag_str = ""
        if rag_context:
            rag_str = "\n=== Relevant Codebase Context (RAG) ===\n"
            for r in rag_context:
                rag_str += f"File: {r.chunk.file_path} (Lines {r.chunk.start_line}-{r.chunk.end_line}, Similarity Score: {r.similarity:.2f})\n"
                rag_str += f"Chunk Type: {r.chunk.chunk_type}\n"
                rag_str += f"Content:\n{r.chunk.content}\n"
                rag_str += "-" * 40 + "\n"

        # Format Dismissed Feedback context
        feedback_str = ""
        if dismissed_feedback:
            feedback_str = "\n=== Historical User Feedback (Dismissed False Positives) ===\n"
            feedback_str += "The developer previously dismissed the following review recommendations. DO NOT report issues matching these patterns:\n"
            for item in dismissed_feedback:
                feedback_str += f"- Dismissed Issue: {item.get('comment_title')}\n"
                feedback_str += f"  Code pattern: `{item.get('code_snippet')}`\n"
                feedback_str += f"  Reason for dismissal: {item.get('explanation', 'No explanation provided.')}\n"
                feedback_str += "-" * 40 + "\n"

        system_instruction = (
            "You are an elite senior software engineer and security auditor conducting an exhaustive code review and security audit.\n"
            "Analyze the changes in the provided file in extreme detail. Do not ignore any bugs, issues, or risks.\n"
            "You must identify and report EVERY SINGLE code defect, security vulnerability, performance bottleneck, logic flaw, "
            "syntax error, naming mismatch, resource leak, division by zero, index/off-by-one error, infinite loop, key/attribute error, "
            "weak cryptography, and bad design pattern present in the modified lines. Be extremely thorough.\n"
            "CRITICAL: To avoid exceeding output token limits, you MUST group all repetitive minor issues (such as multiple leftover debug print "
            "statements, minor style issues, or similar patterns) into a single consolidated review comment that lists the line numbers. "
            "This leaves output budget to report critical vulnerabilities and logic errors as separate, detailed comments.\n"
            "For each issue, provide a clear, helpful explanation and a complete drop-in replacement code fix where possible.\n"
            "You must restrict your review comments ONLY to the lines that were added or modified in the current diff.\n"
            "Read 'Historical User Feedback' to avoid raising suggestions the user previously dismissed as false positives."
        )

        prompt = f"""
Review the following code file changes.

File Path: {file_path}
Modified/Added Line Numbers: {added_lines}
{findings_str}
{rag_str}
{feedback_str}

=== Full File Content ===
{file_content}
========================

Please review only the modified line numbers {added_lines}. Respond with a JSON object conforming to the ReviewResult schema.
"""

        # Fallback to mock if API key or library is not available
        if not self.client:
            return self._generate_mock_review(file_path, file_content, added_lines, static_findings, rag_context, dismissed_feedback)

        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=ReviewResult,
                    system_instruction=system_instruction,
                    temperature=0.2,
                )
            )
            
            result_text = response.text
            data = json.loads(result_text)
            return ReviewResult.model_validate(data)
        except Exception as e:
            print(f"Error during LLM generation: {e}. Falling back to rule-based mock reviews.")
            return self._generate_mock_review(file_path, file_content, added_lines, static_findings, rag_context, dismissed_feedback)

    def _generate_mock_review(self, file_path: str, file_content: str, added_lines: List[int], static_findings: List[Dict[str, Any]], rag_context: List[SearchResult] = None, dismissed_feedback: List[dict] = None) -> ReviewResult:
        """
        Generates a simulated review when LLM is unavailable, integrating rule-based findings and listing RAG results.
        Automatically suppresses issues matching dismissed feedback history.
        """
        comments = []
        
        # Suppress comments matching user dismissal history
        suppressed_titles = set()
        if dismissed_feedback:
            for item in dismissed_feedback:
                title = item.get("comment_title", "").lower().strip()
                if title:
                    suppressed_titles.add(title)
        
        # Convert static findings into review comments
        for f in static_findings:
            # Check if this rule was previously dismissed by the user
            if f["rule_name"].lower().strip() in suppressed_titles:
                continue
                
            severity_map = {
                "critical": Severity.CRITICAL,
                "warning": Severity.WARNING,
                "info": Severity.INFO
            }
            category_map = {
                "SEC": IssueCategory.SECURITY,
                "STYLE": IssueCategory.STYLE,
                "PERF": IssueCategory.PERFORMANCE
            }
            
            rule_prefix = f["rule_id"].split("-")[0]
            category = category_map.get(rule_prefix, IssueCategory.BUG)
            severity = severity_map.get(f["severity"], Severity.INFO)
            
            # Formulate mock code suggestions
            suggestion = None
            original_code = f["code_line"]
            if f["rule_id"] == "SEC-001":
                suggestion = CodeSuggestion(
                    original_code=original_code,
                    replacement_code="api_key = os.environ.get('API_KEY')",
                    explanation="Retrieve the secret from environment variables instead of hardcoding."
                )
            elif f["rule_id"] == "SEC-002":
                suggestion = CodeSuggestion(
                    original_code=original_code,
                    replacement_code="cursor.execute('SELECT * FROM users WHERE id = %s', (user_id,))",
                    explanation="Use parameterized queries to prevent SQL injection."
                )
            elif f["rule_id"] == "STYLE-001":
                suggestion = CodeSuggestion(
                    original_code=original_code,
                    replacement_code="def my_func(items=None):\n    if items is None:\n        items = []",
                    explanation="Avoid mutable list default values to prevent unexpected behavior between function calls."
                )
                
            comments.append(ReviewComment(
                file_path=file_path,
                start_line=f["line"],
                end_line=f["line"],
                category=category,
                severity=severity,
                title=f["rule_name"],
                explanation=f["message"],
                suggestion=suggestion
            ))

        # Add a mock semantic finding if we detect common issues in vulnerable file but no static warnings matched
        if "vulnerable_code.py" in file_path and not static_findings:
            if "mock review finding" not in suppressed_titles:
                comments.append(ReviewComment(
                    file_path=file_path,
                    start_line=12,
                    end_line=12,
                    category=IssueCategory.BUG,
                    severity=Severity.WARNING,
                    title="Mock Review Finding",
                    explanation="This is a mock check indicating where an LLM review would highlight logic issues or improvements.",
                    suggestion=None
                ))

        summary = (
            "### Code Review Summary (Local Mock Mode)\n"
            f"Reviewed `{file_path}` successfully. "
            f"Detected {len(comments)} issues using rule-based pre-filters. "
            "Configure a valid `GEMINI_API_KEY` to run the fully automated LLM reasoning reviews."
        )

        if rag_context:
            summary += "\n\n**Retrieved Codebase Context (RAG):**\n"
            for r in rag_context:
                summary += f"- `{r.chunk.file_path}` (Lines {r.chunk.start_line}-{r.chunk.end_line}, Similarity Score: {r.similarity:.2f}, Type: {r.chunk.chunk_type})\n"

        if dismissed_feedback:
            summary += "\n\n**Applied User Feedback (Suppressed Categories):**\n"
            for item in dismissed_feedback:
                summary += f"- Suppressed `{item.get('comment_title')}` based on feedback logged on {item.get('file_path')}\n"

        return ReviewResult(comments=comments, summary=summary)
