"""
DockAI LLM Providers Module.

This module provides a unified interface for creating LLM instances across
multiple providers (OpenAI, Azure OpenAI, Google Gemini, Anthropic). It enables users
to configure different models for each AI agent in the DockAI workflow.

Supported Providers:
- openai: OpenAI API
- azure: Azure OpenAI Service
- gemini: Google Gemini
- anthropic: Anthropic Claude
- ollama: Ollama

Configuration is done via environment variables:
- DOCKAI_LLM_PROVIDER: Default provider (openai, azure, gemini, anthropic, ollama)
- DOCKAI_MODEL_<AGENT>: Model name for each agent
- Provider-specific credentials (OPENAI_API_KEY, AZURE_OPENAI_*, GOOGLE_API_KEY, ANTHROPIC_API_KEY)

Per-Agent Model Configuration:
- DOCKAI_MODEL_ANALYZER: Model for the analyzer agent
- DOCKAI_MODEL_BLUEPRINT: Model for the blueprint agent
- DOCKAI_MODEL_GENERATOR: Model for the generator agent
- DOCKAI_MODEL_GENERATOR_ITERATIVE: Model for iterative generation
- DOCKAI_MODEL_REVIEWER: Model for the security reviewer
- DOCKAI_MODEL_REFLECTOR: Model for failure reflection
- DOCKAI_MODEL_ERROR_ANALYZER: Model for error classification
- DOCKAI_MODEL_ITERATIVE_IMPROVER: Model for iterative improvement
"""

import os
import logging
from typing import Optional, Any, Literal
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger("dockai")


class LLMProvider(str, Enum):
    """Supported LLM providers."""
    OPENAI = "openai"
    AZURE = "azure"
    GEMINI = "gemini"
    ANTHROPIC = "anthropic"
    OLLAMA = "ollama"


# Default models for each provider
DEFAULT_MODELS = {
    LLMProvider.OPENAI: {
        "fast": "gpt-4o-mini",      # Fast, cost-effective model for analysis
        "powerful": "gpt-4o",        # Powerful model for generation/reflection
    },
    LLMProvider.AZURE: {
        "fast": "gpt-4o-mini",       # Azure deployment name for fast model
        "powerful": "gpt-4o",         # Azure deployment name for powerful model
    },
    LLMProvider.GEMINI: {
        "fast": "gemini-1.5-flash",  # Fast Gemini model
        "powerful": "gemini-1.5-pro", # Powerful Gemini model
    },
    LLMProvider.ANTHROPIC: {
        "fast": "claude-3-5-haiku-latest",   # Fast Claude model
        "powerful": "claude-sonnet-4-20250514", # Powerful Claude model
    },
    LLMProvider.OLLAMA: {
        "fast": "llama3",            # Fast Ollama model
        "powerful": "llama3",        # Powerful Ollama model
    },
}


# Agent to model type mapping (which agents need fast vs powerful models)
AGENT_MODEL_TYPE = {
    "analyzer": "fast",
    "blueprint": "powerful", # Blueprint needs powerful model for planning
    "generator": "powerful",
    "generator_iterative": "powerful",
    "reviewer": "fast",
    "reflector": "powerful",
    "error_analyzer": "fast",
    "iterative_improver": "powerful",
}


