"""
DockAI Adaptive Agent Graph.

This module implements the core agentic workflow for the DockAI framework.
It defines the state machine that orchestrates the entire Dockerfile generation process,
moving from analysis to planning, generation, validation, and iterative improvement.

Key Workflow Capabilities:
1.  **Strategic Planning**: Plans before generating code.
2.  **Failure Reflection**: Analyzes failures to learn and adapt.
3.  **Smart Iteration**: Makes targeted fixes instead of blind retries.
4.  **Dynamic Routing**: Adapts the workflow based on analysis results (e.g., re-analyzing if assumptions were wrong).
"""

import logging
from typing import Literal
from langgraph.graph import StateGraph, END

from ..core.state import DockAIState
from ..core.errors import ErrorType
from .nodes import (
    scan_node,
    analyze_node,
    read_files_node,
    blueprint_node,
    generate_node,
    review_node,
    validate_node,
    reflect_node,
    increment_retry
)

# Initialize logger for the 'dockai' namespace
logger = logging.getLogger("dockai")


# ==================== CONDITIONAL EDGE FUNCTIONS ====================

def should_retry(state: DockAIState) -> Literal["reflect", "end"]:
    """
    Determines the next step after a validation attempt.
    
    This function acts as a gatekeeper, deciding whether to retry a failed
    build/validation or to terminate the process. It considers the error type,
    retry limits, and whether the error is fixable by the agent.

    Args:
        state (DockAIState): The current state of the workflow.

    Returns:
        Literal["reflect", "end"]: "reflect" to proceed to the reflection phase,
        or "end" to stop the workflow.
    """
    error_details = state.get("error_details")
    
    if error_details:
        error_type = error_details.get("error_type", "")
        should_retry_flag = error_details.get("should_retry", True)
        
        # Don't retry for project errors (user must fix) or environment errors (system issue)
        if error_type in [ErrorType.PROJECT_ERROR.value, ErrorType.ENVIRONMENT_ERROR.value]:
            logger.error(f"Cannot retry: {error_details.get('message', 'Unknown error')}")
            logger.info(f"Solution: {error_details.get('suggestion', 'Check the error and try again')}")
            return "end"
        
        # If the error analysis specifically says not to retry
        if not should_retry_flag:
            logger.error(f"{error_details.get('message', 'Unknown error')}")
            return "end"
    
    # Check if we have reached the maximum number of retries
    validation_result = state.get("validation_result")
    
    # Handle security check failures (which happen before validation result is set)
    if state.get("error") and not validation_result:
        retry_count = state.get("retry_count", 0)
        max_retries = state.get("max_retries", 3)
        if retry_count < max_retries:
            return "reflect"  # Go to reflection before retry
        else:
            logger.error("Max retries reached - security check failed.")
            return "end"

    # Handle validation failures
    if validation_result:
        if validation_result["success"]:
            return "end"  # Success!
        
        retry_count = state.get("retry_count", 0)
        max_retries = state.get("max_retries", 3)
        
        if retry_count < max_retries:
            return "reflect"  # Go to reflection before retry
        
        logger.error("Max retries reached - validation failed.")
        return "end"
        
    return "end"


def check_security(state: DockAIState) -> Literal["validate", "reflect", "end"]:
    """
    Checks the result of the security review node.

    If the security review found critical issues, it routes to reflection/retry.
    Otherwise, it proceeds to the validation phase (building the image).

    Args:
        state (DockAIState): The current state of the workflow.

    Returns:
        Literal["validate", "reflect", "end"]: The next node to execute.
    """
    if state.get("error"):
        retry_count = state.get("retry_count", 0)
        max_retries = state.get("max_retries", 3)
        if retry_count < max_retries:
            return "reflect"  # Go to reflection before retry
        return "end"
    return "validate"


def check_reanalysis(state: DockAIState) -> Literal["analyze", "blueprint", "generate"]:
    """
    Determines the entry point for the next iteration after reflection.
    
    Based on the insights gained during reflection, we might need to:
    - Re-analyze the project (if we misunderstood the stack).
    - Create a new blueprint (if the strategy was wrong).
    - Just regenerate the Dockerfile (if it was a minor syntax/config issue).

    Args:
        state (DockAIState): The current state of the workflow.

    Returns:
        Literal["analyze", "blueprint", "generate"]: The next node to execute.
    """
    needs_reanalysis = state.get("needs_reanalysis", False)
    reflection = state.get("reflection", {})
    
    if needs_reanalysis:
        logger.info("Re-analysis needed based on reflection")
        return "analyze"
    
    # Check if reflection suggests major strategy change
    if reflection:
        if reflection.get("should_change_build_strategy"):
            logger.info("Strategy change needed - creating new blueprint")
            return "blueprint"
    
    # For targeted fixes, go directly to generate
    return "generate"


# ==================== GRAPH CONSTRUCTION ====================

def create_graph():
    """
    Constructs and compiles the DockAI state graph.
    
    The workflow structure:
    
    scan → analyze → read_files → blueprint → generate → review
                                                            ↓
                                                     (check_security)
                                                       ↓        ↓
                                                   validate   END (critical issue)
                                                       ↓
                                                  (should_retry)
                                                  ↓      ↓      ↓
                                              reflect   END   increment_retry → END
                                                  ↓
                                           (check_reanalysis)
                                              ↓          ↓
                                          analyze    blueprint/generate
    
    Returns:
        CompiledGraph: The executable LangGraph workflow.
    """
    workflow = StateGraph(DockAIState)
    
    # Add nodes to the graph
    workflow.add_node("scan", scan_node)
    workflow.add_node("analyze", analyze_node)
    workflow.add_node("read_files", read_files_node)
    workflow.add_node("blueprint", blueprint_node)
    workflow.add_node("generate", generate_node)
    workflow.add_node("review", review_node)
    workflow.add_node("validate", validate_node)
    workflow.add_node("reflect", reflect_node)
    workflow.add_node("increment_retry", increment_retry)
    
    # Set the entry point
    workflow.set_entry_point("scan")
    
    # Define the main linear flow
    workflow.add_edge("scan", "analyze")
    workflow.add_edge("analyze", "read_files")
    workflow.add_edge("read_files", "blueprint")
    workflow.add_edge("blueprint", "generate")
    workflow.add_edge("generate", "review")
    
    # Define conditional routing after security review
    workflow.add_conditional_edges(
        "review",
        check_security,
        {
            "validate": "validate",
            "reflect": "reflect",
            "end": END
        }
    )
    
    # Define conditional routing after validation (build/test)
    workflow.add_conditional_edges(
        "validate",
        should_retry,
        {
            "reflect": "reflect",
            "end": END
        }
    )
    
    # Define the feedback loop
    workflow.add_edge("reflect", "increment_retry")
    
    workflow.add_conditional_edges(
        "increment_retry",
        check_reanalysis,
        {
            "analyze": "analyze",
            "blueprint": "blueprint",
            "generate": "generate"
        }
    )
    
    return workflow.compile()

