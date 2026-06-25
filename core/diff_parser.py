import re
from typing import List, Dict, Any, Set

def parse_diff(diff_text: str) -> List[Dict[str, Any]]:
    """
    Parses a unified git diff into a list of structured file changes.
    Each file change contains:
      - file_path: target path (e.g., 'src/main.py')
      - is_new: bool indicating if the file is newly created
      - is_deleted: bool indicating if the file was deleted
      - hunks: list of hunks, each hunk is a dict with 'old_start', 'new_start', 'lines'
      - added_lines: list of line numbers in the new file that were added/modified
    """
    files = []
    current_file = None
    hunk_header_regex = re.compile(r"^@@ -(\d+),?(\d*) \+(\d+),?(\d*) @@")

    lines = diff_text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        
        # Detect start of file diff
        if line.startswith("diff --git"):
            # If we had a file in progress, save it
            if current_file:
                files.append(current_file)
            
            current_file = {
                "file_path": None,
                "is_new": False,
                "is_deleted": False,
                "hunks": [],
                "added_lines": set()
            }
            # Extract file path (handles simple renames or custom prefixes)
            # Standard: diff --git a/path/to/file b/path/to/file
            parts = line.split(" ")
            if len(parts) >= 4:
                b_path = parts[3]
                if b_path.startswith("b/"):
                    current_file["file_path"] = b_path[2:]
                else:
                    current_file["file_path"] = b_path
            i += 1
            continue

        if not current_file:
            i += 1
            continue

        # Check for metadata
        if line.startswith("new file mode"):
            current_file["is_new"] = True
            i += 1
            continue
        elif line.startswith("deleted file mode"):
            current_file["is_deleted"] = True
            i += 1
            continue
        elif line.startswith("--- a/"):
            # Update file_path if not set
            i += 1
            continue
        elif line.startswith("+++ b/"):
            # Update file_path if not set
            path = line[6:]
            current_file["file_path"] = path
            i += 1
            continue

        # Match hunk header
        match = hunk_header_regex.match(line)
        if match:
            old_start = int(match.group(1))
            new_start = int(match.group(3))
            
            hunk = {
                "old_start": old_start,
                "new_start": new_start,
                "lines": []
            }
            current_file["hunks"].append(hunk)
            
            # Start tracking line numbers for the new file
            current_new_line = new_start
            
            i += 1
            # Parse hunk content lines
            while i < len(lines) and not lines[i].startswith("diff --git") and not lines[i].startswith("@@"):
                hunk_line = lines[i]
                hunk["lines"].append(hunk_line)
                
                if hunk_line.startswith("+"):
                    current_file["added_lines"].add(current_new_line)
                    current_new_line += 1
                elif hunk_line.startswith("-"):
                    # Deletion does not advance line count in new file
                    pass
                else:
                    # Context line advances both
                    current_new_line += 1
                i += 1
            continue

        i += 1

    if current_file:
        files.append(current_file)

    # Convert sets to sorted lists for final return
    for f in files:
        f["added_lines"] = sorted(list(f["added_lines"]))

    return files