@dataclass
class LLMConfig:
    """
    Configuration for LLM provider and per-agent model settings.
    
    Attributes:
        default_provider: The LLM provider to use (openai, azure, gemini, anthropic, ollama)
        models: Dictionary mapping agent names to model names
        temperature: Default temperature for LLM calls
        
    Azure-specific attributes:
        azure_endpoint: Azure OpenAI endpoint URL
        azure_api_version: Azure OpenAI API version
        azure_deployment_map: Mapping of model names to Azure deployment names
        
    Gemini-specific attributes:
        google_project: Google Cloud project ID (optional)

    Ollama-specific attributes:
        ollama_base_url: Base URL for Ollama API (default: http://localhost:11434)
        
    Caching attributes:
        enable_caching: Enable in-memory LLM response caching (default: True)
    """
    default_provider: LLMProvider = LLMProvider.OPENAI
    
    # Per-agent model configuration
    models: dict = field(default_factory=dict)
    
    # General settings
    temperature: float = 0.0
    
    # Azure-specific settings
    azure_endpoint: Optional[str] = None
    azure_api_version: str = "2024-02-15-preview"
    azure_deployment_map: dict = field(default_factory=dict)
    
    # Gemini-specific settings
    google_project: Optional[str] = None

    # Ollama-specific settings
    ollama_base_url: str = "http://localhost:11434"
    
    # Caching settings
    enable_caching: bool = True


# Global LLM configuration instance
_llm_config: Optional[LLMConfig] = None
_cache_initialized: bool = False


def _init_llm_cache() -> None:
    """Initialize in-memory LLM response caching for the current run."""
    global _cache_initialized
    if _cache_initialized:
        return
    
    try:
        from langchain.cache import InMemoryCache
        from langchain.globals import set_llm_cache
        set_llm_cache(InMemoryCache())
        _cache_initialized = True
        logger.debug("LLM caching enabled (in-memory)")
    except ImportError:
        logger.debug("LangChain cache not available, skipping")
    except Exception as e:
        logger.debug(f"Failed to initialize LLM cache: {e}")


def get_llm_config() -> LLMConfig:
    """
    Returns the global LLM configuration.
    
    If not initialized, creates a default configuration from environment variables.
    
    Returns:
        LLMConfig: The current LLM configuration.
    """
    global _llm_config
    if _llm_config is None:
        _llm_config = load_llm_config_from_env()
    return _llm_config


def set_llm_config(config: LLMConfig) -> None:
    """
    Sets the global LLM configuration.
    
    Args:
        config (LLMConfig): The LLM configuration to set.
    """
    global _llm_config
    _llm_config = config


def load_llm_config_from_env() -> LLMConfig:
    """
    Loads LLM configuration from environment variables.
    
    Environment Variables:
        DOCKAI_LLM_PROVIDER: Provider name (openai, azure, gemini, anthropic, ollama)
        DOCKAI_MODEL_<AGENT>: Model for specific agent
        
        Azure-specific:
        AZURE_OPENAI_ENDPOINT: Azure endpoint URL
        AZURE_OPENAI_API_VERSION: API version
        AZURE_OPENAI_DEPLOYMENT_<MODEL>: Deployment name mapping
        
        Gemini-specific:
        GOOGLE_CLOUD_PROJECT: Google Cloud project ID

        Ollama-specific:
        OLLAMA_BASE_URL: Base URL for Ollama API
    
    Returns:
        LLMConfig: Configuration loaded from environment.
    """
    # Determine provider
    provider_str = os.getenv("DOCKAI_LLM_PROVIDER", "openai").lower()
    try:
        provider = LLMProvider(provider_str)
    except ValueError:
        logger.warning(f"Unknown provider '{provider_str}', defaulting to OpenAI")
        provider = LLMProvider.OPENAI
    
    # Load per-agent model configuration
    models = {}
    
    # Map of agent names to their environment variable names
    agent_env_map = {
        "analyzer": "DOCKAI_MODEL_ANALYZER",
        "blueprint": "DOCKAI_MODEL_BLUEPRINT", 
        "generator": "DOCKAI_MODEL_GENERATOR",
        "generator_iterative": "DOCKAI_MODEL_GENERATOR_ITERATIVE",
        "reviewer": "DOCKAI_MODEL_REVIEWER",
        "reflector": "DOCKAI_MODEL_REFLECTOR",
        "error_analyzer": "DOCKAI_MODEL_ERROR_ANALYZER",
        "iterative_improver": "DOCKAI_MODEL_ITERATIVE_IMPROVER",
    }
    
    # Load models from environment
    for agent, env_var in agent_env_map.items():
        model = os.getenv(env_var)
        if model:
            models[agent] = model
    
    # Load Azure-specific settings
    azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    azure_api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")
    
    # Load Azure deployment mappings
    azure_deployment_map = {}
    for key, value in os.environ.items():
        if key.startswith("AZURE_OPENAI_DEPLOYMENT_"):
            model_name = key.replace("AZURE_OPENAI_DEPLOYMENT_", "").lower().replace("_", "-")
            azure_deployment_map[model_name] = value
    
    # Load Gemini-specific settings
    google_project = os.getenv("GOOGLE_CLOUD_PROJECT")

    # Load Ollama-specific settings
    ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    
    # Load caching settings (enabled by default for efficiency)
    enable_caching = os.getenv("DOCKAI_LLM_CACHING", "true").lower() in ("true", "1", "yes")
    
    return LLMConfig(
        default_provider=provider,
        models=models,
        azure_endpoint=azure_endpoint,
        azure_api_version=azure_api_version,
        azure_deployment_map=azure_deployment_map,
        google_project=google_project,
        ollama_base_url=ollama_base_url,
        enable_caching=enable_caching,
    )


