import os
from pathlib import Path

from .decorator import tool


def _validate_path(path: str) -> Path:
    """Validate and sanitize path to prevent path traversal attacks."""
    p = Path(path).resolve()
    if ".." in Path(path).parts:
        raise ValueError("Path traversal is not allowed")
    return p


@tool(
    name="FileRead",
    description="Read the contents of a file from the filesystem"
)
async def file_read(path: str, limit: int = None, offset: int = 0) -> str:
    """
    Read a file
    
    Args:
        path: Path to the file to read
        limit: Maximum number of lines to read (optional)
        offset: Starting line number (default: 0)
    
    Returns:
        File contents
    """
    try:
        p = _validate_path(path)
        if not p.exists():
            return f"Error: File not found: {path}"
        if not p.is_file():
            return f"Error: Not a file: {path}"
        
        with open(p, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        start = offset
        if start > len(lines):
            return ""
        
        if limit is not None:
            end = start + limit
            lines = lines[start:end]
        else:
            lines = lines[start:]
        
        return ''.join(lines)
    
    except PermissionError:
        return f"Error: Permission denied: {path}"
    except Exception as e:
        return f"Error: {str(e)}"


@tool(
    name="FileWrite",
    description="Write content to a file, creating or overwriting as needed"
)
async def file_write(path: str, content: str, append: bool = False) -> str:
    """
    Write to a file
    
    Args:
        path: Path to the file to write
        content: Content to write
        append: If True, append to existing file instead of overwriting
    
    Returns:
        Success message
    """
    try:
        p = _validate_path(path)
        
        parent = p.parent
        if not parent.exists():
            return f"Error: Directory does not exist: {parent}"
        
        mode = 'a' if append else 'w'
        with open(p, mode, encoding='utf-8') as f:
            f.write(content)
        
        action = "Appended to" if append else "Written to"
        return f"{action} file: {path}"
    
    except PermissionError:
        return f"Error: Permission denied: {path}"
    except Exception as e:
        return f"Error: {str(e)}"


@tool(
    name="FileEdit",
    description="Edit a file by replacing specific content with new content"
)
async def file_edit(path: str, old_content: str, new_content: str) -> str:
    """
    Edit a file
    
    Args:
        path: Path to the file to edit
        old_content: The content to find and replace
        new_content: The new content to replace with
    
    Returns:
        Success message
    """
    try:
        p = _validate_path(path)
        
        if not p.exists():
            return f"Error: File not found: {path}"
        if not p.is_file():
            return f"Error: Not a file: {path}"
        
        with open(p, 'r', encoding='utf-8') as f:
            content = f.read()
        
        if old_content not in content:
            return f"Error: Content not found in file: {path}"
        
        new_file_content = content.replace(old_content, new_content)
        
        with open(p, 'w', encoding='utf-8') as f:
            f.write(new_file_content)
        
        return f"Edited file: {path}"
    
    except PermissionError:
        return f"Error: Permission denied: {path}"
    except Exception as e:
        return f"Error: {str(e)}"
