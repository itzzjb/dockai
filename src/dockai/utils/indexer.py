"""
DockAI Project Indexer Module.

This module provides semantic indexing of project files for intelligent
context retrieval. It uses local embeddings (no API cost) to enable
similarity search across the codebase.

Key Features:
- In-memory vector store for fast similarity search
- Local HuggingFace embeddings (all-MiniLM-L6-v2) - FREE
- Fallback to keyword search if embeddings unavailable
- Integration with code intelligence for AST analysis

Architecture:
    Source Files → Chunking → Embedding → Vector Store
                                              ↓
                         Query → Similar Chunks Retrieved

Environment Variables:

- DOCKAI_EMBEDDING_MODEL: HuggingFace model name (default: all-MiniLM-L6-v2)
"""

import os
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Any

import numpy as np
from sentence_transformers import SentenceTransformer

from .code_intelligence import analyze_file, FileAnalysis

logger = logging.getLogger("dockai")


@dataclass
class FileChunk:
    """
    Represents a chunk of a file for embedding and retrieval.
    
    Files are split into overlapping chunks to enable semantic search
    while maintaining context around matched content.
    
    Attributes:
        file_path: Relative path to the source file.
        content: Text content of the chunk.
        start_line: Starting line number (1-indexed).
        end_line: Ending line number (1-indexed).
        chunk_type: Type of chunk ("full", "chunk", "function", "class").
        metadata: Additional metadata for ranking.
    """
    file_path: str
    content: str
    start_line: int
    end_line: int
    chunk_type: str = "chunk"
    metadata: Dict = field(default_factory=dict)


