"""
DockAI Main Entry Point.

This module serves as the command-line interface (CLI) entry point for the DockAI application.
It handles argument parsing, environment validation, logging configuration, and the initialization
of the main agent workflow.
"""

import os
import sys
import logging
import warnings

# Suppress Pydantic V1 compatibility warning with Python 3.14+
warnings.filterwarnings("ignore", message=".*Pydantic V1.*Python 3.14.*")

import typer
from dotenv import load_dotenv

from ..workflow.graph import create_graph
from . import ui
from ..utils.prompts import load_prompts, set_prompt_config
from ..utils.tracing import init_tracing, shutdown_tracing, record_workflow_start, record_workflow_end

# Load environment variables from .env file
load_dotenv()

# Initialize Typer application with Rich markup support
# We use a callback with explicit invoke_without_command handling to ensure 'build' appears as a subcommand
app = typer.Typer(
    rich_markup_mode="rich",
    help="[bold blue]DockAI[/bold blue] - The Customizable AI Dockerfile Generation Framework",
    no_args_is_help=True,
    add_completion=True
)

# Add a version command to make this a multi-command app (so 'build' shows as subcommand)
@app.command("version", hidden=True)
def version():
    """Show version information."""
    from .. import __version__
    typer.echo(f"DockAI v{__version__}")

# Configure logging using the centralized setup from the UI module
logger = ui.setup_logging()

def load_instructions(path: str):
    """
    Loads custom instructions and prompts for the AI agent from various sources.

    Instructions and prompts can be provided via:
    1. Environment variables (DOCKAI_*_INSTRUCTIONS, DOCKAI_PROMPT_*)
    2. A local `.dockai` file in the target directory.

    The `.dockai` file supports sections:
    - [analyzer], [generator] - Legacy sections for backward compatibility
    - [instructions_*] - Extra instructions appended to default prompts
    - [prompt_*] - Complete prompt replacements

    Args:
        path (str): The absolute path to the target directory where `.dockai` might exist.

    Returns:
        PromptConfig: The merged prompt configuration loaded from environment variables
            and the .dockai file.
    """
    # Load and set custom prompts and instructions configuration
    # This handles all 8 prompts and their instructions from env vars and .dockai file
    prompt_config = load_prompts(path)
    set_prompt_config(prompt_config)
    logger.debug("Custom prompts and instructions configuration loaded")
    
    # Return prompt configuration directly
    return prompt_config

