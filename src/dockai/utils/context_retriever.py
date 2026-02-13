"""
DockAI Context Retriever Module.

This module combines AST analysis and semantic search to retrieve
the most relevant context for Dockerfile generation. It acts as
the intelligence layer between the project index and the LLM.

Key Features:
- Combines multiple retrieval strategies (AST, semantic, pattern matching)
- Deduplicates and ranks retrieved content
- Generates structured summaries from code analysis
- Respects token limits with smart truncation
- **Dynamic Context**: Adapts search strategy based on detected project stack

Architecture:
    Query → [AST Lookup] + [Semantic Search] + [Pattern Match] → Merged Context
                                                                      ↓
                                                              Ranked + Deduplicated
                                                                      ↓
                                                              Context for LLM
"""

import os
import logging
from typing import List, Dict, Set, Optional, Any
from dataclasses import dataclass

from .indexer import ProjectIndex, FileChunk
from .code_intelligence import FileAnalysis

logger = logging.getLogger("dockai")


@dataclass
class RetrievedContext:
    """
    Container for retrieved context with metadata.
    
    Attributes:
        content: The actual text content.
        source: Source file path.
        relevance_score: How relevant this context is (0.0 - 1.0).
        context_type: Type of context ("dependency", "entry_point", "config", "semantic_match").
    """
    content: str
    source: str
    relevance_score: float
    context_type: str


