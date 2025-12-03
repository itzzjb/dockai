"""
DockAI - The Customizable AI Dockerfile Generation Framework.

This package provides an intelligent, adaptive system for analyzing repositories
and generating optimized, production-ready Dockerfiles using Large Language Models.

The framework is organized into the following submodules:
- core: LLM providers, schemas, state management, and error handling
- agents: AI-powered analyzers, generators, and reviewers
- workflow: LangGraph workflow orchestration
- utils: Utility functions for scanning, validation, prompts, etc.
- cli: Command-line interface and UI components
"""

__version__ = "3.1.2"

# Lazy imports to avoid circular dependencies
# Users can import directly from submodules for specific functionality
