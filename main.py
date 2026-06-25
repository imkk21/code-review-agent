import os
import sys
import argparse
import subprocess

# Reconfigure stdout/stderr to support unicode emojis on Windows
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

from core.diff_parser import parse_diff
from core.static_analysis import analyze_file
from core.reviewer import CodeReviewer
from core.rag_orchestrator import RAGOrchestrator
from core.config import load_env

# Load environment variables from .env file
load_env()

def print_review_report(review_result):
    """
    Renders the review results in a beautiful Markdown format to stdout.
    """
    print("\n" + "="*80)
    print("                      CODE REVIEW AGENT REPORT")
    print("="*80)
    
    print(f"\n{review_result.summary}\n")
    
    if not review_result.comments:
        print("🎉 No issues detected! Your code changes look clean and well-structured.")
        print("="*80 + "\n")
        return
        
    print(f"Detected {len(review_result.comments)} issue(s):\n")
    
    for idx, comment in enumerate(review_result.comments, 1):
        severity_color = {
            "critical": "🚨 CRITICAL",
            "warning": "⚠️ WARNING",
            "info": "ℹ️ INFO"
        }.get(comment.severity, comment.severity.upper())
        
        category_icon = {
            "bug": "🐛 Bug",
            "security": "🔒 Security",
            "performance": "⚡ Performance",
            "style": "🎨 Style/Maintainability"
        }.get(comment.category, comment.category.capitalize())
        
        print(f"{idx}. {severity_color} | {category_icon} | {comment.title}")
        print(f"   File: {comment.file_path} (Lines {comment.start_line}-{comment.end_line})")
        print(f"   Explanation: {comment.explanation}")
        
        if comment.suggestion:
            print("\n   💡 Suggested Fix:")
            print("   " + "-"*40)
            print("   [Original Code]:")
            for line in comment.suggestion.original_code.splitlines():
                print(f"   - {line}")
            print("\n   [Replacement Code]:")
            for line in comment.suggestion.replacement_code.splitlines():
                print(f"   + {line}")
            print(f"   Explanation: {comment.suggestion.explanation}")
            print("   " + "-"*40)
        print("\n" + "-"*80)
        
    print("="*80 + "\n")

def run_git_diff() -> str:
    """
    Retrieves the current git diff of unstaged changes.
    """
    try:
        result = subprocess.run(
            ["git", "diff"],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"Error executing 'git diff': {e.stderr}")
        return ""
    except FileNotFoundError:
        print("Error: 'git' command not found. Please ensure Git is installed and in your PATH.")
        return ""

