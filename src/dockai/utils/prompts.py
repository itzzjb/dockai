"""
DockAI Custom Prompts Module.

This module provides centralized management of all AI prompts used throughout DockAI.
It supports loading custom prompts and instructions from environment variables, allowing 
users to customize the behavior of each AI agent persona.

Each prompt/instruction can be customized via:
1. Environment variables (DOCKAI_PROMPT_* for full prompts, DOCKAI_*_INSTRUCTIONS for instructions)
2. A `.dockai` file in the project root with [prompt_*] or [instructions_*] sections

Available prompts (complete replacement):
- DOCKAI_PROMPT_ANALYZER: The Build Engineer that analyzes project structure
- DOCKAI_PROMPT_BLUEPRINT: The Chief Architect that plans build strategy and runtime config
- DOCKAI_PROMPT_GENERATOR: The Docker Architect that generates Dockerfiles
- DOCKAI_PROMPT_REVIEWER: The Security Engineer that reviews for vulnerabilities
- DOCKAI_PROMPT_REFLECTOR: The Principal DevOps Engineer that analyzes failures
- DOCKAI_PROMPT_ERROR_ANALYZER: The DevOps Engineer that classifies errors
- DOCKAI_PROMPT_ITERATIVE_IMPROVER: The Senior Docker Engineer that applies fixes

Available instructions (appended to default prompts):
- DOCKAI_ANALYZER_INSTRUCTIONS: Extra instructions for the analyzer
- DOCKAI_BLUEPRINT_INSTRUCTIONS: Extra instructions for the blueprint architect
- DOCKAI_GENERATOR_INSTRUCTIONS: Extra instructions for the generator
- DOCKAI_REVIEWER_INSTRUCTIONS: Extra instructions for security review
- DOCKAI_REFLECTOR_INSTRUCTIONS: Extra instructions for failure reflection
- DOCKAI_ERROR_ANALYZER_INSTRUCTIONS: Extra instructions for error analysis
- DOCKAI_ITERATIVE_IMPROVER_INSTRUCTIONS: Extra instructions for iterative improvement
"""

import os
from typing import Dict, Optional
from dataclasses import dataclass, field


# Environment variable prefixes
PROMPT_ENV_PREFIX = "DOCKAI_PROMPT_"
INSTRUCTIONS_ENV_SUFFIX = "_INSTRUCTIONS"


@dataclass
class PromptConfig:
    """
    Configuration class holding all custom prompts and instructions.
    
    Each field corresponds to a specific AI agent persona in the DockAI workflow.
    If a field is None, the default prompt will be used.
    
    Prompts: Complete replacement of the default prompt.
    Instructions: Additional guidance appended to the default prompt.
    """
    # Stage 1: Analyzer - The Build Engineer
    analyzer: Optional[str] = None
    analyzer_instructions: Optional[str] = None
    
    # Stage 2: Blueprint - The Chief Architect
    blueprint: Optional[str] = None
    blueprint_instructions: Optional[str] = None
    
    # Stage 3: Generator - The Docker Architect (fresh generation)
    generator: Optional[str] = None
    generator_instructions: Optional[str] = None
    
    # Stage 4: Reviewer - The Security Engineer
    reviewer: Optional[str] = None
    reviewer_instructions: Optional[str] = None
    
    # Stage 5: Reflector - The Principal DevOps Engineer (failure analysis)
    reflector: Optional[str] = None
    reflector_instructions: Optional[str] = None
    
    # Error Analyzer - The DevOps Engineer (error classification)
    error_analyzer: Optional[str] = None
    error_analyzer_instructions: Optional[str] = None
    
    # Iterative Improver - The Senior Docker Engineer (applies fixes)
    iterative_improver: Optional[str] = None
    iterative_improver_instructions: Optional[str] = None


# Global prompt configuration instance
_prompt_config: Optional[PromptConfig] = None


def get_prompt_config() -> PromptConfig:
    """
    Returns the global prompt configuration.
    
    If not initialized, creates a default configuration.
    
    Returns:
        PromptConfig: The current prompt configuration.
    """
    global _prompt_config
    if _prompt_config is None:
        _prompt_config = PromptConfig()
    return _prompt_config


