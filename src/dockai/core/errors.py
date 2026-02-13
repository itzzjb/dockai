"""
DockAI Error Classification System.

This module provides AI-powered error classification to distinguish between:
1.  **PROJECT_ERROR**: Developer-side issues that cannot be fixed by regenerating the Dockerfile
    (e.g., missing lock files, invalid code, missing dependencies).
2.  **DOCKERFILE_ERROR**: Issues with the generated Dockerfile that can potentially be fixed by retry
    (e.g., wrong base image, incorrect commands, build failures).
3.  **ENVIRONMENT_ERROR**: Issues with the local environment (Docker not running, network issues).

The classification is done dynamically using AI, making it work for any programming language.
"""

import os
import logging
from enum import Enum
from dataclasses import dataclass
from typing import Optional, Literal, TYPE_CHECKING
from pydantic import BaseModel, Field

# Type checking imports (avoid circular imports)
if TYPE_CHECKING:
    from .agent_context import AgentContext

# Initialize logger for the 'dockai' namespace
logger = logging.getLogger("dockai")


class ErrorType(Enum):
    """
    Enumeration of possible error types for classification.
    
    Attributes:
        PROJECT_ERROR: Issues inherent to the user's project code or configuration.
        DOCKERFILE_ERROR: Issues within the generated Dockerfile that can be corrected.
        ENVIRONMENT_ERROR: Issues with the host system or Docker daemon.
        UNKNOWN_ERROR: Fallback for unclassifiable errors.
    """
    PROJECT_ERROR = "project_error"       # Developer must fix - no retry
    DOCKERFILE_ERROR = "dockerfile_error"  # Can be fixed by retry
    ENVIRONMENT_ERROR = "environment_error"  # Local setup issue - no retry
    UNKNOWN_ERROR = "unknown_error"        # Default - attempt retry


class ErrorAnalysisResult(BaseModel):
    """
    Structured output model for the AI error analysis.
    
    This schema defines the fields that the LLM must populate when analyzing an error.
    It ensures that the output is machine-readable and contains all necessary
    information for decision making.
    """
    error_type: Literal["project_error", "dockerfile_error", "environment_error", "unknown_error"] = Field(
        description="Classification of the error: 'project_error' for issues the developer must fix in their code/config, 'dockerfile_error' for issues that can be fixed by regenerating the Dockerfile, 'environment_error' for local Docker/system issues, 'unknown_error' if unclear"
    )
    problem_summary: str = Field(
        description="A clear, one-sentence summary of what went wrong"
    )
    root_cause: str = Field(
        description="The underlying cause of the error"
    )
    suggestion: str = Field(
        description="Actionable steps the user should take to fix this issue. Include exact commands if applicable."
    )
    can_retry: bool = Field(
        description="True if regenerating the Dockerfile might fix this, False if the user must take action first"
    )
    thought_process: str = Field(
        description="Step-by-step reasoning about the error classification"
    )
    # New fields for smarter recovery
    dockerfile_fix: Optional[str] = Field(
        default=None,
        description="If this is a Dockerfile error, provide the specific fix to apply (e.g., 'use standard image for build stage', 'add apt-get install libcap2-bin')"
    )
    image_suggestion: Optional[str] = Field(
        default=None,
        description="If the error is related to missing dependencies in the image, suggest a better base image (e.g., use standard/full variant for build stage instead of slim/alpine to get system packages)"
    )
    readiness_fix: Optional[str] = Field(
        default=None,
        description="If the error is a readiness timeout or failure, suggest a better regex pattern to detect successful startup (e.g., 'server started at port' instead of 'listening')"
    )


@dataclass
class ClassifiedError:
    """
    Internal representation of a classified error.
    
    This dataclass holds the result of the error analysis in a format that is
    easy to pass around within the application.
    """
    error_type: ErrorType
    message: str
    suggestion: str
    original_error: str
    should_retry: bool
    dockerfile_fix: Optional[str] = None  # Specific fix for Dockerfile issues
    image_suggestion: Optional[str] = None  # Better image to use
    readiness_fix: Optional[str] = None # Better readiness pattern
    
    def to_dict(self):
        """Converts the object to a dictionary for serialization."""
        return {
            "error_type": self.error_type.value,
            "message": self.message,
            "suggestion": self.suggestion,
            "original_error": self.original_error,
            "should_retry": self.should_retry,
            "dockerfile_fix": self.dockerfile_fix,
            "image_suggestion": self.image_suggestion,
            "readiness_fix": self.readiness_fix
        }