def main():
    parser = argparse.ArgumentParser(description="Autonomous AI Code Review Agent (Core Prototype)")
    parser.add_argument("--file", help="Path to a single file to review (simulates reviewing all lines).")
    parser.add_argument("--diff", help="Path to a file containing a raw git diff.")
    parser.add_argument("--git", action="store_true", help="Review current unstaged git changes in the workspace.")
    parser.add_argument("--index", help="Index all code files in the specified directory into RAG memory.")
    parser.add_argument("--model", default="gemini-3.1-flash-lite", help="Gemini model to use for reviews.")
    parser.add_argument("--output", help="Optional path to write the review report in Markdown format.")
    
    args = parser.parse_args()
    
    if not (args.file or args.diff or args.git or args.index):
        parser.print_help()
        sys.exit(0)

    # Scenario 0: Index a directory
    if args.index:
        if not os.path.exists(args.index):
            print(f"Error: Path '{args.index}' does not exist.")
            sys.exit(1)
        print(f"📂 Indexing directory '{args.index}' into local RAG codebase memory...")
        orchestrator = RAGOrchestrator(workspace_root=args.index)
        orchestrator.db.clear() # Clear database for a clean start
        stats = orchestrator.index_directory(args.index)
        print(f"✅ Indexing complete!")
        print(f"   Indexed Files: {stats['indexed_files']}")
        print(f"   Total Chunks:  {stats['total_chunks']}")
        print(f"   Skipped Files: {stats['skipped_files']}")
        sys.exit(0)

    reviewer = CodeReviewer(model_name=args.model)
    orchestrator = RAGOrchestrator(workspace_root=os.getcwd())
    all_comments = []
    summaries = []

    # Scenario 1: Review a single file
    if args.file:
        if not os.path.exists(args.file):
            print(f"Error: File '{args.file}' does not exist.")
            sys.exit(1)
            
        print(f"🔍 Analyzing single file: {args.file}...")
        with open(args.file, "r", encoding="utf-8") as f:
            content = f.read()
            
        lines_count = len(content.splitlines())
        added_lines = list(range(1, lines_count + 1))  # Review whole file
        
        static_findings = analyze_file(content, args.file, added_lines)
        rag_context = orchestrator.get_context_for_changes(args.file, added_lines)
        review_result = reviewer.review_changes(args.file, content, added_lines, static_findings, rag_context=rag_context)
        
        all_comments.extend(review_result.comments)
        summaries.append(review_result.summary)

    # Scenario 2: Review a diff file
    elif args.diff:
        if not os.path.exists(args.diff):
            print(f"Error: Diff file '{args.diff}' does not exist.")
            sys.exit(1)
            
        print(f"🔍 Parsing diff file: {args.diff}...")
        with open(args.diff, "r", encoding="utf-8") as f:
            diff_text = f.read()
            
        file_changes = parse_diff(diff_text)
        if not file_changes:
            print("⚠️ No file changes parsed from diff.")
            sys.exit(0)
            
        for fc in file_changes:
            file_path = fc["file_path"]
            if not file_path or fc["is_deleted"]:
                continue
                
            # Try to read file locally to run static analysis & get full contents for context
            content = ""
            if os.path.exists(file_path):
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
            
            static_findings = analyze_file(content, file_path, fc["added_lines"]) if content else []
            rag_context = orchestrator.get_context_for_changes(file_path, fc["added_lines"]) if content else []
            review_result = reviewer.review_changes(file_path, content, fc["added_lines"], static_findings, rag_context=rag_context)
            
            all_comments.extend(review_result.comments)
            summaries.append(review_result.summary)

    # Scenario 3: Review active git workspace changes
    elif args.git:
        print("🔍 Retrieving active Git diff...")
        diff_text = run_git_diff()
        if not diff_text.strip():
            print("🎉 No unstaged changes found in active git repository.")
            sys.exit(0)
            
        file_changes = parse_diff(diff_text)
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
            review_result = reviewer.review_changes(file_path, content, fc["added_lines"], static_findings, rag_context=rag_context)
            
            all_comments.extend(review_result.comments)
            summaries.append(review_result.summary)

    # Combine results
    final_summary = "\n\n".join(summaries)
    from core.models import ReviewResult as ReviewResultModel
    final_result = ReviewResultModel(comments=all_comments, summary=final_summary)
    
    # Print report
    print_review_report(final_result)
    
    # Save to history ledger and trigger Slack alerts
    try:
        from app import save_review_run
        target_label = args.file if args.file else (args.diff if args.diff else "Git Workspace")
        save_review_run(target_label, final_result)
    except Exception as e:
        print(f"Warning: Failed to log review to history database: {e}")
        
    # Save output if requested
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write("# Code Review Report\n\n")
            f.write(final_result.summary + "\n\n")
            f.write("## Findings\n\n")
            if not final_result.comments:
                f.write("No issues detected.\n")
            for idx, c in enumerate(final_result.comments, 1):
                f.write(f"### {idx}. {c.severity.upper()} | {c.category.upper()} | {c.title}\n")
                f.write(f"- **File:** `{c.file_path}` (Lines {c.start_line}-{c.end_line})\n")
                f.write(f"- **Explanation:** {c.explanation}\n")
                if c.suggestion:
                    f.write("- **Suggested Fix:**\n")
                    f.write("  ```python\n")
                    f.write(f"  # Original:\n  # {c.suggestion.original_code}\n")
                    f.write(f"  # Replacement:\n  {c.suggestion.replacement_code}\n")
                    f.write("  ```\n")
                f.write("\n---\n")
        print(f"💾 Report saved to: {args.output}")

if __name__ == "__main__":
    main()