def set_prompt_config(config: PromptConfig) -> None:
    """
    Sets the global prompt configuration.
    
    Args:
        config (PromptConfig): The prompt configuration to set.
    """
    global _prompt_config
    _prompt_config = config


def load_prompts_from_env() -> PromptConfig:
    """
    Loads custom prompts and instructions from environment variables.
    
    Environment variables follow the patterns:
    - DOCKAI_PROMPT_<NAME> for complete prompt replacement
    - DOCKAI_<NAME>_INSTRUCTIONS for additional instructions
    
    Returns:
        PromptConfig: A configuration with prompts loaded from environment.
    """
    return PromptConfig(
        # Full prompt replacements
        analyzer=os.getenv(f"{PROMPT_ENV_PREFIX}ANALYZER"),
        blueprint=os.getenv(f"{PROMPT_ENV_PREFIX}BLUEPRINT"),
        generator=os.getenv(f"{PROMPT_ENV_PREFIX}GENERATOR"),
        reviewer=os.getenv(f"{PROMPT_ENV_PREFIX}REVIEWER"),
        reflector=os.getenv(f"{PROMPT_ENV_PREFIX}REFLECTOR"),
        error_analyzer=os.getenv(f"{PROMPT_ENV_PREFIX}ERROR_ANALYZER"),
        iterative_improver=os.getenv(f"{PROMPT_ENV_PREFIX}ITERATIVE_IMPROVER"),
        # Instructions (appended to defaults)
        analyzer_instructions=os.getenv("DOCKAI_ANALYZER_INSTRUCTIONS"),
        blueprint_instructions=os.getenv("DOCKAI_BLUEPRINT_INSTRUCTIONS"),
        generator_instructions=os.getenv("DOCKAI_GENERATOR_INSTRUCTIONS"),
        reviewer_instructions=os.getenv("DOCKAI_REVIEWER_INSTRUCTIONS"),
        reflector_instructions=os.getenv("DOCKAI_REFLECTOR_INSTRUCTIONS"),
        error_analyzer_instructions=os.getenv("DOCKAI_ERROR_ANALYZER_INSTRUCTIONS"),
        iterative_improver_instructions=os.getenv("DOCKAI_ITERATIVE_IMPROVER_INSTRUCTIONS"),
    )


def load_prompts_from_file(path: str) -> Dict[str, str]:
    """
    Loads custom prompts and instructions from a .dockai file.
    
    The file supports sections like:
    - [prompt_analyzer], [prompt_generator], etc. for complete prompt replacement
    - [instructions_analyzer], [instructions_generator], etc. for additional instructions
    - Legacy [analyzer], [generator] sections for backward compatibility
    
    Args:
        path (str): The absolute path to the directory containing .dockai file.
        
    Returns:
        Dict[str, str]: A dictionary mapping prompt/instruction names to their content.
    """
    prompts = {}
    dockai_file_path = os.path.join(path, ".dockai")
    
    if not os.path.exists(dockai_file_path):
        return prompts
    
    try:
        with open(dockai_file_path, "r") as f:
            content = f.read()
            
        # Parse prompt and instruction sections
        lines = content.split('\n')
        current_section = None
        section_content = []
        
        # Map of section names to config field names
        section_map = {
            # Full prompt replacements
            "[prompt_analyzer]": "analyzer",
            "[prompt_blueprint]": "blueprint",
            "[prompt_generator]": "generator",
            "[prompt_reviewer]": "reviewer",
            "[prompt_reflector]": "reflector",
            "[prompt_error_analyzer]": "error_analyzer",
            "[prompt_iterative_improver]": "iterative_improver",
            # Instructions (appended to defaults)
            "[instructions_analyzer]": "analyzer_instructions",
            "[instructions_blueprint]": "blueprint_instructions",
            "[instructions_generator]": "generator_instructions",
            "[instructions_reviewer]": "reviewer_instructions",
            "[instructions_reflector]": "reflector_instructions",
            "[instructions_error_analyzer]": "error_analyzer_instructions",
            "[instructions_iterative_improver]": "iterative_improver_instructions",
            # Legacy section names (backward compatibility)
            "[analyzer]": "analyzer_instructions",
            "[generator]": "generator_instructions",
        }
        
        for line in lines:
            line_lower = line.strip().lower()
            
            # Check if this is a new section
            if line_lower in section_map:
                # Save previous section if exists
                if current_section and section_content:
                    prompts[current_section] = "\n".join(section_content).strip()
                
                current_section = section_map[line_lower]
                section_content = []
            elif current_section is not None:
                # Skip comment lines but include everything else
                if not line.strip().startswith('#'):
                    section_content.append(line)
        
        # Don't forget the last section
        if current_section and section_content:
            prompts[current_section] = "\n".join(section_content).strip()
            
    except Exception as e:
        import logging
        logger = logging.getLogger("dockai")
        logger.warning(f"Could not parse prompts from .dockai file: {e}")
    
    return prompts