def get_model_for_agent(agent_name: str, config: Optional[LLMConfig] = None) -> str:
    """
    Gets the configured model name for a specific agent.
    
    Args:
        agent_name: Name of the agent (e.g., 'analyzer', 'generator')
        config: Optional LLM config, uses global if not provided
        
    Returns:
        str: The model name to use for this agent
    """
    if config is None:
        config = get_llm_config()
    
    # Check if agent has a specific model configured
    if agent_name in config.models:
        return config.models[agent_name]
    
    # Fall back to default model for this agent's type
    model_type = AGENT_MODEL_TYPE.get(agent_name, "fast")
    return DEFAULT_MODELS[config.default_provider][model_type]


def create_llm(
    agent_name: str,
    temperature: float = 0.0,
    config: Optional[LLMConfig] = None,
    **kwargs
) -> Any:
    """
    Creates an LLM instance for the specified agent.
    
    This is the main factory function that creates the appropriate LLM
    based on the provider configuration.
    
    Args:
        agent_name: Name of the agent (e.g., 'analyzer', 'generator', 'reviewer')
        temperature: Temperature for generation (0.0 = deterministic)
        config: Optional LLM config, uses global if not provided
        **kwargs: Additional arguments passed to the LLM constructor
        
    Returns:
        A LangChain chat model instance (ChatOpenAI, AzureChatOpenAI, or ChatGoogleGenerativeAI)
        
    Raises:
        ValueError: If the provider is not supported or credentials are missing
    """
    if config is None:
        config = get_llm_config()
    
    # Initialize caching on first LLM creation
    if config.enable_caching:
        _init_llm_cache()
    
    model_name = get_model_for_agent(agent_name, config)
    
    # Determine provider for this specific agent
    provider = config.default_provider
    
    # Check if model name specifies a provider (e.g. "gemini/gemini-pro")
    if "/" in model_name:
        parts = model_name.split("/", 1)
        try:
            provider = LLMProvider(parts[0])
            model_name = parts[1]
        except ValueError:
            # Not a valid provider prefix, assume it's part of the model name
            pass
            
    logger.debug(f"Creating LLM for agent '{agent_name}': provider={provider.value}, model={model_name}")
    
    if provider == LLMProvider.OPENAI:
        return _create_openai_llm(model_name, temperature, **kwargs)
    elif provider == LLMProvider.AZURE:
        return _create_azure_llm(model_name, temperature, config, **kwargs)
    elif provider == LLMProvider.GEMINI:
        return _create_gemini_llm(model_name, temperature, config, **kwargs)
    elif provider == LLMProvider.ANTHROPIC:
        return _create_anthropic_llm(model_name, temperature, **kwargs)
    elif provider == LLMProvider.OLLAMA:
        return _create_ollama_llm(model_name, temperature, config, **kwargs)
    else:
        raise ValueError(f"Unsupported LLM provider: {provider}")


