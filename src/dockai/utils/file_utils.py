"""
DockAI File Utilities Module.

This module provides utilities for reading and processing project files
for LLM consumption. It includes intelligent truncation, token estimation,
and code minification to optimize context sent to language models.
"""

import os
import logging
import re
from typing import List, Optional

logger = logging.getLogger("dockai")

# Approximate tokens per character (rough estimate: 1 token ≈ 4 chars for English text/code)
CHARS_PER_TOKEN = 4


def estimate_tokens(text: str) -> int:
    """Estimate the number of tokens in a string (rough approximation)."""
    return len(text) // CHARS_PER_TOKEN


def minify_code(content: str, filename: str) -> str:
    """
    Minify code by removing comments and excessive whitespace.
    This saves tokens without losing semantic meaning for the LLM.
    """
    if not content:
        return ""
        
    ext = os.path.splitext(filename)[1].lower()
    
    # Python/Ruby/Shell/Perl/YAML/Dockerfile style comments (#)
    if ext in ('.py', '.rb', '.sh', '.pl', '.yml', '.yaml', '.dockerfile', '.conf', '.ini', '.toml'):
        # Remove lines that are purely comments, but keep inline comments to be safe (simpler regex)
        # Also remove empty lines
        lines = content.splitlines()
        minified_lines = []
        for line in lines:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            minified_lines.append(line)
        return "\n".join(minified_lines)
    
    # C-style comments (//) for JS, TS, Go, Java, C, C++, Rust
    elif ext in ('.js', '.ts', '.jsx', '.tsx', '.go', '.java', '.c', '.cpp', '.h', '.rs', '.css', '.scss'):
        lines = content.splitlines()
        minified_lines = []
        for line in lines:
            stripped = line.strip()
            if not stripped or stripped.startswith("//"):
                continue
            minified_lines.append(line)
        return "\n".join(minified_lines)
        
    return content



def smart_truncate(content: str, filename: str, max_chars: int, max_lines: int) -> str:
    """
    Truncates file content while preserving as much context as possible.
    
    Strategies:
    1. If content fits, return as is.
    2. If it's a code file (py, js, ts, go, rs, java), try to preserve structure.
    3. Fallback to Head + Tail truncation.
    """
    if len(content) <= max_chars and len(content.splitlines()) <= max_lines:
        return content

    lines = content.splitlines()
    total_lines = len(lines)
    
    # Strategy 1: Simple Head + Tail for non-code or massive files
    # We keep more of the head (context/imports) than the tail
    head_ratio = 0.7
    keep_lines = max_lines
    
    if total_lines > keep_lines:
        head_count = int(keep_lines * head_ratio)
        tail_count = keep_lines - head_count
        
        head = "\n".join(lines[:head_count])
        tail = "\n".join(lines[-tail_count:])
        
        return f"{head}\n\n... [TRUNCATED {total_lines - keep_lines} LINES] ...\n\n{tail}"
        
    return content

def read_critical_files(path: str, files_to_read: List[str], truncation_enabled: bool = None) -> str:
    """
    Reads critical files from the repository with optional smart truncation.
    
    Truncation behavior:
    1. If truncation_enabled is explicitly set (True/False), use that.
    2. Otherwise, check DOCKAI_TRUNCATION_ENABLED env var (true/false/1/0).
    3. Default is False (no truncation).
    4. Auto-enables truncation if total content exceeds DOCKAI_TOKEN_LIMIT.
    
    Args:
        path: Root path of the repository.
        files_to_read: List of relative paths to read.
        truncation_enabled: Whether to truncate large files (default: None = use env var).
        
    Returns:
        String containing concatenated file contents.
    """
    # Determine truncation setting from env var if not explicitly provided
    if truncation_enabled is None:
        env_truncation = os.getenv("DOCKAI_TRUNCATION_ENABLED", "false").lower()
        truncation_enabled = env_truncation in ("true", "1", "yes", "on")
    
    # Get token limit for auto-truncation (default: 50K tokens ≈ 200K chars)
    try:
        TOKEN_LIMIT = int(os.getenv("DOCKAI_TOKEN_LIMIT", "50000"))
    except ValueError:
        TOKEN_LIMIT = 50000
    
    file_contents_str = ""
    files_read = 0
    files_failed = []
    auto_truncation_triggered = False
    
    # Files that should be read fully if possible (dependencies)
    CRITICAL_DEPENDENCY_FILES = ["package.json", "requirements.txt", "Gemfile", "go.mod", "Cargo.toml", "pom.xml", "build.gradle"]
    # Files to skip
    SKIP_FILES = ["package-lock.json", "yarn.lock", "pnpm-lock.yaml", "Gemfile.lock", "go.sum", "Cargo.lock"]

    # Get limits from env or use defaults
    try:
        MAX_CHARS = int(os.getenv("DOCKAI_MAX_FILE_CHARS", "200000"))
        MAX_LINES = int(os.getenv("DOCKAI_MAX_FILE_LINES", "5000"))
    except ValueError:
        MAX_CHARS = 200000
        MAX_LINES = 5000

    for rel_path in files_to_read:
        basename = os.path.basename(rel_path)
        
        if basename in SKIP_FILES:
            logger.info(f"Skipping lock file: {rel_path}")
            continue
            
        abs_file_path = os.path.join(path, rel_path)
        try:
            with open(abs_file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
                
                # Determine limits based on file type
                is_dependency_file = basename in CRITICAL_DEPENDENCY_FILES
                
                # Only truncate if truncation is enabled
                if truncation_enabled:
                    # Dependency files get double the line limit but same char limit
                    current_max_lines = MAX_LINES * 2 if is_dependency_file else MAX_LINES
                    current_max_chars = MAX_CHARS
                    
                    original_len = len(content)
                    content = smart_truncate(content, basename, current_max_chars, current_max_lines)
                    
                    if len(content) < original_len:
                        logger.warning(f"Truncated {rel_path}: {original_len} -> {len(content)} chars")
                    
                file_contents_str += f"--- FILE: {rel_path} ---\n{content}\n\n"
                files_read += 1
        except Exception as e:
            logger.warning(f"Could not read {rel_path}: {e}")
            files_failed.append(rel_path)
    
    # Auto-truncation: If total content exceeds token limit, re-read with truncation enabled
    estimated_tokens = estimate_tokens(file_contents_str)
    if not truncation_enabled and estimated_tokens > TOKEN_LIMIT:
        logger.warning(
            f"Content exceeds token limit ({estimated_tokens:,} tokens > {TOKEN_LIMIT:,} limit). "
            f"Auto-enabling truncation..."
        )
        # Re-read files with truncation enabled
        return read_critical_files(path, files_to_read, truncation_enabled=True)
    
    if truncation_enabled:
        logger.info(f"Final content size: ~{estimated_tokens:,} tokens")
    
    logger.info(f"Successfully read {files_read} files" + (f", {len(files_failed)} failed" if files_failed else ""))
    return file_contents_str
