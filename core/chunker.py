import ast
import os
from typing import List
from core.models import CodeChunk

def chunk_python_file(file_path: str, relative_path: str, content: str) -> List[CodeChunk]:
    """
    Parses Python code using AST and splits it into logical function and class chunks.
    """
    chunks = []
    try:
        tree = ast.parse(content, filename=file_path)
    except SyntaxError:
        # Fall back to text chunking if syntax is invalid
        return chunk_text_file(file_path, relative_path, content)

    lines = content.splitlines()
    
    # We want to traverse only top-level classes and functions, or nested functions
    class Visitor(ast.NodeVisitor):
        def visit_ClassDef(self, node):
            # Extract class source lines
            start = node.lineno
            end = node.end_lineno if hasattr(node, 'end_lineno') else len(lines)
            chunk_content = "\n".join(lines[start-1:end])
            chunks.append(CodeChunk(
                file_path=relative_path,
                content=chunk_content,
                start_line=start,
                end_line=end,
                chunk_type="class"
            ))
            self.generic_visit(node)

        def visit_FunctionDef(self, node):
            start = node.lineno
            end = node.end_lineno if hasattr(node, 'end_lineno') else len(lines)
            chunk_content = "\n".join(lines[start-1:end])
            chunks.append(CodeChunk(
                file_path=relative_path,
                content=chunk_content,
                start_line=start,
                end_line=end,
                chunk_type="function"
            ))
            # No need to visit nested functions unless we want separate chunks for them
            self.generic_visit(node)

        def visit_AsyncFunctionDef(self, node):
            self.visit_FunctionDef(node)

    visitor = Visitor()
    visitor.visit(tree)
    
    # If no structured chunks were found, create a module-level chunk
    if not chunks:
        chunks.append(CodeChunk(
            file_path=relative_path,
            content=content,
            start_line=1,
            end_line=len(lines),
            chunk_type="module"
        ))
        
    return chunks

def chunk_text_file(file_path: str, relative_path: str, content: str) -> List[CodeChunk]:
    """
    Chunks a non-python text file (like md, yaml, json) by paragraphs or line windows.
    """
    chunks = []
    lines = content.splitlines()
    if not lines:
        return []
        
    # Chunk by paragraphs or groups of 25 lines with overlap of 5 lines
    chunk_size = 25
    overlap = 5
    
    i = 0
    while i < len(lines):
        end = min(i + chunk_size, len(lines))
        chunk_content = "\n".join(lines[i:end])
        chunks.append(CodeChunk(
            file_path=relative_path,
            content=chunk_content,
            start_line=i + 1,
            end_line=end,
            chunk_type="general"
        ))
        i += (chunk_size - overlap)
        
    return chunks

def chunk_file(file_path: str, workspace_root: str = "") -> List[CodeChunk]:
    """
    Reads a file and returns its semantic chunks based on file type.
    """
    if not os.path.exists(file_path):
        return []
        
    relative_path = os.path.relpath(file_path, workspace_root) if workspace_root else file_path
    relative_path = relative_path.replace("\\", "/") # Normalize paths for RAG index consistency
    
    # Try reading file contents as utf-8 text
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
    except Exception:
        # Ignore binary or unreadable files
        return []
        
    if not content.strip():
        return []
        
    _, ext = os.path.splitext(file_path.lower())
    if ext == ".py":
        return chunk_python_file(file_path, relative_path, content)
    elif ext in [".md", ".txt", ".json", ".yaml", ".yml", ".js", ".ts", ".html", ".css"]:
        return chunk_text_file(file_path, relative_path, content)
    else:
        # For unsupported extensions, skip or do generic text chunking if they are text
        return []