def analyze_error_with_ai(context: 'AgentContext') -> ClassifiedError:
    """
    Uses AI to analyze and classify an error message.
    
    This function invokes an LLM to understand the context of an error, regardless
    of the programming language or framework involved. It maps the raw error
    message to a structured `ClassifiedError` object.
    
    Args:
        context (AgentContext): Unified context containing error_message, container_logs,
            analysis_result (for stack info), and other relevant information.
        
    Returns:
        ClassifiedError: An object containing the error type, summary, and suggested fix.
    """
    # Import locally to avoid circular dependencies if any
    from langchain_core.prompts import ChatPromptTemplate
    from ..utils.callbacks import TokenUsageCallback
    from ..utils.prompts import get_prompt
    from .llm_providers import create_llm
    from .agent_context import AgentContext
    
    # Extract values from context
    error_message = context.error_message or ""
    logs = context.container_logs or ""
    stack = context.analysis_result.get("stack", "") if context.analysis_result else ""
    
    try:
        # Create LLM using the provider factory for the error analyzer agent
        llm = create_llm(agent_name="error_analyzer", temperature=0)
        
        # Configure structured output
        structured_llm = llm.with_structured_output(ErrorAnalysisResult)
        
        # Define the default system prompt for the "DevOps Engineer" persona
        default_prompt = """You are an autonomous AI reasoning agent. Your task is to analyze an error and determine what went wrong and whether it can be automatically fixed.

Think like a troubleshooter - examine the evidence, classify the problem, and recommend the right course of action.

## Your Analysis Process

STEP 1 - EXAMINE THE ERROR:
  - What does the error message say?
  - At what stage did this fail (build, runtime, startup)?
  - What was the system trying to do when it failed?

STEP 2 - CLASSIFY THE ERROR:

  **PROJECT_ERROR** - Problems in the user's code/configuration that they must fix:
  - Missing lock files or required project files
  - Syntax errors or bugs in source code
  - Missing dependencies that should be declared
  - Invalid configuration files
  - Code that won't compile due to source issues
  - These CANNOT be fixed by regenerating the Dockerfile
  
  **DOCKERFILE_ERROR** - Problems in the generated Dockerfile that can be fixed by retry:
  - Wrong base image or tag selection
  - Missing system packages needed for build/runtime
  - Incorrect build or run commands
  - Missing COPY instructions for source files
  - Permission issues fixable with chmod/chown
  - Binary compatibility issues between stages
  - These CAN be fixed by regenerating with lessons learned
  
  **ENVIRONMENT_ERROR** - Problems with the local system:
  - Docker daemon not running
  - Network issues (can't pull images)
  - Disk space or memory issues
  - These CANNOT be fixed by regenerating

STEP 3 - DETERMINE ACTIONABILITY:
  - Can regenerating the Dockerfile fix this?
  - What specific change would fix it?
  - Should a different base image be used?
  - Should the readiness pattern be adjusted?

STEP 4 - PROVIDE GUIDANCE:
  - For PROJECT_ERROR: Tell user exactly what to fix and how
  - For DOCKERFILE_ERROR: Specify the dockerfile_fix to apply
  - For ENVIRONMENT_ERROR: Explain the system issue to resolve

## CRITICAL: Warnings vs Errors

**IMPORTANT: Deprecation warnings are NOT errors!**

When analyzing build logs, you MUST distinguish between:
- **Warnings** (informational, don't cause failure): deprecated, WARN, warning, notice
- **Errors** (actual failures): ERR!, error:, fatal:, exit code != 0

**Package manager deprecation warnings ARE NOT ERRORS:**
```
<pkg-manager> warn deprecated package@1.0.0
DEPRECATION: package X is no longer supported
warning: feature Y is deprecated
```
These are HARMLESS warnings about packages/tools that might need updating.
They do NOT cause the build to fail and do NOT require any action.
DO NOT classify deprecation warnings as PROJECT_ERROR or DOCKERFILE_ERROR.

If you see deprecation warnings but the build/run actually succeeded (exit code 0),
the operation was SUCCESSFUL. Only look for ACTUAL errors.

## Special Cases

**Source file not found in container**: 
  This is ALWAYS a DOCKERFILE_ERROR - the file exists, it just wasn't copied.
  dockerfile_fix must include adding the proper COPY instruction.

**Missing module/package at runtime in multi-stage builds**:
  If the error says a module/package is not found (e.g., "ModuleNotFoundError: No module named 'flask'",
  "Cannot find module 'express'", "Error: Cannot find module") but the dependency IS declared in the
  project's dependency file (requirements.txt, package.json, Gemfile, etc.):
  - This is ALWAYS a DOCKERFILE_ERROR, NOT a PROJECT_ERROR.
  - The packages were installed in the builder stage (e.g., into /usr/local/lib/python3.x/site-packages)
    but only /app was copied to the runtime stage, so installed packages are missing.
  - dockerfile_fix: "Copy installed packages from builder to runtime stage (e.g., COPY --from=builder
    /usr/local/lib/python3.x/site-packages /usr/local/lib/python3.x/site-packages and
    COPY --from=builder /usr/local/bin /usr/local/bin), or install dependencies directly in runtime stage,
    or use a virtualenv in the builder and copy it to runtime."
  - NEVER tell the user to add a dependency that is already in their dependency file.

**Binary not found / executable missing**:
  Usually a binary compatibility issue between build and runtime stages.
  Consider static linking or compatible base images.

**Readiness timeout / startup pattern not detected**:
  The app started but the log pattern wasn't found.
  Look at actual logs to suggest a better readiness_fix regex pattern.

**Deprecation warnings (ANY language)**:
  Deprecation warnings are HARMLESS, NOT errors. They appear as:
  "deprecated", "DEPRECATION:", "will be removed", "no longer supported"
  DO NOT treat these as errors. Look for actual error messages instead.

**Security audit tool failures**:
  Commands like `<pkg-manager> audit` exit non-zero when there are unfixable vulnerabilities.
  This is a DOCKERFILE_ERROR. The fix is to REMOVE the audit command from the Dockerfile.
  Legacy projects often have vulnerabilities that cannot be auto-fixed.
  The dockerfile_fix should be: "Remove the audit command from the RUN instruction"

**Truncated / Missing Logs**:
  If the error says "logs were truncated" or "no explicit error message":
  - Assume this IS a DOCKERFILE_ERROR (e.g., build crashed or apt failed silently).
  - Set should_retry = True.
  - Suggest increasing verbosity or checking package names.
  - DO NOT classify as UNKNOWN_ERROR unless you are sure it is not retryable.

## Output Requirements

- Be specific about what file or command needs to be created/run
- For PROJECT_ERROR, include exact steps for the user
- For DOCKERFILE_ERROR, always populate dockerfile_fix
- If image change needed, populate image_suggestion
- If readiness pattern wrong, populate readiness_fix
"""

        # Get custom prompt if configured, otherwise use default
        system_prompt = get_prompt("error_analyzer", default_prompt)

        # Create the chat prompt template
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("user", """Analyze this error and classify it:

Technology Stack: {stack}

Error Message:
{error_message}

Container/Build Logs:
{logs}

Classify this error and provide guidance.""")
        ])
        
        # Create the execution chain: Prompt -> LLM -> Structured Output
        chain = prompt | structured_llm
        
        # Initialize callback to track token usage
        callback = TokenUsageCallback()
        
        # Execute the chain
        result = chain.invoke(
            {
                "stack": stack or "Unknown",
                "error_message": error_message[:5000],  # Increase limit to capture more context
                "logs": logs[-10000:] if logs else "No additional logs"  # Take the TAIL of the logs (last 10000 chars) where errors usually are
            },
            config={"callbacks": [callback]}
        )
        
        # Log token usage for debugging
        usage = callback.get_usage()
        logger.debug(f"Error analysis used {usage.get('total_tokens', 0)} tokens")
        
        # Map the string result to the ErrorType enum
        error_type_map = {
            "project_error": ErrorType.PROJECT_ERROR,
            "dockerfile_error": ErrorType.DOCKERFILE_ERROR,
            "environment_error": ErrorType.ENVIRONMENT_ERROR,
            "unknown_error": ErrorType.UNKNOWN_ERROR
        }
        
        error_type = error_type_map.get(result.error_type, ErrorType.UNKNOWN_ERROR)
        
        logger.debug(f"AI Error Analysis: {result.thought_process}")
        
        return ClassifiedError(
            error_type=error_type,
            message=result.problem_summary,
            suggestion=result.suggestion,
            original_error=error_message[:500],
            should_retry=result.can_retry,
            dockerfile_fix=result.dockerfile_fix,
            image_suggestion=result.image_suggestion,
            readiness_fix=result.readiness_fix
        )
        
    except Exception as e:
        logger.error(f"Problem: AI error analysis failed - {e}")
        # Fallback to unknown error if AI analysis fails
        return ClassifiedError(
            error_type=ErrorType.UNKNOWN_ERROR,
            message="Error analysis failed - see details below",
            suggestion="Check the error details and logs. If the issue persists, please report it.",
            original_error=error_message[:500],
            should_retry=True
        )


