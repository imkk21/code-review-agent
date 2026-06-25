import re
from typing import List, Dict, Any

# Simple regex-based rules
RULES = [
    {
        "id": "SEC-001",
        "name": "Hardcoded Secret",
        "pattern": re.compile(r"(?:api_key|secret|password|token|access_key|private_key)\s*=\s*['\"][a-zA-Z0-9_\-]{8,}['\"]", re.IGNORECASE),
        "message": "Potential hardcoded secret or credential detected. Use environment variables instead.",
        "severity": "critical"
    },
    {
        "id": "SEC-002",
        "name": "SQL Injection Risk",
        "pattern": re.compile(r"\.execute\(\s*f['\"].*\{.*\}['\"]\s*\)", re.IGNORECASE),
        "message": "Potential SQL injection risk. Avoid inserting variables directly into SQL strings using f-strings. Use parameterized queries instead.",
        "severity": "critical"
    },
    {
        "id": "SEC-003",
        "name": "Dangerous Eval/Exec",
        "pattern": re.compile(r"\b(eval|exec)\b\s*\(", re.IGNORECASE),
        "message": "Avoid using eval() or exec() as they can execute arbitrary code and present severe security risks.",
        "severity": "critical"
    },
    {
        "id": "STYLE-001",
        "name": "Mutable Default Argument",
        "pattern": re.compile(r"def\s+[a-zA-Z_][a-zA-Z0-9_]*\s*\(.*=[ \t]*(\[\]|\{\})\s*[,)]", re.IGNORECASE),
        "message": "Avoid using mutable default arguments (like list [] or dict {}). Use None as the default value and instantiate inside the function.",
        "severity": "warning"
    },
    {
        "id": "STYLE-002",
        "name": "Print Statement Debugging",
        "pattern": re.compile(r"\bprint\s*\(", re.IGNORECASE),
        "message": "Leftover print statement. Consider using standard logging instead.",
        "severity": "info"
    },
    {
        "id": "PERF-001",
        "name": "Inefficient String Concatenation",
        "pattern": re.compile(r"\+=\s*['\"].*['\"]", re.IGNORECASE),
        "message": "Concatenating strings inside loops using += can be slow. Use str.join() for better performance.",
        "severity": "info"
    }
]

def analyze_file(file_content: str, file_path: str, target_lines: List[int] = None) -> List[Dict[str, Any]]:
    """
    Analyzes file contents against simple rules.
    If target_lines is provided, only reports findings on those lines.
    """
    findings = []
    lines = file_content.splitlines()
    
    for idx, line in enumerate(lines, start=1):
        # If target lines are specified, restrict checks to these lines
        if target_lines is not None and idx not in target_lines:
            continue
            
        # Strip comments heuristic to avoid matching keywords in comments
        parts = line.split('#', 1)
        code_part = parts[0]
        if len(parts) > 1:
            # If quotes are unbalanced, the '#' might be inside a string literal
            if (code_part.count('"') % 2 != 0) or (code_part.count("'") % 2 != 0):
                code_part = line
                
        code_part = code_part.strip()
        if not code_part:
            continue
            
        for rule in RULES:
            if rule["pattern"].search(code_part):
                findings.append({
                    "file_path": file_path,
                    "line": idx,
                    "rule_id": rule["id"],
                    "rule_name": rule["name"],
                    "message": rule["message"],
                    "severity": rule["severity"],
                    "code_line": line.strip()
                })
                
    return findings
