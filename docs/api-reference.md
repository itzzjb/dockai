# API Reference

This document provides code-level documentation for DockAI's main modules and functions.

## Table of Contents

- [Workflow Module](#workflow-module)
- [Agents Module](#agents-module)
- [Utils Module](#utils-module)
- [Core Module](#core-module)
- [CLI Module](#cli-module)

## Workflow Module

### `src/dockai/workflow/graph.py`

Main workflow orchestration using LangGraph.

#### `create_graph() -> CompiledGraph`

Constructs and compiles the DockAI state graph.

**Parameters:** None

**Returns:**
- `CompiledGraph`: Compiled LangGraph state graph

**Graph Structure:**
```
START → scan → analyze → read_files → blueprint → generate 
→ review → [conditional: validate/reflect/end] → validate 
→ [conditional: reflect/end] → reflect → increment_retry 
→ [conditional: analyze/blueprint/generate]
```

**Example:**
```python
from dockai.workflow.graph import create_graph

graph = create_graph()
result = graph.invoke({
    "path": "/path/to/project",
    "config": {},
    "max_retries": 3,
    "retry_count": 0,
    "usage_stats": []
})
```

#### Conditional Edge Functions

These functions are defined in `graph.py` and control the workflow routing:

- **`should_retry(state) -> "reflect" | "end"`**: Decides whether to retry after validation failure. Checks error type, retry limits, and whether the error is fixable.
- **`check_security(state) -> "validate" | "reflect" | "end"`**: Routes based on security review results. Proceeds to validation if secure, reflects if insecure.
- **`check_reanalysis(state) -> "analyze" | "blueprint" | "generate"`**: After reflection, decides whether to re-analyze, re-plan, or just regenerate.

### `src/dockai/workflow/nodes.py`

Workflow node implementations.

#### `scan_node(state: DockAIState) -> DockAIState`

Scans the project directory to build a file tree.

**Returns:**
- Updated state with `file_tree` populated

#### `analyze_node(state: DockAIState) -> DockAIState`

Performs AI-powered project analysis.

**Returns:**
- Updated state with `analysis_result` and `usage_stats`

#### `read_files_node(state: DockAIState) -> DockAIState`

Reads project files using RAG-based context retrieval.

**Returns:**
- Updated state with `file_contents` and optionally `code_intelligence`

#### `blueprint_node(state: DockAIState) -> DockAIState`

Creates architectural blueprint and runtime configuration.

**Returns:**
- Updated state with `current_plan`, `detected_health_endpoint`, `readiness_patterns`

#### `generate_node(state: DockAIState) -> DockAIState`

Generates the Dockerfile. Supports two modes:
1. **Fresh generation**: Creates a new Dockerfile based on the blueprint
2. **Iterative improvement**: Uses reflection data to make targeted fixes to an existing Dockerfile

**Returns:**
- Updated state with `dockerfile_content`

#### `review_node(state: DockAIState) -> DockAIState`

Performs AI-powered security review. Automatically skips for script projects or when `DOCKAI_SKIP_SECURITY_REVIEW=true`.

**Returns:**
- Updated state with potential security errors or a fixed Dockerfile

#### `validate_node(state: DockAIState) -> DockAIState`

Validates the Dockerfile with Docker, Hadolint, and Trivy. Saves functional Dockerfiles as fallback candidates.

**Returns:**
- Updated state with `validation_result`, `error`, `error_details`, and optionally `best_dockerfile`

#### `reflect_node(state: DockAIState) -> DockAIState`

Analyzes failures and determines next steps. On max retries, reverts to the last working Dockerfile if available.

**Returns:**
- Updated state with `reflection`, `retry_history`, `needs_reanalysis`, and `previous_dockerfile`

#### `increment_retry(state: DockAIState) -> DockAIState`

Helper node that increments the retry counter.

**Returns:**
- Updated state with incremented `retry_count`

## Agents Module

All agent functions use the unified `AgentContext` dataclass (from `src/dockai/core/agent_context.py`) which provides a consistent interface for passing project information, retry state, and custom instructions to each agent.

### `src/dockai/agents/analyzer.py`

#### `analyze_repo_needs(context: AgentContext) -> Tuple[AnalysisResult, Dict[str, int]]`

**Stage 1: The Brain.** Analyzes the repository to determine project requirements. Uses an LLM to analyze the file list and deduce technology stack, project type (service vs. script), and build/start commands.

**Parameters:**
- `context` (`AgentContext`): Unified context containing `file_tree` and `custom_instructions`

**Returns:**
- `Tuple[AnalysisResult, Dict[str, int]]`: Structured analysis result and token usage stats

**Example:**
```python
from dockai.agents.analyzer import analyze_repo_needs
from dockai.core.agent_context import AgentContext

context = AgentContext(
    file_tree=["app.js", "package.json", "src/server.js"],
    custom_instructions=""
)
result, usage = analyze_repo_needs(context)
# result.project_type -> "service"
# result.stack -> "Node.js/Express"
```

### `src/dockai/agents/generator.py`

#### `generate_dockerfile(context: AgentContext) -> Tuple[str, str, str, Any]`

**Stage 2: The Architect.** Orchestrates Dockerfile generation. Decides whether to generate fresh or iteratively improve based on retry state.

**Parameters:**
- `context` (`AgentContext`): Unified context containing analysis results, file contents, retry history, plan, reflection, and custom instructions

**Returns:**
- `Tuple[str, str, str, Any]`: (Dockerfile content, project type, AI thought process, token usage stats)

### `src/dockai/agents/reviewer.py`

#### `review_dockerfile(context: AgentContext) -> Tuple[SecurityReviewResult, Any]`

**Stage 2.5: The Security Engineer.** Performs static security analysis of the generated Dockerfile using an LLM. Checks for critical issues, best practices, and generates a corrected Dockerfile if critical issues are found.

**Parameters:**
- `context` (`AgentContext`): Unified context containing `dockerfile_content`

**Returns:**
- `Tuple[SecurityReviewResult, Any]`: Structured security review result and token usage stats

The `SecurityReviewResult` includes:
- `is_secure`: Whether the Dockerfile passes security checks
- `issues`: List of `SecurityIssue` objects with severity, description, line number, and suggestion
- `fixed_dockerfile`: Corrected Dockerfile if critical issues were found

### `src/dockai/agents/agent_functions.py`

Shared adaptive agent functions used across the workflow.

#### `reflect_on_failure(context: AgentContext) -> Tuple[ReflectionResult, Dict[str, int]]`

Analyzes a failed Dockerfile build/run to determine root cause and solution. Uses error logs, the problematic Dockerfile, and project context.

**Parameters:**
- `context` (`AgentContext`): Uses `dockerfile_content`, `error_message`, `error_details`, `analysis_result`, `retry_history`, `container_logs`, `custom_instructions`

**Returns:**
- `Tuple[ReflectionResult, Dict[str, int]]`: Structured reflection result with specific fixes, and token usage

The `ReflectionResult` includes:
- `root_cause_analysis`, `specific_fixes`, `needs_reanalysis`
- `confidence_in_fix`: `"high"`, `"medium"`, or `"low"`
- `should_change_base_image`, `should_change_build_strategy`

#### `generate_iterative_dockerfile(context: AgentContext) -> Tuple[IterativeDockerfileResult, Dict[str, int]]`

Generates an improved Dockerfile by applying fixes from the reflection phase.

**Parameters:**
- `context` (`AgentContext`): Uses `dockerfile_content`, `reflection`, `analysis_result`, `file_contents`, `current_plan`, `verified_tags`, `custom_instructions`

**Returns:**
- `Tuple[IterativeDockerfileResult, Dict[str, int]]`: Result with improved Dockerfile content, and token usage

#### `create_blueprint(context: AgentContext) -> Tuple[BlueprintResult, Dict[str, int]]`

Generates a complete architectural blueprint (Plan + Runtime Config) in one pass. Combines planning and runtime detection to reduce token usage and latency.

**Parameters:**
- `context` (`AgentContext`): Unified context containing file contents and analysis results

**Returns:**
- `Tuple[BlueprintResult, Dict[str, int]]`: Combined blueprint result (plan + runtime config), and token usage

## Utils Module

### `src/dockai/utils/indexer.py`

RAG indexing and retrieval using sentence-transformer embeddings.

#### `class FileChunk`

```python
@dataclass
class FileChunk:
    file_path: str
    content: str
    start_line: int
    end_line: int
    chunk_type: str = "chunk"   # "full", "chunk", "function", "class"
    metadata: Dict = field(default_factory=dict)
```

#### `class ProjectIndex`

##### `__init__(use_embeddings: bool = True)`

Initializes the project index. When `use_embeddings=True`, uses sentence-transformers (`all-MiniLM-L6-v2`) for semantic search; otherwise falls back to keyword search.

##### `index_project(root_path: str, file_tree: List[str], chunk_size: int = 400, chunk_overlap: int = 50) -> None`

Indexes all files: reads content, performs AST analysis, splits into chunks, and builds embeddings.

**Parameters:**
- `root_path`: Absolute path to project root
- `file_tree`: List of relative file paths
- `chunk_size`: Lines per chunk (default: 400)
- `chunk_overlap`: Overlap between chunks (default: 50)

##### `search(query: str, top_k: int = 10) -> List[FileChunk]`

Searches for the most relevant file chunks. Uses cosine similarity when embeddings are available, falls back to keyword matching.

**Parameters:**
- `query`: Search query
- `top_k`: Number of chunks to return

**Returns:**
- List of `FileChunk` objects ranked by relevance

##### `get_entry_points() -> List[str]`

Returns all entry points detected by AST analysis across indexed files.

##### `get_all_env_vars() -> List[str]`

Returns all environment variables referenced across indexed files.

##### `get_all_ports() -> List[int]`

Returns all port numbers detected across indexed files.

##### `get_frameworks() -> List[str]`

Returns all frameworks detected across indexed files.

##### `get_stats() -> Dict`

Returns indexing statistics including `total_files`, `total_chunks`, and `indexed_at`.

### `src/dockai/utils/context_retriever.py`

Intelligent context assembly for Dockerfile generation using RAG results.

#### `class ContextRetriever`

##### `__init__(index: ProjectIndex, analysis_result: Dict[str, Any] = None)`

**Parameters:**
- `index`: An indexed `ProjectIndex` instance
- `analysis_result`: Analysis output from the analyzer agent

##### `get_dockerfile_context(max_tokens: int = 50000) -> str`

Retrieves optimal context for Dockerfile generation. Combines multiple strategies:
1. Must-have files (package.json, requirements.txt, etc.)
2. AST analysis summaries (detected ports, env vars, frameworks)
3. Entry point source code
4. Import graph traversal from entry points
5. Semantic search with dynamic queries
6. Catch-all for remaining budget

**Parameters:**
- `max_tokens`: Maximum token budget (default: 50000)

**Returns:**
- `str`: Assembled context optimized for LLM consumption

### `src/dockai/utils/scanner.py`

#### `get_file_tree(root_path: str) -> List[str]`

Traverses the directory tree to build a flat list of relative file paths.

**Parameters:**
- `root_path`: The root directory to scan

**Returns:**
- `List[str]`: List of relative paths that should be analyzed

**Filter Strategy:**
- Hardcoded ignore directories (node_modules, \_\_pycache\_\_, .git, etc.)
- `.gitignore` patterns
- `.dockerignore` patterns

**Raises:** `PermissionError`, `FileNotFoundError`, `NotADirectoryError`

### `src/dockai/utils/validator.py`

#### `validate_docker_build_and_run(directory, project_type, stack, ...) -> Tuple[bool, str, int, Optional[ClassifiedError]]`

Validates a Dockerfile by building and testing the container.

**Parameters:**
- `directory` (`str`): Directory containing the Dockerfile
- `project_type` (`str`): `"service"` or `"script"` (default: `"service"`)
- `stack` (`str`): Detected technology stack (default: `"Unknown"`)
- `health_endpoint` (`Optional[Tuple[str, int]]`): (endpoint_path, port) for health checking
- `recommended_wait_time` (`int`): AI-recommended container wait time in seconds (default: 5)
- `readiness_patterns` (`List[str]`): AI-detected log patterns indicating successful startup
- `failure_patterns` (`List[str]`): AI-detected log patterns indicating failure
- `no_cache` (`bool`): Disable Docker build cache (default: `False`)
- `analysis_result` (`dict`): Original project analysis context

**Returns:**
- `Tuple[bool, str, int, Optional[ClassifiedError]]`: (success, message, image_size_bytes, classified_error)

**Validation Steps:**
1. Docker build
2. Hadolint linting
3. Container startup (with readiness pattern detection)
4. Health check (if endpoint configured)
5. Error classification (on failure)

### `src/dockai/utils/code_intelligence.py`

#### `analyze_file(filepath: str, content: str) -> Optional[FileAnalysis]`

Main entry point for code analysis. Auto-detects language from file extension and applies the appropriate analyzer.

**Parameters:**
- `filepath`: Relative file path (used for language detection)
- `content`: File content

**Returns:**
- `FileAnalysis` object with:
  - `symbols`: List of `CodeSymbol` (functions, classes, imports, variables)
  - `imports`: Import statements
  - `entry_points`: Detected entry point functions
  - `exposed_ports`: Port numbers found in code
  - `env_vars`: Environment variable references
  - `framework_hints`: Detected framework usage

**Supported Languages (15):**
Python, JavaScript, TypeScript, Go, Rust, Ruby, PHP, Java, C#, Kotlin, Scala, Elixir, Haskell, Dart, Swift

**Also parses manifests:** package.json, go.mod, requirements.txt, pyproject.toml, Cargo.toml, Gemfile, composer.json

- Python uses the built-in `ast` module for accurate parsing
- All other languages use configurable regex patterns from `language_configs.py`

### `src/dockai/utils/file_utils.py`

#### `read_critical_files(path: str, files_to_read: List[str], truncation_enabled: bool = None) -> str`

Reads specified files from a project directory with optional smart truncation.

**Parameters:**
- `path`: Project root path
- `files_to_read`: List of relative file paths to read
- `truncation_enabled`: Whether to truncate large files. Auto-enables if total content exceeds `DOCKAI_TOKEN_LIMIT`

**Returns:**
- `str`: Concatenated file contents

#### `smart_truncate(content: str, filename: str, max_chars: int, max_lines: int) -> str`

Intelligently truncates file content using a head 70% + tail 30% strategy, preserving structure at both ends of the file.

**Parameters:**
- `content`: File content
- `filename`: File name (for type detection)
- `max_chars`: Maximum character limit
- `max_lines`: Maximum line limit

**Returns:**
- `str`: Truncated content

#### `estimate_tokens(text: str) -> int`

Estimates token count for a text string (approximate: chars / 4).

#### `minify_code(content: str, filename: str) -> str`

Minifies code by removing comments and blank lines (language-aware).

## Core Module

### `src/dockai/core/llm_providers.py`

Manages LLM provider configuration and model creation.

#### `class LLMProvider(Enum)`

```python
class LLMProvider(str, Enum):
    OPENAI = "openai"
    AZURE = "azure"
    GEMINI = "gemini"
    ANTHROPIC = "anthropic"
    OLLAMA = "ollama"
```

#### `class LLMConfig`

```python
@dataclass
class LLMConfig:
    default_provider: LLMProvider = LLMProvider.OPENAI
    models: dict = field(default_factory=dict)
    temperature: float = 0.0
    azure_endpoint: Optional[str] = None
    azure_api_version: str = "2024-02-15-preview"
    azure_deployment_map: dict = field(default_factory=dict)
    google_project: Optional[str] = None
    ollama_base_url: str = "http://localhost:11434"
    enable_caching: bool = True
```

#### `get_model_for_agent(agent_name: str, config: Optional[LLMConfig] = None) -> str`

Returns the model name string for a given agent. Falls back to provider defaults (fast model for most agents, powerful model for generator/reviewer).

**Parameters:**
- `agent_name`: Name of the agent (e.g., `"analyzer"`, `"generator"`, `"reviewer"`)
- `config`: Optional LLM config; uses the global config if not provided

**Returns:**
- `str`: Model name to use

#### `create_llm(agent_name: str, temperature: float = 0.0, config: Optional[LLMConfig] = None, **kwargs) -> ChatModel`

Creates and returns a LangChain chat model instance for the given agent.

**Parameters:**
- `agent_name`: Name of the agent
- `temperature`: Temperature for generation (default: 0.0 = deterministic)
- `config`: Optional LLM config
- `**kwargs`: Additional arguments passed to the LLM constructor

**Returns:**
- Configured LangChain chat model instance

**Raises:** `ValueError` if provider not supported or credentials missing

**Supported Providers:**
- OpenAI → `ChatOpenAI`
- Google Gemini → `ChatGoogleGenerativeAI`
- Anthropic Claude → `ChatAnthropic`
- Azure OpenAI → `AzureChatOpenAI`
- Ollama → `ChatOllama`

**Example:**
```python
from dockai.core.llm_providers import create_llm, load_llm_config_from_env, set_llm_config

# Load config from environment variables
config = load_llm_config_from_env()
set_llm_config(config)

# Create LLM for a specific agent
llm = create_llm("analyzer", temperature=0.0)
response = llm.invoke("Analyze this project...")
```

#### `load_llm_config_from_env() -> LLMConfig`

Creates an `LLMConfig` from environment variables (`DOCKAI_LLM_PROVIDER`, `DOCKAI_MODEL_*`, API keys, etc.).

#### `get_llm_config() -> LLMConfig`

Returns the current global LLM config. Creates a default from env vars if not initialized.

#### `set_llm_config(config: LLMConfig) -> None`

Sets the global LLM configuration.

### `src/dockai/core/agent_context.py`

#### `class AgentContext`

Unified context dataclass passed to all agent functions, eliminating the need for individual parameter passing.

```python
@dataclass
class AgentContext:
    # Core project information (always available)
    file_tree: List[str] = field(default_factory=list)
    file_contents: str = ""
    analysis_result: Dict[str, Any] = field(default_factory=dict)

    # Strategic planning (available after planning phase)
    current_plan: Optional[Dict[str, Any]] = None

    # Retry and failure context (available during retries)
    retry_history: List[Dict[str, Any]] = field(default_factory=list)
    dockerfile_content: Optional[str] = None
    reflection: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    error_details: Optional[Dict[str, Any]] = None
    container_logs: str = ""
    retry_count: int = 0

    # Agent-specific customization
    custom_instructions: str = ""

    # External data
    verified_tags: str = ""
```

##### `AgentContext.from_state(state: Dict[str, Any], agent_name: str = "") -> AgentContext`

Factory method to create an `AgentContext` from the workflow state dictionary. Automatically extracts the relevant fields and loads any custom instructions for the specified agent.

### `src/dockai/core/schemas.py`

Pydantic schemas for structured LLM outputs.

#### Key Schemas:

| Schema | Description |
|--------|-------------|
| `AnalysisResult` | Output of the analyzer: stack, project_type, files_to_read, build/start commands, suggested_base_image, health_endpoint |
| `BlueprintResult` | Combined plan + runtime config: base_image_strategy, build_strategy, health endpoints, readiness patterns |
| `PlanningResult` | Architectural plan: multi-stage strategy, optimization priorities, challenges, mitigations |
| `RuntimeConfigResult` | Runtime detection: health endpoints, startup patterns, estimated startup time |
| `DockerfileResult` | Generated Dockerfile with thought process and project type |
| `IterativeDockerfileResult` | Improved Dockerfile with changes summary and confidence level |
| `SecurityReviewResult` | Security review: is_secure flag, issues list, optional fixed_dockerfile |
| `SecurityIssue` | Individual security issue: severity, description, line_number, suggestion |
| `ReflectionResult` | Failure analysis: root cause, specific fixes, needs_reanalysis, confidence |
| `HealthEndpoint` | Health endpoint: path and port |
| `HealthEndpointDetectionResult` | Health detection results with confidence |
| `ReadinessPatternResult` | Startup patterns and timing estimates |

### `src/dockai/core/errors.py`

Error classification system using AI-powered analysis.

#### `class ErrorType(Enum)`

```python
class ErrorType(Enum):
    PROJECT_ERROR = "project_error"
    DOCKERFILE_ERROR = "dockerfile_error"
    ENVIRONMENT_ERROR = "environment_error"
    UNKNOWN_ERROR = "unknown_error"
```

#### `classify_error(context: AgentContext) -> ClassifiedError`

Public entry point for error classification. Validates API key availability, then delegates to AI analysis.

**Parameters:**
- `context` (`AgentContext`): Uses `error_message`, `container_logs`, `analysis_result`

**Returns:**
- `ClassifiedError` with `error_type`, `message`, `suggestion`, `should_retry`, and optional `dockerfile_fix`

#### `analyze_error_with_ai(context: AgentContext) -> ClassifiedError`

Performs AI-powered error analysis using an LLM to understand and classify Docker build/run errors.

### `src/dockai/core/state.py`

#### `class DockAIState(TypedDict)`

LangGraph state schema defining all fields that flow through the workflow.

(See [State Schema Reference](#state-schema-reference) below for the complete field listing.)

### `src/dockai/core/mcp_server.py`

Model Context Protocol server for Claude Desktop integration via FastMCP.

#### Tools Exposed:

| Tool | Description |
|------|-------------|
| `analyze_project` | Analyze a project directory for Dockerfile generation |
| `generate_dockerfile_content` | Generate a Dockerfile (returns content, does not write to disk) |
| `validate_dockerfile` | Validate a Dockerfile by building and running it |
| `run_full_workflow` | Full pipeline: analyze, generate, validate, retry (same as `dockai build`) |

## CLI Module

### `src/dockai/cli/main.py`

#### `build(path: str, verbose: bool, no_cache: bool)`

Main CLI command for building Dockerfiles. Orchestrates the full pipeline: LLM config setup, API key validation, custom instructions loading, state creation, and workflow invocation.

**Parameters:**
- `path` (`str`): Path to the repository to analyze (required argument)
- `verbose` (`bool`): Enable verbose debug logging (`--verbose` / `-v`, default: `False`)
- `no_cache` (`bool`): Disable Docker build cache (`--no-cache`, default: `False`)

**Example:**
```bash
dockai build /path/to/project --verbose
```

### `src/dockai/cli/ui.py`

Rich-powered terminal UI utilities.

| Function | Description |
|----------|-------------|
| `setup_logging(verbose: bool) -> Logger` | Configures logging with Rich formatting |
| `print_welcome()` | Displays branded welcome banner |
| `print_error(title, message, details)` | Displays formatted error panel |
| `print_success(message)` | Displays success message |
| `print_warning(message)` | Displays warning message |
| `display_summary(final_state, output_path)` | Displays generation results summary |
| `display_failure(final_state)` | Displays failure information |
| `get_status_spinner(message) -> Status` | Returns a Rich status spinner |

## State Schema Reference

Complete `DockAIState` fields (defined in `src/dockai/core/state.py`):

```python
class DockAIState(TypedDict):
    # INPUTS
    path: str                                    # Project path
    config: Dict[str, Any]                       # Configuration dictionary
    max_retries: int                             # Maximum retry attempts

    # INTERMEDIATE ARTIFACTS
    file_tree: List[str]                         # List of relative paths
    file_contents: str                           # RAG-retrieved context

    # Analysis & Planning
    analysis_result: Dict[str, Any]              # Analyzer output
    current_plan: Optional[Dict[str, Any]]       # Blueprint (plan + runtime config)

    # Generation
    dockerfile_content: str                      # Generated Dockerfile
    previous_dockerfile: Optional[str]           # Previous attempt's Dockerfile
    best_dockerfile: Optional[str]               # Best working Dockerfile so far
    best_dockerfile_source: Optional[str]        # Source of best Dockerfile

    # Validation & Execution
    validation_result: Dict[str, Any]            # Validation output
    retry_count: int                             # Current attempt number

    # Error Handling
    error: Optional[str]                         # Short error message
    error_details: Optional[Dict[str, Any]]      # Detailed error info
    logs: List[str]                              # Log entries

    # ADAPTIVE INTELLIGENCE
    retry_history: List[RetryAttempt]            # History of all attempts
    reflection: Optional[Dict[str, Any]]         # Reflection analysis

    # Smart Detection
    detected_health_endpoint: Optional[Dict[str, Any]]  # Health endpoint info
    readiness_patterns: List[str]                # Startup success patterns
    failure_patterns: List[str]                  # Startup failure patterns

    # Control Flow
    needs_reanalysis: bool                       # Whether to re-run analyzer

    # Observability
    usage_stats: List[Dict[str, Any]]            # Token usage per agent
```

### `RetryAttempt` (TypedDict)

```python
class RetryAttempt(TypedDict):
    attempt_number: int
    dockerfile_content: str
    error_message: str
    error_type: str
    what_was_tried: str
    why_it_failed: str
    lesson_learned: str
```

## Configuration Schema

The `config` dictionary inside `DockAIState` contains per-agent custom instructions and build options. Most settings (LLM provider, models, validation flags, RAG, etc.) are read directly from environment variables by each module, not from this dict.

**Actual `config` dict structure** (built in `cli/main.py`):

```python
{
    # Per-Agent Custom Instructions (from .dockai/prompts/ or env vars)
    "analyzer_instructions": str,
    "blueprint_instructions": str,
    "generator_instructions": str,
    "generator_iterative_instructions": str,
    "reviewer_instructions": str,
    "reflector_instructions": str,
    "error_analyzer_instructions": str,
    "iterative_improver_instructions": str,

    # Build Options
    "no_cache": bool,              # --no-cache flag
}
```

**Settings read from environment variables** (not in config dict):

```python
# These are read directly by their respective modules:
# LLM: llm_providers.py
"DOCKAI_LLM_PROVIDER"             # "openai", "gemini", "anthropic", "azure", "ollama"
"DOCKAI_MODEL_ANALYZER"           # Per-agent model override
"DOCKAI_MODEL_GENERATOR"          # Per-agent model override
# ... (see Configuration Guide for full list)

# Validation: validator.py / nodes.py
"DOCKAI_SKIP_HADOLINT"            # Skip Hadolint linting
"DOCKAI_SKIP_SECURITY_SCAN"       # Skip Trivy scanning
"DOCKAI_SKIP_HEALTH_CHECK"        # Skip health check validation
"DOCKAI_MAX_IMAGE_SIZE_MB"        # Max allowed image size

# File Reading: file_utils.py / nodes.py
"DOCKAI_TOKEN_LIMIT"              # Default: 50000
"DOCKAI_READ_ALL_FILES"           # Read all source files

# RAG: indexer.py
"DOCKAI_EMBEDDING_MODEL"          # Default: all-MiniLM-L6-v2

# Retry: cli/main.py
"MAX_RETRIES"                     # Default: 3

# Caching: llm_providers.py
"DOCKAI_LLM_CACHING"             # Enable LLM response caching
```

---

## Example: Complete Programmatic Usage

```python
from dockai.workflow.graph import create_graph
from dockai.core.state import DockAIState
from dockai.core.llm_providers import load_llm_config_from_env, set_llm_config

# Initialize LLM configuration from environment variables
llm_config = load_llm_config_from_env()
set_llm_config(llm_config)

# Configuration
config = {
    "path": "/path/to/project",
    "llm_provider": "openai",
    "model_analyzer": "gpt-4o-mini",
    "model_generator": "gpt-4o",
    "max_retries": 3,
    "skip_hadolint": False,
    "use_rag": True,
    "token_limit": 50000
}

# Build graph
graph = create_graph()

# Initial state
initial_state: DockAIState = {
    "path": config["path"],
    "config": config,
    "max_retries": config.get("max_retries", 3)
}

# Run workflow
result = graph.invoke(initial_state)

# Access results
print("Dockerfile:", result["dockerfile_content"])
print("Usage:", result["usage_stats"])

if result.get("error"):
    print("Error:", result["error"])
    print("Details:", result["error_details"])
```

---

**For more details, see the source code in `src/dockai/`.**