def _create_openai_llm(model_name: str, temperature: float, **kwargs) -> Any:
    """Creates an OpenAI LLM instance."""
    try:
        from langchain_openai import ChatOpenAI
    except ImportError as e:
        logger.error("Failed to import langchain_openai - is it installed?")
        raise ImportError(
            "The langchain_openai package is not installed. "
            "Install it with: pip install langchain-openai"
        ) from e
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        logger.error("OPENAI_API_KEY environment variable is missing")
        raise ValueError(
            "OPENAI_API_KEY environment variable is required for OpenAI provider. "
            "Set it in your .env file or environment."
        )
    
    try:
        return ChatOpenAI(
            model=model_name,
            temperature=temperature,
            api_key=api_key,
            **kwargs
        )
    except Exception as e:
        logger.error(f"Failed to create OpenAI LLM: {e}")
        raise


def _create_azure_llm(model_name: str, temperature: float, config: LLMConfig, **kwargs) -> Any:
    """Creates an Azure OpenAI LLM instance."""
    try:
        from langchain_openai import AzureChatOpenAI
    except ImportError as e:
        logger.error("Failed to import langchain_openai - is it installed?")
        raise ImportError(
            "The langchain_openai package is not installed. "
            "Install it with: pip install langchain-openai"
        ) from e
    
    api_key = os.getenv("AZURE_OPENAI_API_KEY")
    if not api_key:
        logger.error("AZURE_OPENAI_API_KEY environment variable is missing")
        raise ValueError(
            "AZURE_OPENAI_API_KEY environment variable is required for Azure provider. "
            "Set it in your .env file or environment."
        )
    
    if not config.azure_endpoint:
        logger.error("AZURE_OPENAI_ENDPOINT environment variable is missing")
        raise ValueError(
            "AZURE_OPENAI_ENDPOINT environment variable is required for Azure provider. "
            "Set it to your Azure OpenAI endpoint URL."
        )
    
    # Get deployment name from mapping or use model name
    deployment_name = config.azure_deployment_map.get(model_name, model_name)
    
    try:
        return AzureChatOpenAI(
            azure_deployment=deployment_name,
            azure_endpoint=config.azure_endpoint,
            api_version=config.azure_api_version,
            api_key=api_key,
            temperature=temperature,
            **kwargs
        )
    except Exception as e:
        logger.error(f"Failed to create Azure OpenAI LLM: {e}")
        raise


def _create_gemini_llm(model_name: str, temperature: float, config: LLMConfig, **kwargs) -> Any:
    """Creates a Google Gemini LLM instance."""
    try:
        from langchain_google_genai import ChatGoogleGenerativeAI
    except ImportError as e:
        logger.error("Failed to import langchain_google_genai - is it installed?")
        raise ImportError(
            "The langchain_google_genai package is not installed. "
            "Install it with: pip install langchain-google-genai"
        ) from e
    
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        logger.error("GOOGLE_API_KEY environment variable is missing")
        raise ValueError(
            "GOOGLE_API_KEY environment variable is required for Gemini provider. "
            "Set it in your .env file or environment."
        )
    
    try:
        return ChatGoogleGenerativeAI(
            model=model_name,
            temperature=temperature,
            google_api_key=api_key,
            **kwargs
        )
    except Exception as e:
        logger.error(f"Failed to create Gemini LLM: {e}")
        raise


