"""
DockAI MCP Server Module.

This module provides a Model Context Protocol (MCP) server implementation
that allows AI tools like Claude Desktop and Cursor to interact with DockAI
functionality directly. It exposes tools for:
- Project analysis
- Dockerfile generation
- Dockerfile validation
- Full agentic workflow execution
"""

import os
import logging
from typing import Optional
from mcp.server.fastmcp import FastMCP

from dockai.utils.scanner import get_file_tree
from dockai.agents.analyzer import analyze_repo_needs
from dockai.agents.generator import generate_dockerfile
from dockai.utils.file_utils import read_critical_files
from dockai.utils.validator import validate_docker_build_and_run
from dockai.core.agent_context import AgentContext

# Initialize logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("dockai-mcp")

# Create MCP Server
mcp = FastMCP("DockAI")

@mcp.tool()
def analyze_project(path: str) -> str:
    """
    Analyzes a local project directory to determine Docker requirements.
    
    Args:
        path: Absolute path to the project directory.
        
    Returns:
        A summary of the detected stack, build commands, and critical files.
    """
    if not os.path.exists(path):
        return f"Error: Path '{path}' does not exist."
        
    logger.info(f"Analyzing project at: {path}")
    file_tree = get_file_tree(path)
    
    # Run analysis with AgentContext
    analyzer_context = AgentContext(file_tree=file_tree)
    analysis_result, _ = analyze_repo_needs(context=analyzer_context)
    
    summary = [
        f"Stack: {analysis_result.stack}",
        f"Project Type: {analysis_result.project_type}",
        f"Build Command: {analysis_result.build_command}",
        f"Start Command: {analysis_result.start_command}",
        f"Suggested Base Image: {analysis_result.suggested_base_image}",
        f"Critical Files: {', '.join(analysis_result.files_to_read)}"
    ]
    
    return "\n".join(summary)

@mcp.tool()
def generate_dockerfile_content(path: str, instructions: Optional[str] = None) -> str:
    """
    Generates a production-ready Dockerfile for the project at the given path.
    Does NOT write to disk, just returns the content.
    
    Args:
        path: Absolute path to the project directory.
        instructions: Optional custom instructions (e.g., "Use Alpine", "Expose port 3000").
        
    Returns:
        The generated Dockerfile content.
    """
    if not os.path.exists(path):
        return f"Error: Path '{path}' does not exist."
        
    logger.info(f"Generating Dockerfile for: {path}")
    
    # 1. Scan
    file_tree = get_file_tree(path)
    
    # 2. Analyze with AgentContext
    analyzer_context = AgentContext(file_tree=file_tree, custom_instructions=instructions or "")
    analysis_result, _ = analyze_repo_needs(context=analyzer_context)
    
    # 3. Read Files
    file_contents = read_critical_files(path, analysis_result.files_to_read)
    
    # 4. Generate with AgentContext
    generator_context = AgentContext(
        file_tree=file_tree,
        file_contents=file_contents,
        analysis_result=analysis_result.model_dump(),
        custom_instructions=instructions or ""
    )
    dockerfile_content, _, thought_process, _ = generate_dockerfile(context=generator_context)
    
    return dockerfile_content

@mcp.tool()
def validate_dockerfile(path: str, dockerfile_content: str) -> str:
    """
    Validates a Dockerfile by building and running it.
    
    Args:
        path: Absolute path to the project directory (build context).
        dockerfile_content: The content of the Dockerfile to test.
        
    Returns:
        Validation result message.
    """
    if not os.path.exists(path):
        return f"Error: Path '{path}' does not exist."
        
    # Write temporary Dockerfile for validation
    temp_dockerfile_path = os.path.join(path, "Dockerfile.dockai_validation")
    with open(temp_dockerfile_path, "w") as f:
        f.write(dockerfile_content)
        
    try:
        # The validator expects a Dockerfile at the project root.
        # Back up any existing Dockerfile before writing the test content.
        real_dockerfile_path = os.path.join(path, "Dockerfile")
        backup_path = None
        if os.path.exists(real_dockerfile_path):
            backup_path = os.path.join(path, "Dockerfile.bak")
            os.rename(real_dockerfile_path, backup_path)
            
        with open(real_dockerfile_path, "w") as f:
            f.write(dockerfile_content)
            
        success, message, _, _ = validate_docker_build_and_run(
            directory=path,
            project_type="service",
            stack="unknown",
            health_endpoint=None,
            recommended_wait_time=5
        )
        
        return f"Validation {'Success' if success else 'Failed'}: {message}"
        
    finally:
        # Restore the original Dockerfile if one was backed up
        if backup_path and os.path.exists(backup_path):
            os.rename(backup_path, real_dockerfile_path)
        elif os.path.exists(real_dockerfile_path):
            # NOTE: Leaves Dockerfile on disk since Docker build requires a file context
            pass

@mcp.tool()
def run_full_workflow(path: str, instructions: Optional[str] = None) -> str:
    """
    Executes the full DockAI agentic workflow (Scan -> Analyze -> Plan -> Generate -> Validate -> Fix).
    This runs the exact same logic as the CLI 'dockai build' command.
    
    It will:
    1. Analyze the project.
    2. Generate a Dockerfile.
    3. Build and validate it.
    4. If validation fails, it will self-reflect and retry (up to 3 times).
    
    Args:
        path: Absolute path to the project directory.
        instructions: Optional custom instructions for the agents.
        
    Returns:
        A summary of the run, including the final Dockerfile content and validation status.
    """
    if not os.path.exists(path):
        return f"Error: Path '{path}' does not exist."
        
    logger.info(f"Running full workflow for: {path}")
    
    # Import here to avoid circular dependencies if any
    from dockai.workflow.graph import create_graph
    
    # Initialize state
    initial_state = {
        "path": path,
        "config": {
            "generator_instructions": instructions or "",
            "analyzer_instructions": instructions or ""
        },
        "retry_count": 0,
        "max_retries": 3,
        "usage_stats": []
    }
    
    # Run the graph
    app = create_graph()
    final_state = app.invoke(initial_state)
    
    # Extract results
    dockerfile = final_state.get("dockerfile_content", "")
    validation = final_state.get("validation_result", {})
    success = validation.get("success", False)
    message = validation.get("message", "No validation message")
    retry_count = final_state.get("retry_count", 0)
    
    result = [
        f"Workflow Completed in {retry_count} attempts.",
        f"Status: {'SUCCESS' if success else 'FAILED'}",
        f"Validation Message: {message}",
        "",
        "--- Final Dockerfile ---",
        dockerfile
    ]
    
    return "\n".join(result)

if __name__ == "__main__":
    mcp.run()