def classify_error(context: 'AgentContext') -> ClassifiedError:
    """
    Public entry point to classify an error using AI.
    
    This function checks for necessary configuration (API key) before delegating
    to the AI analysis function. Supports multiple LLM providers.
    
    Args:
        context (AgentContext): Unified context containing error_message, container_logs,
            and analysis_result (for stack info).
        
    Returns:
        ClassifiedError: The classified error object.
    """
    # Check if any LLM provider API key is configured
    # Import locally to avoid circular dependencies
    from .llm_providers import get_provider_info, get_llm_config
    from .agent_context import AgentContext
    
    config = get_llm_config()
    provider_info = get_provider_info()
    
    # Check if the default provider has credentials configured
    # This supports all providers including Ollama which might not need an API key
    is_configured = provider_info["credentials_configured"].get(config.default_provider.value, False)
    
    error_message = context.error_message or ""
    
    if not is_configured:
        logger.error(f"Problem: {config.default_provider.value.upper()} is not fully configured - cannot analyze error")
        return ClassifiedError(
            error_type=ErrorType.UNKNOWN_ERROR,
            message="Cannot analyze error - LLM provider not configured",
            suggestion=f"Set the required environment variables for {config.default_provider.value} in your .env file",
            original_error=error_message[:500],
            should_retry=True
        )
    
    return analyze_error_with_ai(context)