def _create_anthropic_llm(model_name: str, temperature: float, **kwargs) -> Any:
    """Creates an Anthropic Claude LLM instance."""
    try:
        from langchain_anthropic import ChatAnthropic
    except ImportError as e:
        logger.error("Failed to import langchain_anthropic - is it installed?")
        raise ImportError(
            "The langchain_anthropic package is not installed. "
            "Install it with: pip install langchain-anthropic"
        ) from e
    
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        logger.error("ANTHROPIC_API_KEY environment variable is missing")
        raise ValueError(
            "ANTHROPIC_API_KEY environment variable is required for Anthropic provider. "
            "Set it in your .env file or environment."
        )
    
    try:
        return ChatAnthropic(
            model=model_name,
            temperature=temperature,
            api_key=api_key,
            **kwargs
        )
    except Exception as e:
        logger.error(f"Failed to create Anthropic LLM: {e}")
        raise


def _create_ollama_llm(model_name: str, temperature: float, config: LLMConfig, **kwargs) -> Any:
    """
    Creates an Ollama LLM instance.
    
    If Ollama is not available locally, this function will automatically
    start an Ollama Docker container and use it instead.
    """
    from langchain_ollama import ChatOllama
    from ..utils.ollama_docker import get_ollama_url, is_ollama_available
    
    # Check if Ollama is available at configured URL
    configured_url = config.ollama_base_url
    
    if is_ollama_available(configured_url):
        logger.debug(f"Using Ollama at {configured_url}")
        base_url = configured_url
    else:
        # Try to get Ollama URL (may start Docker container)
        logger.info("Ollama not available at configured URL, checking alternatives...")
        try:
            base_url = get_ollama_url(model_name=model_name, preferred_url=configured_url)
            logger.info(f"Using Ollama at {base_url}")
        except RuntimeError as e:
            raise ValueError(
                f"Ollama is not available and could not be started via Docker.\n"
                f"Options:\n"
                f"  1. Install and run Ollama locally: https://ollama.ai/download\n"
                f"  2. Install Docker to use Ollama via container\n"
                f"  3. Use a different LLM provider (set DOCKAI_LLM_PROVIDER)\n"
                f"\nError: {e}"
            ) from e
    
    return ChatOllama(
        model=model_name,
        temperature=temperature,
        base_url=base_url,
        **kwargs
    )


def get_provider_info() -> dict:
    """
    Returns information about the current LLM provider configuration.
    
    Useful for logging and debugging.
    
    Returns:
        dict: Provider information including name, models, and configuration status
    """
    config = get_llm_config()
    
    info = {
        "default_provider": config.default_provider.value,
        "models": {},
        "credentials_configured": {},
    }
    
    # Check credentials for all providers
    info["credentials_configured"]["openai"] = bool(os.getenv("OPENAI_API_KEY"))
    
    info["credentials_configured"]["azure"] = bool(
        os.getenv("AZURE_OPENAI_API_KEY") and config.azure_endpoint
    )
    if info["credentials_configured"]["azure"]:
        info["azure_endpoint"] = config.azure_endpoint
        info["azure_api_version"] = config.azure_api_version
        
    info["credentials_configured"]["gemini"] = bool(os.getenv("GOOGLE_API_KEY"))
    info["credentials_configured"]["anthropic"] = bool(os.getenv("ANTHROPIC_API_KEY"))
    
    info["credentials_configured"]["ollama"] = True
    info["ollama_base_url"] = config.ollama_base_url
    
    # Get model for each agent
    for agent in AGENT_MODEL_TYPE.keys():
        info["models"][agent] = get_model_for_agent(agent, config)
    
    return info


def log_provider_info() -> None:
    """Logs the current LLM provider configuration."""
    info = get_provider_info()
    
    logger.info(f"Default LLM Provider: {info['default_provider'].upper()}")
    
    # Check if default provider has credentials
    if not info["credentials_configured"].get(info['default_provider'], False):
        logger.warning(f"Credentials not configured for default provider {info['default_provider']}!")
    
    # Group models by unique value for cleaner output
    model_groups = {}
    for agent, model in info["models"].items():
        if model not in model_groups:
            model_groups[model] = []
        model_groups[model].append(agent)
    
    logger.info("Model Configuration:")
    for model, agents in model_groups.items():
        logger.info(f"  {model}: {', '.join(agents)}")