class ProjectIndex:
    """
    Persistent semantic index using in-memory embeddings.
    
    The index combines:
    1. In-memory vector store for fast semantic search
    2. AST analysis for code understanding
    
    Attributes:
        use_embeddings: Whether to use semantic embeddings.
        code_analysis: Dictionary mapping file paths to their AST analysis.
    """
    
    def __init__(self, use_embeddings: bool = True):
        self.use_embeddings = use_embeddings
        self.code_analysis: Dict[str, FileAnalysis] = {}
        self.chunks: List[FileChunk] = []
        self.chunk_embeddings: Optional[np.ndarray] = None
        
        self._model_name = os.getenv("DOCKAI_EMBEDDING_MODEL", "all-MiniLM-L6-v2")
        
        # Initialize embedding model immediately since it's a core dependency
        if use_embeddings:
            try:
                # Suppress HuggingFace tokenizers fork warning
                # This warning appears because we fork Docker processes after loading the model
                # Setting this to "false" prevents warnings without affecting functionality
                os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
                
                self.embedder = SentenceTransformer(self._model_name)
                logger.info(f"Loaded local embedding model: {self._model_name}")
            except Exception as e:
                logger.warning(f"Could not load embedding model: {e}. Falling back to keyword search.")
                self.use_embeddings = False
                self.embedder = None
        else:
            self.embedder = None
    
    def index_project(
        self, 
        root_path: str, 
        file_tree: List[str],
        chunk_size: int = 400,
        chunk_overlap: int = 50
    ) -> None:
        """
        Index all files in the project.
        
        This method:
        1. Reads all files
        2. Performs AST analysis on supported files
        3. Splits files into chunks
        4. Creates embeddings for all chunks
        
        Args:
            root_path: Absolute path to project root.
            file_tree: List of relative file paths to index.
            chunk_size: Target number of lines per chunk.
            chunk_overlap: Number of overlapping lines between chunks.
        """
        logger.info(f"Indexing {len(file_tree)} files for semantic search...")
        
        files_indexed = 0
        
        for rel_path in file_tree:
            abs_path = os.path.join(root_path, rel_path)
            
            try:
                with open(abs_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                
                # Skip empty files
                if not content.strip():
                    continue
                
                # AST Analysis for code files
                analysis = analyze_file(rel_path, content)
                if analysis:
                    self.code_analysis[rel_path] = analysis
                
                # Chunk the file for embedding
                self._chunk_file(rel_path, content, chunk_size, chunk_overlap)
                files_indexed += 1
                
            except Exception as e:
                logger.debug(f"Could not index {rel_path}: {e}")
        
        logger.info(f"Indexed {files_indexed} files into {len(self.chunks)} chunks")
        
        # Build embeddings for all chunks
        if self.use_embeddings and self.chunks and self.embedder:
            self._build_embeddings()
    
    def _chunk_file(
        self, 
        path: str, 
        content: str, 
        chunk_size: int,
        chunk_overlap: int
    ) -> None:
        """
        Split a file into overlapping chunks for embedding.
        
        Small files are stored as single chunks. Large files are split
        with overlap to maintain context across chunk boundaries.
        
        Args:
            path: Relative file path.
            content: File content.
            chunk_size: Target lines per chunk.
            chunk_overlap: Overlap lines between chunks.
        """
        lines = content.split('\n')
        total_lines = len(lines)
        
        # Determine file importance for metadata
        is_config = self._is_config_file(path)
        is_dependency = self._is_dependency_file(path)
        is_dockerfile = 'dockerfile' in path.lower()
        
        metadata = {
            "is_config": is_config,
            "is_dependency": is_dependency,
            "is_dockerfile": is_dockerfile,
        }
        
        # Small files: store as single chunk (prioritize these files)
        if total_lines <= chunk_size:
            self.chunks.append(FileChunk(
                file_path=path,
                content=content,
                start_line=1,
                end_line=total_lines,
                chunk_type="full",
                metadata=metadata
            ))
            return
        
        # Large files: split into overlapping chunks
        step = max(1, chunk_size - chunk_overlap)
        for i in range(0, total_lines, step):
            end = min(i + chunk_size, total_lines)
            chunk_lines = lines[i:end]
            chunk_content = '\n'.join(chunk_lines)
            
            # Skip near-empty chunks
            if len(chunk_content.strip()) < 50:
                continue
            
            self.chunks.append(FileChunk(
                file_path=path,
                content=chunk_content,
                start_line=i + 1,
                end_line=end,
                chunk_type="chunk",
                metadata=metadata
            ))
            
            # Stop if we've reached the end
            if end >= total_lines:
                break
    
    def _is_config_file(self, path: str) -> bool:
        """Check if a file is a configuration file."""
        config_patterns = [
            'config', 'settings', '.env', '.yml', '.yaml', '.toml',
            '.json', '.ini', '.cfg', 'makefile'
        ]
        path_lower = path.lower()
        return any(p in path_lower for p in config_patterns)
    
    def _is_dependency_file(self, path: str) -> bool:
        """Check if a file is a dependency manifest."""
        dep_files = [
            'package.json', 'requirements.txt', 'pyproject.toml',
            'go.mod', 'cargo.toml', 'gemfile', 'pom.xml', 'build.gradle',
            'composer.json', 'setup.py', 'setup.cfg'
        ]
        return os.path.basename(path).lower() in [f.lower() for f in dep_files]
    
    def _build_embeddings(self) -> None:
        """Build and store embeddings in memory."""
        if not self.use_embeddings or not self.chunks or not self.embedder:
            return

        logger.info(f"Processing {len(self.chunks)} chunks for semantic index...")
        
        documents = [chunk.content for chunk in self.chunks]
        
        try:
            # Generate embeddings for all documents at once
            # SentenceTransformers handles batching internally
            # Disable progress bar to use our own logging
            embeddings = self.embedder.encode(
                documents, 
                convert_to_numpy=True,
                show_progress_bar=False
            )
            
            # Normalize embeddings for cosine similarity
            norm = np.linalg.norm(embeddings, axis=1, keepdims=True)
            self.chunk_embeddings = embeddings / norm
            
            logger.info(f"Successfully generated embeddings for {len(documents)} chunks")
        except Exception as e:
            logger.error(f"Failed to generate embeddings: {e}")
            self.use_embeddings = False
            self.chunk_embeddings = None

    def search(self, query: str, top_k: int = 10) -> List[FileChunk]:
        """
        Search for chunks most relevant to the query.
        """
        if not self.chunks:
            return []
        
        if self.use_embeddings:
            return self._semantic_search(query, top_k)
        else:
            return self._keyword_search(query, top_k)
    
    def _semantic_search(self, query: str, top_k: int) -> List[FileChunk]:
        """Perform semantic similarity search using in-memory cosine similarity."""
        if self.chunk_embeddings is None or not self.chunks:
            return []
            
        try:
            # Embed the query (disable progress bar for single query)
            query_embedding = self.embedder.encode(
                [query], 
                convert_to_numpy=True,
                show_progress_bar=False
            )
            
            # Normalize query embedding
            query_norm = np.linalg.norm(query_embedding, axis=1, keepdims=True)
            query_embedding = query_embedding / query_norm
            
            # Calculate cosine similarity (dot product of normalized vectors)
            # shape: (1, embedding_dim) x (num_chunks, embedding_dim).T -> (1, num_chunks)
            scores = np.dot(query_embedding, self.chunk_embeddings.T)[0]
            
            # Get top k indices
            top_indices = np.argsort(scores)[-top_k:][::-1]
            
            # Retrieve chunks
            retrieved_chunks = []
            for idx in top_indices:
                # Optional: Filter out low relevance scores (e.g. < 0.3) if needed
                if scores[idx] > 0.0:  # Just keeping all positive matches for now
                     retrieved_chunks.append(self.chunks[idx])
            
            return retrieved_chunks
            
        except Exception as e:
            logger.error(f"Semantic search failed: {e}")
            return []
    
    def _keyword_search(self, query: str, top_k: int) -> List[FileChunk]:
        """Fallback keyword-based search."""
        query_words = set(query.lower().split())
        scored = []
        
        for chunk in self.chunks:
            chunk_words = set(chunk.content.lower().split())
            
            # Calculate overlap score
            score = len(query_words & chunk_words)
            
            # Boost for important files
            if chunk.metadata.get("is_dependency"):
                score *= 1.3
            if chunk.metadata.get("is_dockerfile"):
                score *= 1.5
            if chunk.metadata.get("is_config"):
                score *= 1.1
            
            if score > 0:
                scored.append((score, chunk))
        
        # Sort by score descending
        scored.sort(reverse=True, key=lambda x: x[0])
        
        return [chunk for _, chunk in scored[:top_k]]
    
    def get_entry_points(self) -> List[str]:
        """Get all detected entry points from AST analysis."""
        entry_points = []
        for analysis in self.code_analysis.values():
            entry_points.extend(analysis.entry_points)
        return entry_points
    
    def get_all_env_vars(self) -> List[str]:
        """Get all detected environment variables from AST analysis."""
        env_vars = set()
        for analysis in self.code_analysis.values():
            env_vars.update(analysis.env_vars)
        return list(env_vars)
    
    def get_all_ports(self) -> List[int]:
        """Get all detected ports from AST analysis."""
        ports = set()
        for analysis in self.code_analysis.values():
            ports.update(analysis.exposed_ports)
        return list(ports)
    
    def get_frameworks(self) -> List[str]:
        """Get all detected frameworks from AST analysis."""
        frameworks = set()
        for analysis in self.code_analysis.values():
            frameworks.update(analysis.framework_hints)
        return list(frameworks)
    
    def get_stats(self) -> Dict:
        """Get indexing statistics."""
        return {
            "total_chunks": len(self.chunks),
            "total_files_analyzed": len(self.code_analysis),
            "embeddings_available": self.chunk_embeddings is not None,
            "embedding_model": self._model_name if self.use_embeddings else None,
            "entry_points": len(self.get_entry_points()),
            "env_vars_detected": len(self.get_all_env_vars()),
            "ports_detected": len(self.get_all_ports()),
            "frameworks_detected": self.get_frameworks(),
        }