def format_error_for_display(classified_error: ClassifiedError, verbose: bool = False) -> str:
    """
    Formats a classified error for user-friendly display in the CLI.
    
    Args:
        classified_error (ClassifiedError): The classified error object to format.
        verbose (bool, optional): Whether to include the full original error message. Defaults to False.
        
    Returns:
        str: A formatted string ready for printing to the console.
    """
    error_type_display = {
        ErrorType.PROJECT_ERROR: "[PROJECT ERROR] Fix Required",
        ErrorType.DOCKERFILE_ERROR: "[DOCKERFILE ERROR] Retrying...",
        ErrorType.ENVIRONMENT_ERROR: "[ENVIRONMENT ERROR]",
        ErrorType.UNKNOWN_ERROR: "[UNKNOWN ERROR]"
    }
    
    lines = [
        f"\n{'='*60}",
        f"{error_type_display.get(classified_error.error_type, 'Error')}",
        f"{'='*60}",
        f"\nProblem: {classified_error.message}",
        f"\nSolution: {classified_error.suggestion}",
    ]
    
    if verbose and classified_error.original_error:
        lines.extend([
            f"\nDetails:",
            f"   {classified_error.original_error[:300]}..."
        ])
    
    if not classified_error.should_retry:
        lines.append(f"\nThis error cannot be fixed by retrying. Please fix the issue and try again.")
    
    lines.append(f"{'='*60}\n")
    
    return "\n".join(lines)