class ContextRetriever:
    """
    Retrieves optimal context for Dockerfile generation.
    
    This class orchestrates multiple retrieval strategies to gather
    the most relevant information for the LLM:
    
    1. **Must-Have Files**: Dependencies, existing Dockerfiles, configs
    2. **AST-Extracted**: Entry points, environment variables, ports
    3. **Semantic Search**: Content matching Dockerfile-related queries (Stack-aware)
    
    Example Usage:
        >>> index = ProjectIndex(use_embeddings=True)
        >>> index.index_project("/path/to/project", file_tree)
        >>> retriever = ContextRetriever(index, analysis_result)
        >>> context = retriever.get_dockerfile_context(max_tokens=50000)
    """
    
    # Files that should always be included if present (General)
    MUST_HAVE_FILES = {
        # Dependency files
        "package.json", "requirements.txt", "pyproject.toml",
        "go.mod", "cargo.toml", "gemfile", "pom.xml", "build.gradle",
        "composer.json", "setup.py", "pipfile",
        # Docker files
        "dockerfile", "docker-compose.yml", "docker-compose.yaml",
        ".dockerignore",
        # Config files
        ".env.example", ".env.sample",
        # Version files
        ".nvmrc", ".python-version", ".ruby-version", ".node-version", ".tool-versions",
    }
    
    # Base queries for semantic search
    BASE_QUERIES = [
        "install dependencies build requirements",
        "main entry point start server application",
        "configuration environment variables settings",
        "port listen bind http server",
        "database connection redis mongo postgres",
    ]
    
    def __init__(self, index: ProjectIndex, analysis_result: Dict[str, Any] = None):
        """
        Initialize the context retriever.
        
        Args:
            index: A populated ProjectIndex instance.
            analysis_result: Result from the Analysis stage (stack, project_type).
        """
        self.index = index
        self.analysis_result = analysis_result or {}
    
    def get_dockerfile_context(self, max_tokens: int = 50000) -> str:
        """
        Retrieve optimal context for Dockerfile generation.
        
        This method combines multiple strategies to gather comprehensive
        context while respecting token limits:
        
        1. Include all must-have files (dependencies, existing Docker files)
        2. Extract and summarize AST analysis (entry points, env vars, ports)
        3. Perform semantic search for Dockerfile-relevant content (Stack-aware)
        4. Deduplicate and merge results
        5. Truncate to fit within token limit
        
        Args:
            max_tokens: Maximum tokens for the context (approx 4 chars/token).
            
        Returns:
            Formatted string containing all relevant context.
        """
        context_parts: List[RetrievedContext] = []
        seen_files: Set[str] = set()
        
        # 1. MUST-HAVE FILES: Always include these if present
        # Enhance MUST_HAVE based on stack
        target_files = self.MUST_HAVE_FILES.copy()
        stack = self.analysis_result.get("stack", "").lower()
        if "python" in stack:
            target_files.update({"manage.py", "wsgi.py", "asgi.py", "gunicorn.conf.py", "uwsgi.ini"})
        elif "node" in stack or "javascript" in stack:
            target_files.update({"yarn.lock", "package-lock.json", "next.config.js", "vite.config.js", "webpack.config.js"})
        elif "go" in stack:
            target_files.update({"main.go"})
            
        for chunk in self.index.chunks:
            filename = os.path.basename(chunk.file_path).lower()
            if filename in target_files:
                if chunk.file_path not in seen_files:
                    # Special handling for lock files: Truncate heavily to save tokens
                    if "lock" in filename and filename not in ("yarn.lock", "go.sum", "cargo.lock"): # Keep some lock files but maybe truncate
                         # For massive lock files, strict limit
                         context_parts.append(RetrievedContext(
                            content=self._format_chunk(chunk, truncate_lines=50), 
                            source=chunk.file_path,
                            relevance_score=1.0, 
                            context_type="must_have"
                        ))
                    else:
                        context_parts.append(RetrievedContext(
                            content=self._format_chunk(chunk),
                            source=chunk.file_path,
                            relevance_score=1.0,  # Highest priority
                            context_type="must_have"
                        ))
                    seen_files.add(chunk.file_path)
        
        # 2. AST-EXTRACTED INTELLIGENCE: Summarize code analysis
        ast_summary = self._generate_ast_summary()
        if ast_summary:
            context_parts.append(RetrievedContext(
                content=ast_summary,
                source="__ast_analysis__",
                relevance_score=0.95,
                context_type="ast_summary"
            ))
        
        # 3. ENTRY POINT CODE: Include actual code for detected entry points
        entry_point_code = self._get_entry_point_code()
        for code in entry_point_code:
            if code["source"] not in seen_files:
                context_parts.append(RetrievedContext(
                    content=code["content"],
                    source=code["source"],
                    relevance_score=0.9,
                    context_type="entry_point"
                ))
                seen_files.add(code["source"])
        
        # 4. GRAPH TRAVERSAL: Follow imports from entry points
        imported_files = self._get_imported_files(seen_files)
        for imp_file in imported_files:
            if imp_file["source"] not in seen_files:
                context_parts.append(RetrievedContext(
                    content=imp_file["content"],
                    source=imp_file["source"],
                    relevance_score=0.85, # Higher than semantic search, lower than direct entry point
                    context_type="imported_dependency"
                ))
                seen_files.add(imp_file["source"])

        # 5. SEMANTIC SEARCH: Find relevant chunks
        queries = self._generate_dynamic_queries()
        
        for query in queries:
            results = self.index.search(query, top_k=3)
            for chunk in results:
                if chunk.file_path not in seen_files:
                    context_parts.append(RetrievedContext(
                        content=self._format_chunk(chunk),
                        source=chunk.file_path,
                        relevance_score=0.7,
                        context_type="semantic_match"
                    ))
                    seen_files.add(chunk.file_path)

        # 6. CATCH-ALL: Include ALL other files if enabled (default: True)
        # This addresses user requirement for "no filtering" while keeping priority logic.
        read_all = os.getenv("DOCKAI_READ_ALL_FILES", "true").lower() in ("true", "1", "yes", "on")
        if read_all:
            for chunk in self.index.chunks:
                if chunk.file_path not in seen_files:
                    # Give lower relevance so they are dropped first if token limit hit
                    context_parts.append(RetrievedContext(
                        content=self._format_chunk(chunk),
                        source=chunk.file_path,
                        relevance_score=0.5,
                        context_type="catch_all"
                    ))
                    seen_files.add(chunk.file_path)
        
        # 7. SORT by relevance and MERGE
        context_parts.sort(key=lambda x: x.relevance_score, reverse=True)
        
        # 8. BUILD final context string with token limit
        max_chars = max_tokens * 4  # Approximate chars per token
        final_context = self._build_final_context(context_parts, max_chars)
        
        logger.info(
            f"Context retriever: {len(context_parts)} sources, "
            f"{len(final_context)} chars (~{len(final_context)//4} tokens)"
        )
        
        return final_context
    
    def _generate_dynamic_queries(self) -> List[str]:
        """Generate search queries based on project analysis."""
        queries = self.BASE_QUERIES.copy()
        stack = self.analysis_result.get("stack", "").lower()
        
        # Add stack-specific queries
        if "python" in stack:
            queries.extend([
                "wsgi application object",
                "asgi application object",
                "django settings configuration",
                "flask app instance",
                "gunicorn configuration"
            ])
        elif "node" in stack or "javascript" in stack:
            queries.extend([
                "npm run start script",
                "node_modules location",
                "next.config.js export",
                "express app listen"
            ])
        elif "go" in stack:
             queries.extend([
                "go build output",
                "func main execution",
                "gin router setup"
            ])
        
        return queries

    def _format_chunk(self, chunk: FileChunk, truncate_lines: Optional[int] = None) -> str:
        """
        Format a chunk for inclusion in context.
        
        Args:
            chunk: The FileChunk to format.
            truncate_lines: Optional limit on lines (useful for lockfiles).
        """
        from .file_utils import minify_code
        
        # Minify content to save tokens (remove comments/whitespace)
        # We don't minify dependent files where exact line numbers might matter less than config structure
        # But generally minification helps RAG.
        content = minify_code(chunk.content, chunk.file_path)
        
        if truncate_lines:
             lines = content.split('\n')
             if len(lines) > truncate_lines:
                 content = '\n'.join(lines[:truncate_lines]) + f"\n... (truncated {len(lines)-truncate_lines} lines) ..."

        if chunk.chunk_type == "full":
            return f"--- FILE: {chunk.file_path} ---\n{content}"
        else:
            return (
                f"--- FILE: {chunk.file_path} (lines {chunk.start_line}-{chunk.end_line}) ---\n"
                f"{content}"
            )
    
    def _generate_ast_summary(self) -> str:
        """Generate a summary of AST analysis for the LLM."""
        if not self.index.code_analysis:
            return ""
        
        parts = ["--- CODE INTELLIGENCE SUMMARY ---"]
        
        # Entry points
        entry_points = self.index.get_entry_points()
        if entry_points:
            parts.append(f"\n## Detected Entry Points:")
            for ep in entry_points[:10]:  # Limit to 10
                parts.append(f"  - {ep}")
        
        # Environment variables
        env_vars = self.index.get_all_env_vars()
        if env_vars:
            parts.append(f"\n## Environment Variables Used in Code:")
            parts.append(f"  {', '.join(sorted(env_vars)[:20])}")  # Limit to 20
        
        # Ports
        ports = self.index.get_all_ports()
        if ports:
            parts.append(f"\n## Ports Detected in Code:")
            parts.append(f"  {', '.join(str(p) for p in sorted(ports))}")
        
        # Frameworks
        frameworks = self.index.get_frameworks()
        if frameworks:
            parts.append(f"\n## Frameworks Detected:")
            parts.append(f"  {', '.join(sorted(frameworks))}")
        
        # Languages
        languages = set(a.language for a in self.index.code_analysis.values())
        if languages:
            parts.append(f"\n## Languages:")
            parts.append(f"  {', '.join(sorted(languages))}")
        
        if len(parts) > 1:
            return "\n".join(parts)
        return ""
    
    def _get_entry_point_code(self) -> List[Dict]:
        """Get the actual code for detected entry points."""
        results = []
        
        for path, analysis in self.index.code_analysis.items():
            if not analysis.entry_points:
                continue
            
            # Find the chunk containing this file
            for chunk in self.index.chunks:
                if chunk.file_path == path and chunk.chunk_type == "full":
                    results.append({
                        "source": path,
                        "content": f"--- ENTRY POINT FILE: {path} ---\n{chunk.content}"
                    })
                    break
        
        return results[:5]  # Limit to 5 entry point files
    
    def _get_imported_files(self, seen_files: Set[str]) -> List[Dict]:
        """
        Graph-RAG: Retrieve files imported by entry points.
        This follows the import graph to find critical dependencies (settings, db config, etc.)
        that might be missed by semantic search.
        """
        results = []
        project_files = {c.file_path for c in self.index.chunks}
        
        # Identify entry point files
        entry_point_files = [
            path for path, analysis in self.index.code_analysis.items()
            if analysis.entry_points
        ]
        
        # If no explicit entry points, try to guess main files
        if not entry_point_files:
            entry_point_files = [
                f for f in project_files 
                if f.lower() in ('app.py', 'main.py', 'server.js', 'index.js', 'main.go', 'manage.py')
            ]
        
        target_imports = set()
        
        # Collect all imports from entry point files
        for ep_file in entry_point_files:
            if ep_file in self.index.code_analysis:
                target_imports.update(self.index.code_analysis[ep_file].imports)
                
        # Resolve imports to file paths
        for imp in target_imports:
            resolved_path = self._resolve_import_path(imp, project_files)
            if resolved_path and resolved_path not in seen_files:
                 # Find content
                for chunk in self.index.chunks:
                    if chunk.file_path == resolved_path and chunk.chunk_type == "full":
                        results.append({
                            "source": resolved_path,
                            "content": self._format_chunk(chunk)
                        })
                        import_hit_msg = f"Graph-RAG: Found imported dependency '{imp}' -> {resolved_path}"
                        logger.debug(import_hit_msg)
                        break
        
        return results

    def _resolve_import_path(self, import_name: str, project_files: Set[str]) -> Optional[str]:
        """
        Resolve a Python/JS import string to a likely file path in the project.
        """
        # Python style: "from core.config import settings" -> "core/config.py"
        py_path = import_name.replace('.', '/') + '.py'
        if py_path in project_files:
            return py_path
            
        # Check __init__.py for module imports
        init_path = import_name.replace('.', '/') + '/__init__.py'
        if init_path in project_files:
            return init_path
            
        # JS style: "./utils" -> "utils.js" or "utils/index.js"
        # Since import_name typically comes from AST which cleans it, we assume basic name
        js_path = import_name + '.js'
        if js_path in project_files:
            return js_path
            
        js_ts_path = import_name + '.ts'
        if js_ts_path in project_files:
            return js_ts_path
            
        # Try direct match (if import was "utils.py")
        if import_name in project_files:
            return import_name
            
        return None

    def _build_final_context(
        self, 
        context_parts: List[RetrievedContext], 
        max_chars: int
    ) -> str:
        """Build the final context string with deduplication and truncation."""
        final_parts = []
        current_chars = 0
        
        for ctx in context_parts:
            content_chars = len(ctx.content)
            
            if current_chars + content_chars > max_chars:
                # Check if we can add a truncated version
                remaining = max_chars - current_chars
                if remaining > 500:  # Only add if significant space remains
                    truncated = ctx.content[:remaining-100] + "\n\n... [TRUNCATED] ..."
                    final_parts.append(truncated)
                break
            
            final_parts.append(ctx.content)
            current_chars += content_chars + 2  # +2 for newlines
        
        return "\n\n".join(final_parts)
    
    def get_quick_summary(self) -> Dict:
        """
        Get a quick summary of what the retriever found.
        
        Returns:
            Dictionary with summary statistics.
        """
        return {
            "files_indexed": len(self.index.chunks),
            "files_analyzed": len(self.index.code_analysis),
            "entry_points": self.index.get_entry_points(),
            "env_vars": self.index.get_all_env_vars(),
            "ports": self.index.get_all_ports(),
            "frameworks": self.index.get_frameworks(),
            "embeddings_available": self.index.chunk_embeddings is not None,
        }