@app.command("build")
def build(
    path: str = typer.Argument(..., help="Path to the repository to analyze"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose debug logging"),
    no_cache: bool = typer.Option(False, "--no-cache", help="Disable Docker build cache")
):
    """
    Build a Dockerfile for a project using AI analysis.
    
    Analyzes the target repository, generates an optimized Dockerfile,
    validates it against best practices, and saves it to the project directory.
    """
    if verbose:
        logger.setLevel(logging.DEBUG)
        logger.debug("Verbose mode enabled")
    
    # Initialize OpenTelemetry tracing (if enabled via DOCKAI_ENABLE_TRACING)
    init_tracing(service_name="dockai")
    
    # Check for LangSmith tracing
    if os.getenv("LANGCHAIN_TRACING_V2", "false").lower() == "true":
        logger.info("LangSmith tracing enabled")
    
    # Note: no_cache flag is passed through config to validator.py which adds --no-cache to docker build
    
    # Validate input path existence
    if not os.path.exists(path):
        ui.print_error("Path Error", f"Path '{path}' does not exist.")
        logger.error(f"Problem: Path '{path}' does not exist.")
        raise typer.Exit(code=1)
    
    # Import and initialize LLM provider configuration
    from ..core.llm_providers import get_llm_config, load_llm_config_from_env, set_llm_config, log_provider_info, LLMProvider
    
    # Load LLM configuration from environment
    llm_config = load_llm_config_from_env()
    set_llm_config(llm_config)
    
    # Validate API key configuration based on provider
    if llm_config.default_provider == LLMProvider.OPENAI:
        if not os.getenv("OPENAI_API_KEY"):
            ui.print_error("Configuration Error", "OPENAI_API_KEY not found in environment variables.", 
                          "Please create a .env file with your API key or set the OPENAI_API_KEY environment variable.")
            logger.error("Problem: OPENAI_API_KEY missing")
            raise typer.Exit(code=1)
    elif llm_config.default_provider == LLMProvider.AZURE:
        if not os.getenv("AZURE_OPENAI_API_KEY"):
            ui.print_error("Configuration Error", "AZURE_OPENAI_API_KEY not found in environment variables.",
                          "Please set AZURE_OPENAI_API_KEY and AZURE_OPENAI_ENDPOINT environment variables.")
            logger.error("Problem: AZURE_OPENAI_API_KEY missing")
            raise typer.Exit(code=1)
        if not llm_config.azure_endpoint:
            ui.print_error("Configuration Error", "AZURE_OPENAI_ENDPOINT not found in environment variables.",
                          "Please set the AZURE_OPENAI_ENDPOINT environment variable.")
            logger.error("Problem: AZURE_OPENAI_ENDPOINT missing")
            raise typer.Exit(code=1)
    elif llm_config.default_provider == LLMProvider.GEMINI:
        if not os.getenv("GOOGLE_API_KEY"):
            ui.print_error("Configuration Error", "GOOGLE_API_KEY not found in environment variables.",
                          "Please set the GOOGLE_API_KEY environment variable.")
            logger.error("Problem: GOOGLE_API_KEY missing")
            raise typer.Exit(code=1)
    elif llm_config.default_provider == LLMProvider.ANTHROPIC:
        if not os.getenv("ANTHROPIC_API_KEY"):
            ui.print_error("Configuration Error", "ANTHROPIC_API_KEY not found in environment variables.",
                          "Please set the ANTHROPIC_API_KEY environment variable.")
            logger.error("Problem: ANTHROPIC_API_KEY missing")
            raise typer.Exit(code=1)
    
    # Log LLM provider and model configuration
    log_provider_info()

    ui.print_welcome()
    logger.info(f"Starting analysis for: {path}")

    # Check if Dockerfile exists and warn
    output_path = os.path.join(path, "Dockerfile")
    if os.path.exists(output_path):
        logger.warning(f"Dockerfile already exists at {output_path}. It will be overwritten.")


    # Load custom instructions
    prompt_config = load_instructions(path)
    
    # Initialize the workflow state with all necessary fields
    initial_state = {
        "path": os.path.abspath(path),
        "file_tree": [],
        "analysis_result": {},
        "file_contents": "",
        "dockerfile_content": "",
        "previous_dockerfile": None,  # For iterative improvement
        "validation_result": {"success": False, "message": ""},
        "retry_count": 0,
        "max_retries": int(os.getenv("MAX_RETRIES", "3")),
        "error": None,
        "error_details": None,
        "logs": [],
        "usage_stats": [],
        "config": {
            "analyzer_instructions": prompt_config.analyzer_instructions or "",
            "blueprint_instructions": prompt_config.blueprint_instructions or "",
            "generator_instructions": prompt_config.generator_instructions or "",
            "reviewer_instructions": prompt_config.reviewer_instructions or "",
            "reflector_instructions": prompt_config.reflector_instructions or "",
            "error_analyzer_instructions": prompt_config.error_analyzer_instructions or "",
            "iterative_improver_instructions": prompt_config.iterative_improver_instructions or "",
            "no_cache": no_cache
        },
        # Adaptive agent fields for learning and planning
        "retry_history": [],  # Full history of attempts for learning
        "current_plan": None,  # AI-generated strategic plan
        "reflection": None,  # AI reflection on failures
        "detected_health_endpoint": None,  # AI-detected from file contents
        "readiness_patterns": [],  # AI-detected startup log patterns
        "failure_patterns": [],  # AI-detected failure log patterns
        "needs_reanalysis": False,  # Flag to trigger re-analysis
        "best_dockerfile": None  # Stores the best functional Dockerfile (e.g. built but had lint errors) from previous attempts
    }

    # Create and compile the LangGraph workflow
    workflow = create_graph()
    
    # Record workflow start for tracing
    record_workflow_start(path, {"max_retries": initial_state["max_retries"]})
    
    try:
        # Execute the workflow with a visual spinner
        with ui.get_status_spinner("[bold green]Running DockAI Framework...[/bold green]"):
            # Prepare configuration for LangGraph/LangSmith
            invoke_config = {
                "metadata": {
                    "project_path": path,
                    "verbose": verbose,
                    "no_cache": no_cache,
                    "max_retries": initial_state["max_retries"]
                }
            }
            final_state = workflow.invoke(initial_state, config=invoke_config)
    except KeyboardInterrupt:
        # Handle user interruption gracefully
        ui.print_error("Cancelled", "Operation cancelled by user.")
        logger.info("User interrupted the operation")
        raise typer.Exit(code=130)
    except PermissionError as e:
        # Handle Docker permission issues
        ui.print_error(
            "Permission Error",
            "Unable to access Docker daemon. This usually means your user doesn't have permission to run Docker.",
            "Try running: sudo usermod -aG docker $USER\\nThen log out and back in, or use: sudo dockai build ."
        )
        logger.error(f"Docker permission error: {e}")
        raise typer.Exit(code=1)
    except ConnectionError as e:
        # Handle network/Docker connection issues
        ui.print_error(
            "Connection Error",
            "Failed to connect to required services (Docker daemon or LLM API).",
            "Ensure Docker is running: docker ps\\nCheck your internet connection and API credentials."
        )
        logger.error(f"Connection error: {e}")
        if verbose:
            logger.exception("Connection error details")
        raise typer.Exit(code=1)
    except TimeoutError as e:
        # Handle timeout errors
        ui.print_error(
            "Timeout Error",
            "Operation timed out while waiting for a response.",
            "The Docker build or LLM API call took too long. Try again or increase timeout settings."
        )
        logger.error(f"Timeout error: {e}")
        raise typer.Exit(code=1)
    except MemoryError as e:
        # Handle out of memory errors
        ui.print_error(
            "Memory Error",
            "Ran out of memory while processing the repository.",
            "Try processing a smaller directory or increase available system memory.\\nConsider excluding large directories using .dockerignore."
        )
        logger.error(f"Memory error: {e}")
        raise typer.Exit(code=1)
    except Exception as e:
        # Handle unexpected errors gracefully
        error_msg = str(e)
        error_type = type(e).__name__
        
        # Check for common LangGraph errors like recursion limits
        if "GraphRecursionError" in error_msg or "recursion" in error_msg.lower():
            ui.print_error(
                "Max Retries Exceeded", 
                "The system reached the maximum retry limit while trying to generate a valid Dockerfile.",
                "Check the error details above for specific guidance on how to fix the issue.\\nYou can also increase MAX_RETRIES in .env or run with --verbose for more details."
            )
        # Check for API authentication errors
        elif "authentication" in error_msg.lower() or "unauthorized" in error_msg.lower() or "401" in error_msg:
            ui.print_error(
                "Authentication Error",
                "Failed to authenticate with the LLM API.",
                "Check your API key is correct and has not expired.\\nVerify the key in your .env file or environment variables."
            )
        # Check for rate limiting
        elif "rate limit" in error_msg.lower() or "429" in error_msg:
            ui.print_error(
                "Rate Limit Error",
                "Hit API rate limits. Too many requests to the LLM provider.",
                "Wait a few minutes and try again, or upgrade your API plan for higher limits."
            )
        # Check for model errors
        elif "model" in error_msg.lower() and ("not found" in error_msg.lower() or "does not exist" in error_msg.lower()):
            ui.print_error(
                "Model Not Found",
                "The specified AI model does not exist or is not accessible.",
                "Check the model name in your configuration and ensure you have access to it."
            )
        else:
            ui.print_error(
                f"Unexpected Error ({error_type})", 
                error_msg[:300] if len(error_msg) > 300 else error_msg,
                "Run with --verbose for detailed logs or check the error message above."
            )
            if verbose:
                logger.exception("Unexpected error with full traceback")
        
        raise typer.Exit(code=1)

    # Process and display the final results
    validation_result = final_state["validation_result"]
    output_path = os.path.join(path, "Dockerfile")
    
    # Calculate total tokens for tracing
    total_tokens = sum(
        stat.get("total_tokens", 0) 
        for stat in final_state.get("usage_stats", [])
        if isinstance(stat, dict)
    )
    
    if validation_result["success"]:
        record_workflow_end(True, final_state.get("retry_count", 0), total_tokens)
        shutdown_tracing()
        ui.display_summary(final_state, output_path)
    else:
        record_workflow_end(False, final_state.get("retry_count", 0), total_tokens)
        shutdown_tracing()
        ui.display_failure(final_state)
        raise typer.Exit(code=1)

if __name__ == "__main__":
    app()