def load_prompts(path: str) -> PromptConfig:
    """
    Loads custom prompts and instructions from all sources and merges them.
    
    Priority order (highest to lowest):
    1. Environment variables
    2. .dockai file
    3. Default prompts (built into each module)
    
    Args:
        path (str): The absolute path to the project directory.
        
    Returns:
        PromptConfig: The merged prompt configuration.
    """
    # Start with environment variables
    config = load_prompts_from_env()
    
    # Load from .dockai file
    file_prompts = load_prompts_from_file(path)
    
    # Merge prompts - env vars take precedence, but file prompts fill in gaps
    if file_prompts.get("analyzer") and not config.analyzer:
        config.analyzer = file_prompts["analyzer"]
    if file_prompts.get("blueprint") and not config.blueprint:
        config.blueprint = file_prompts["blueprint"]
    if file_prompts.get("generator") and not config.generator:
        config.generator = file_prompts["generator"]
    if file_prompts.get("reviewer") and not config.reviewer:
        config.reviewer = file_prompts["reviewer"]
    if file_prompts.get("reflector") and not config.reflector:
        config.reflector = file_prompts["reflector"]
    if file_prompts.get("error_analyzer") and not config.error_analyzer:
        config.error_analyzer = file_prompts["error_analyzer"]
    if file_prompts.get("iterative_improver") and not config.iterative_improver:
        config.iterative_improver = file_prompts["iterative_improver"]
    
    # Merge instructions - env vars take precedence, but file instructions fill in gaps
    if file_prompts.get("analyzer_instructions") and not config.analyzer_instructions:
        config.analyzer_instructions = file_prompts["analyzer_instructions"]
    if file_prompts.get("blueprint_instructions") and not config.blueprint_instructions:
        config.blueprint_instructions = file_prompts["blueprint_instructions"]
    if file_prompts.get("generator_instructions") and not config.generator_instructions:
        config.generator_instructions = file_prompts["generator_instructions"]
    if file_prompts.get("reviewer_instructions") and not config.reviewer_instructions:
        config.reviewer_instructions = file_prompts["reviewer_instructions"]
    if file_prompts.get("reflector_instructions") and not config.reflector_instructions:
        config.reflector_instructions = file_prompts["reflector_instructions"]
    if file_prompts.get("error_analyzer_instructions") and not config.error_analyzer_instructions:
        config.error_analyzer_instructions = file_prompts["error_analyzer_instructions"]
    if file_prompts.get("iterative_improver_instructions") and not config.iterative_improver_instructions:
        config.iterative_improver_instructions = file_prompts["iterative_improver_instructions"]
    
    return config


def get_prompt(prompt_name: str, default: str) -> str:
    """
    Gets a custom prompt or returns the default, with instructions appended.
    
    This is the main function used by other modules to get prompts.
    
    Logic:
    1. If a custom prompt is configured, return it (instructions are NOT appended to custom prompts)
    2. If no custom prompt, return default with instructions appended (if any)
    
    Args:
        prompt_name (str): The name of the prompt (e.g., 'analyzer', 'generator').
        default (str): The default prompt to use if no custom prompt is configured.
        
    Returns:
        str: The final prompt to use.
    """
    config = get_prompt_config()
    
    prompt_map = {
        "analyzer": config.analyzer,
        "blueprint": config.blueprint,
        "generator": config.generator,
        "reviewer": config.reviewer,
        "reflector": config.reflector,
        "error_analyzer": config.error_analyzer,
        "iterative_improver": config.iterative_improver,
    }
    
    instructions_map = {
        "analyzer": config.analyzer_instructions,
        "blueprint": config.blueprint_instructions,
        "generator": config.generator_instructions,
        "reviewer": config.reviewer_instructions,
        "reflector": config.reflector_instructions,
        "error_analyzer": config.error_analyzer_instructions,
        "iterative_improver": config.iterative_improver_instructions,
    }
    
    custom_prompt = prompt_map.get(prompt_name)
    custom_instructions = instructions_map.get(prompt_name)
    
    # If custom prompt is set, use it directly (instructions don't apply)
    if custom_prompt:
        return custom_prompt
    
    # Use default prompt, append instructions if any
    final_prompt = default
    if custom_instructions:
        final_prompt += f"\n\nADDITIONAL INSTRUCTIONS:\n{custom_instructions}\n"
    
    return final_prompt


def get_instructions(prompt_name: str) -> Optional[str]:
    """
    Gets custom instructions for a specific prompt.
    
    This is useful when you need to access instructions separately from prompts.
    
    Args:
        prompt_name (str): The name of the prompt (e.g., 'analyzer', 'generator').
        
    Returns:
        Optional[str]: The custom instructions if configured, otherwise None.
    """
    config = get_prompt_config()
    
    instructions_map = {
        "analyzer": config.analyzer_instructions,
        "blueprint": config.blueprint_instructions,
        "generator": config.generator_instructions,
        "reviewer": config.reviewer_instructions,
        "reflector": config.reflector_instructions,
        "error_analyzer": config.error_analyzer_instructions,
        "iterative_improver": config.iterative_improver_instructions,
    }
    
    return instructions_map.get(prompt_name)


# List of all available prompt names for documentation
AVAILABLE_PROMPTS = [
    ("analyzer", "DOCKAI_PROMPT_ANALYZER", "[prompt_analyzer]", 
     "The Build Engineer that analyzes project structure and technology stack"),
    ("blueprint", "DOCKAI_PROMPT_BLUEPRINT", "[prompt_blueprint]",
     "The Chief Architect that plans build strategy and runtime configuration"),
    ("generator", "DOCKAI_PROMPT_GENERATOR", "[prompt_generator]",
     "The Docker Architect that generates fresh Dockerfiles"),
    ("reviewer", "DOCKAI_PROMPT_REVIEWER", "[prompt_reviewer]",
     "The Security Engineer that reviews Dockerfiles for vulnerabilities"),
    ("reflector", "DOCKAI_PROMPT_REFLECTOR", "[prompt_reflector]",
     "The Principal DevOps Engineer that performs post-mortem failure analysis"),
    ("error_analyzer", "DOCKAI_PROMPT_ERROR_ANALYZER", "[prompt_error_analyzer]",
     "The DevOps Engineer that classifies Docker build/runtime errors"),
    ("iterative_improver", "DOCKAI_PROMPT_ITERATIVE_IMPROVER", "[prompt_iterative_improver]",
     "The Senior Docker Engineer that applies specific fixes to Dockerfiles"),
]

# List of all available instruction names for documentation
AVAILABLE_INSTRUCTIONS = [
    ("analyzer", "DOCKAI_ANALYZER_INSTRUCTIONS", "[instructions_analyzer]", 
     "Extra instructions for the Build Engineer"),
    ("blueprint", "DOCKAI_BLUEPRINT_INSTRUCTIONS", "[instructions_blueprint]",
     "Extra instructions for the Chief Architect"),
    ("generator", "DOCKAI_GENERATOR_INSTRUCTIONS", "[instructions_generator]",
     "Extra instructions for the Docker Architect"),
    ("reviewer", "DOCKAI_REVIEWER_INSTRUCTIONS", "[instructions_reviewer]",
     "Extra instructions for the Security Engineer"),
    ("reflector", "DOCKAI_REFLECTOR_INSTRUCTIONS", "[instructions_reflector]",
     "Extra instructions for failure analysis"),
    ("error_analyzer", "DOCKAI_ERROR_ANALYZER_INSTRUCTIONS", "[instructions_error_analyzer]",
     "Extra instructions for error classification"),
    ("iterative_improver", "DOCKAI_ITERATIVE_IMPROVER_INSTRUCTIONS", "[instructions_iterative_improver]",
     "Extra instructions for applying fixes"),
]
