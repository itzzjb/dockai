# Configuration Reference

DockAI offers extensive configuration through environment variables. This document provides a complete reference of all available options.

## Table of Contents

- [Quick Start](#quick-start)
- [LLM Provider Configuration](#llm-provider-configuration)
- [Model Selection](#model-selection)
- [Validation \& Security](#validation--security)
- [RAG Configuration](#rag-configuration)
- [Retry \& Adaptation](#retry--adaptation)
- [Custom Instructions](#custom-instructions)
- [Custom Prompts](#custom-prompts)
- [Observability](#observability)
- [Advanced Options](#advanced-options)

## Quick Start

The minimal configuration requires only an API key:

```bash
# Option 1: OpenAI (Default)
export OPENAI_API_KEY="sk-..."

# Option 2: Google Gemini
export GOOGLE_API_KEY="AIza..."
export DOCKAI_LLM_PROVIDER="gemini"

# Then run
dockai build .
```

For persistent configuration, create a `.env` file in your project root.

## LLM Provider Configuration

### Provider Selection

**Environment Variable:** `DOCKAI_LLM_PROVIDER`  
**Default:** `openai`  
**Options:** `openai`, `azure`, `gemini`, `anthropic`, `ollama`

```bash
export DOCKAI_LLM_PROVIDER="gemini"
```

### OpenAI

**Required:**
- `OPENAI_API_KEY`: Your OpenAI API key from [platform.openai.com](https://platform.openai.com/api-keys)

**Optional:**
- `OPENAI_ORG_ID`: Organization ID (for enterprise accounts)
- `OPENAI_BASE_URL`: Custom base URL (for proxies)

**Default Models:**
- Analyzer: `gpt-4o-mini`
- Generator: `gpt-4o`
- Reflector: `gpt-4o`

```bash
export OPENAI_API_KEY="sk-proj-..."
```

### Google Gemini

**Required:**
- `GOOGLE_API_KEY`: API key from [aistudio.google.com](https://aistudio.google.com/app/apikey)

**Optional:**
- `GOOGLE_CLOUD_PROJECT`: GCP project ID (for Vertex AI)

**Default Models:**
- Analyzer: `gemini-1.5-flash`
- Generator: `gemini-1.5-pro`
- Reflector: `gemini-1.5-pro`

```bash
export GOOGLE_API_KEY="AIza..."
export DOCKAI_LLM_PROVIDER="gemini"
```

### Anthropic Claude

**Required:**
- `ANTHROPIC_API_KEY`: API key from [console.anthropic.com](https://console.anthropic.com/settings/keys)

**Default Models:**
- Analyzer: `claude-3-5-haiku-latest`
- Generator: `claude-sonnet-4-20250514`
- Reflector: `claude-sonnet-4-20250514`

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
export DOCKAI_LLM_PROVIDER="anthropic"
```

### Azure OpenAI

**Required:**
- `AZURE_OPENAI_API_KEY`: Azure API key
- `AZURE_OPENAI_ENDPOINT`: Azure endpoint URL (e.g., `https://your-resource.openai.azure.com/`)

**Optional:**
- `AZURE_OPENAI_API_VERSION`: API version (default: `2024-02-15-preview`)

**Model Configuration:**
You **must** specify deployment names (not OpenAI model names):

```bash
export AZURE_OPENAI_API_KEY="..."
export AZURE_OPENAI_ENDPOINT="https://your-resource.openai.azure.com/"
export AZURE_OPENAI_API_VERSION="2024-02-15-preview"
export DOCKAI_LLM_PROVIDER="azure"

# Use your deployment names
export DOCKAI_MODEL_ANALYZER="gpt-4o-mini-deployment"
export DOCKAI_MODEL_GENERATOR="gpt-4o-deployment"
```

### Ollama (Local)

**Required:**
- Ollama installed and running ([ollama.com](https://ollama.com/))
- At least one model pulled (e.g., `ollama pull llama3`)

**Optional:**
- `OLLAMA_BASE_URL`: Custom URL (default: `http://localhost:11434`)

```bash
# Start Ollama
ollama serve

# Pull a model
ollama pull llama3

# Configure DockAI
export DOCKAI_LLM_PROVIDER="ollama"
export OLLAMA_BASE_URL="http://localhost:11434"
export DOCKAI_MODEL_ANALYZER="llama3"
export DOCKAI_MODEL_GENERATOR="llama3"
```

## Model Selection

DockAI allows per-agent model configuration for cost optimization.

### Per-Agent Model Configuration

| Agent | Environment Variable | Default (OpenAI) | Default (Gemini) |
|-------|---------------------|------------------|------------------|
| **Analyzer** | `DOCKAI_MODEL_ANALYZER` | `gpt-4o-mini` | `gemini-1.5-flash` |
| **Blueprint** | `DOCKAI_MODEL_BLUEPRINT` | `gpt-4o` | `gemini-1.5-pro` |
| **Generator** | `DOCKAI_MODEL_GENERATOR` | `gpt-4o` | `gemini-1.5-pro` |
| **Reviewer** | `DOCKAI_MODEL_REVIEWER` | `gpt-4o-mini` | `gemini-1.5-flash` |
| **Reflector** | `DOCKAI_MODEL_REFLECTOR` | `gpt-4o` | `gemini-1.5-pro` |
| **Error Analyzer** | `DOCKAI_MODEL_ERROR_ANALYZER` | `gpt-4o-mini` | `gemini-1.5-flash` |
| **Iterative Improver** | `DOCKAI_MODEL_ITERATIVE_IMPROVER` | `gpt-4o` | `gemini-1.5-pro` |

### Example: Cost Optimization

```bash
# Use cheap models for analysis, powerful for generation
export DOCKAI_MODEL_ANALYZER="gpt-4o-mini"         # $0.15 / 1M tokens
export DOCKAI_MODEL_BLUEPRINT="gpt-4o"             # $5.00 / 1M tokens
export DOCKAI_MODEL_GENERATOR="gpt-4o"             # $5.00 / 1M tokens
export DOCKAI_MODEL_REFLECTOR="gpt-4o"             # Best reasoning
```

### Example: All Gemini

```bash
export DOCKAI_LLM_PROVIDER="gemini"
export DOCKAI_MODEL_ANALYZER="gemini-1.5-flash"
export DOCKAI_MODEL_GENERATOR="gemini-1.5-pro"
export DOCKAI_MODEL_REFLECTOR="gemini-2.0-flash-exp"  # Experimental, faster
```

### Legacy Variables (Backward Compatibility)

DockAI v3.x used `MODEL_ANALYZER` and `MODEL_GENERATOR`. These still work but are deprecated:

```bash
# v3.x style (still works)
export MODEL_ANALYZER="gpt-4o-mini"
export MODEL_GENERATOR="gpt-4o"

# v4.x style (recommended)
export DOCKAI_MODEL_ANALYZER="gpt-4o-mini"
export DOCKAI_MODEL_GENERATOR="gpt-4o"
```

## Validation & Security

### Docker Validation

**Image Size Limit:**

```bash
# Fail if image > 500MB
export DOCKAI_MAX_IMAGE_SIZE_MB="500"

# Disable size check
export DOCKAI_MAX_IMAGE_SIZE_MB="0"
```

**Container Resource Limits:**

```bash
export DOCKAI_VALIDATION_MEMORY="512m"   # Memory limit
export DOCKAI_VALIDATION_CPUS="1.0"      # CPU limit
export DOCKAI_VALIDATION_PIDS="100"      # Max processes
```

### Hadolint (Dockerfile Linting)

```bash
# Skip Hadolint
export DOCKAI_SKIP_HADOLINT="true"

# Default: false (run if installed)
export DOCKAI_SKIP_HADOLINT="false"
```

### Trivy (Security Scanning)

```bash
# Skip Trivy
export DOCKAI_SKIP_SECURITY_SCAN="true"

# Fail on any vulnerability
export DOCKAI_STRICT_SECURITY="true"

# Default: run if installed, warn on vulnerabilities
export DOCKAI_SKIP_SECURITY_SCAN="false"
export DOCKAI_STRICT_SECURITY="false"
```

### Health Checks

```bash
# Skip health check validation
export DOCKAI_SKIP_HEALTH_CHECK="true"

# Default: false (validate HEALTHCHECK if present)
export DOCKAI_SKIP_HEALTH_CHECK="false"
```

### AI Security Review

```bash
# Skip AI security review
export DOCKAI_SKIP_SECURITY_REVIEW="true"

# Default: false (run for web apps, auto-skip for scripts)
export DOCKAI_SKIP_SECURITY_REVIEW="false"
```

## RAG Configuration

### Enable/Disable RAG

RAG is **always enabled** in the CLI. The `DOCKAI_USE_RAG` environment variable is only used in the **GitHub Action**.

When using the CLI, RAG is the default and only strategy — if RAG indexing fails, it automatically falls back to a simple "read all text files until token limit" strategy.

```bash
# GitHub Action only: disable RAG
export DOCKAI_USE_RAG="false"
```

**Note:** RAG requires `sentence-transformers` and `numpy`, which are now default dependencies in v4.0.

### Embedding Model

```bash
# Default (balanced speed/quality)
export DOCKAI_EMBEDDING_MODEL="all-MiniLM-L6-v2"

# Higher quality, slower
export DOCKAI_EMBEDDING_MODEL="all-mpnet-base-v2"

# Faster, smaller
export DOCKAI_EMBEDDING_MODEL="paraphrase-MiniLM-L3-v2"
```

### File Reading Strategy

```bash
# Read all source files (recommended)
export DOCKAI_READ_ALL_FILES="true"

# Read only critical files (faster, less accurate)
export DOCKAI_READ_ALL_FILES="false"
```

### File Reading Limits

```bash
# Max characters per file
export DOCKAI_MAX_FILE_CHARS="200000"

# Max lines per file
export DOCKAI_MAX_FILE_LINES="5000"

# Enable smart truncation
export DOCKAI_TRUNCATION_ENABLED="true"

# Token threshold for auto-truncation
export DOCKAI_TOKEN_LIMIT="50000"
```

**Smart Truncation:**
- Keeps imports, class definitions, and key functions
- Truncates long function bodies and repetitive code
- Activates automatically if total context > `DOCKAI_TOKEN_LIMIT`

## Retry & Adaptation

### Max Retries

**Environment Variable:** `MAX_RETRIES`  
**Default:** `3`

```bash
# Allow up to 5 attempts
export MAX_RETRIES="5"

# Disable retries (fail fast)
export MAX_RETRIES="0"
```

Each retry invokes the Reflect → Generate → Validate cycle.

### LLM Caching

**Environment Variable:** `DOCKAI_LLM_CACHING`  
**Default:** `true`

```bash
# Enable in-process caching (saves ~20-30% tokens on retries)
export DOCKAI_LLM_CACHING="true"

# Disable caching
export DOCKAI_LLM_CACHING="false"
```

**Note:** Cache is in-memory and scoped to a single run.

## Custom Instructions

Custom instructions are **appended** to the default agent prompts. Use them to add organization-specific requirements.

### Per-Agent Instructions

```bash
# Analyzer: Project discovery
export DOCKAI_ANALYZER_INSTRUCTIONS="Always check for a .tool-versions file to detect runtime versions."

# Blueprint: Architectural planning
export DOCKAI_BLUEPRINT_INSTRUCTIONS="Prefer multi-stage builds. Use Alpine Linux when possible."

# Generator: Dockerfile creation
export DOCKAI_GENERATOR_INSTRUCTIONS="Always pin all package versions. Include a maintainer label."

# Reviewer: Security audit
export DOCKAI_REVIEWER_INSTRUCTIONS="Flag any internet downloads without checksum verification."

# Reflector: Failure analysis
export DOCKAI_REFLECTOR_INSTRUCTIONS="If the build fails 3 times, suggest re-analyzing the project."

# Error Analyzer: Error classification
export DOCKAI_ERROR_ANALYZER_INSTRUCTIONS="Detect network issues separately from dependency errors."

# Iterative Improver: Surgical fixes
export DOCKAI_ITERATIVE_IMPROVER_INSTRUCTIONS="Only modify lines directly related to the error."
```

### Example: Enterprise Policy

```bash
export DOCKAI_GENERATOR_INSTRUCTIONS="
Company policy:
- Always use Red Hat UBI base images (registry.access.redhat.com/ubi9)
- Pin all versions (no 'latest' tags)
- Include maintainer label: LABEL maintainer='devops@company.com'
- Use multi-stage builds
- Run as non-root user (UID 10000)
"
```

## Custom Prompts

Custom prompts **completely replace** the default prompts. Use them for full control over agent behavior.

⚠️ **Warning:** Overriding prompts can break DockAI's output parsing. Only use if you understand the expected JSON schema.

### Per-Agent Prompts

```bash
export DOCKAI_PROMPT_ANALYZER="..."        # Full replacement for analyzer prompt
export DOCKAI_PROMPT_BLUEPRINT="..."       # Full replacement for blueprint prompt
export DOCKAI_PROMPT_GENERATOR="..."       # Full replacement for generator prompt
export DOCKAI_PROMPT_REVIEWER="..."
export DOCKAI_PROMPT_REFLECTOR="..."
export DOCKAI_PROMPT_ERROR_ANALYZER="..."
export DOCKAI_PROMPT_ITERATIVE_IMPROVER="..."
```

**File-Based Prompts:**

You can also load prompts from files in the `.dockai/` directory:

```bash
# DockAI checks for:
.dockai/
├── analyzer_instructions.txt
├── generator_instructions.txt
├── blueprint_instructions.txt
├── ... (all agents)
└── prompts/
    ├── analyzer.txt
    ├── generator.txt
    └── ... (all agents)
```

Priority order:
1. `DOCKAI_PROMPT_<AGENT>` env var (full replacement)
2. `.dockai/prompts/<agent>.txt` (full replacement)
3. `DOCKAI_<AGENT>_INSTRUCTIONS` env var (appended)
4. `.dockai/<agent>_instructions.txt` (appended)
5. Default prompt

## Observability

### OpenTelemetry Tracing

```bash
export DOCKAI_ENABLE_TRACING="true"
export DOCKAI_TRACING_EXPORTER="otlp"
export OTEL_EXPORTER_OTLP_ENDPOINT="http://localhost:4317"
export OTEL_SERVICE_NAME="dockai"
```

**Console Exporter (Debug):**

```bash
export DOCKAI_ENABLE_TRACING="true"
export DOCKAI_TRACING_EXPORTER="console"
```

Prints trace data to stdout.

### LangSmith Tracing

```bash
export LANGCHAIN_TRACING_V2="true"
export LANGCHAIN_API_KEY="lsv2_..."
export LANGCHAIN_PROJECT="dockai"
export LANGCHAIN_ENDPOINT="https://api.smith.langchain.com"
```

View traces at [smith.langchain.com](https://smith.langchain.com).

### Logging

**Verbose Logging:**

```bash
dockai build . --verbose
```

Enables DEBUG-level logs. Useful for troubleshooting.

## Advanced Options

### Project Path

```bash
# Default: current directory
dockai build .

# Specify custom path
dockai build /path/to/project
```

### No-Cache Flag

```bash
# Disable Docker build cache
dockai build . --no-cache
```

**Note:** When `--no-cache` is used, Docker skips the build cache, ensuring a clean build. On retries, `--no-cache` is automatically enabled.

## Complete Configuration Example

Here's a full `.env` file with common settings:

```bash
# LLM Provider
DOCKAI_LLM_PROVIDER=gemini
GOOGLE_API_KEY=AIza...

# Model Selection
DOCKAI_MODEL_ANALYZER=gemini-1.5-flash
DOCKAI_MODEL_GENERATOR=gemini-1.5-pro
DOCKAI_MODEL_REFLECTOR=gemini-2.0-flash-exp

# Validation
DOCKAI_SKIP_HADOLINT=false
DOCKAI_SKIP_SECURITY_SCAN=false
DOCKAI_STRICT_SECURITY=true
DOCKAI_MAX_IMAGE_SIZE_MB=500
DOCKAI_SKIP_HEALTH_CHECK=false
DOCKAI_SKIP_SECURITY_REVIEW=false

# Retry
MAX_RETRIES=3

# RAG
DOCKAI_USE_RAG=true
DOCKAI_EMBEDDING_MODEL=all-MiniLM-L6-v2
DOCKAI_READ_ALL_FILES=true

# Custom Instructions
DOCKAI_GENERATOR_INSTRUCTIONS=Always use Alpine. Pin versions. Add maintainer label.

# Observability
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=lsv2_...
LANGCHAIN_PROJECT=dockai

# Performance
DOCKAI_LLM_CACHING=true
```

## Environment Variable Reference Table

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `DOCKAI_LLM_PROVIDER` | string | `openai` | LLM provider |
| `OPENAI_API_KEY` | string | - | OpenAI API key |
| `GOOGLE_API_KEY` | string | - | Google API key |
| `ANTHROPIC_API_KEY` | string | - | Anthropic API key |
| `AZURE_OPENAI_API_KEY` | string | - | Azure API key |
| `AZURE_OPENAI_ENDPOINT` | string | - | Azure endpoint |
| `AZURE_OPENAI_API_VERSION` | string | `2024-02-15-preview` | Azure API version |
| `DOCKAI_MODEL_ANALYZER` | string | (provider default) | Analyzer model |
| `DOCKAI_MODEL_BLUEPRINT` | string | (provider default) | Blueprint model |
| `DOCKAI_MODEL_GENERATOR` | string | (provider default) | Generator model |
| `DOCKAI_MODEL_REVIEWER` | string | (provider default) | Reviewer model |
| `DOCKAI_MODEL_REFLECTOR` | string | (provider default) | Reflector model |
| `DOCKAI_MODEL_ERROR_ANALYZER` | string | (provider default) | Error analyzer model |
| `DOCKAI_MODEL_ITERATIVE_IMPROVER` | string | (provider default) | Iterative improver model |
| `MAX_RETRIES` | int | `3` | Max attempts |
| `DOCKAI_SKIP_HADOLINT` | bool | `false` | Skip Hadolint |
| `DOCKAI_SKIP_SECURITY_SCAN` | bool | `false` | Skip Trivy |
| `DOCKAI_STRICT_SECURITY` | bool | `false` | Fail on any vuln |
| `DOCKAI_MAX_IMAGE_SIZE_MB` | int | `500` | Max image size (0 = disabled) |
| `DOCKAI_SKIP_HEALTH_CHECK` | bool | `false` | Skip health check |
| `DOCKAI_SKIP_SECURITY_REVIEW` | bool | `false` | Skip AI security review |
| `DOCKAI_VALIDATION_MEMORY` | string | `512m` | Container memory limit |
| `DOCKAI_VALIDATION_CPUS` | string | `1.0` | Container CPU limit |
| `DOCKAI_VALIDATION_PIDS` | int | `100` | Container PID limit |
| `DOCKAI_MAX_FILE_CHARS` | int | `200000` | Max chars per file |
| `DOCKAI_MAX_FILE_LINES` | int | `5000` | Max lines per file |
| `DOCKAI_TRUNCATION_ENABLED` | bool | `false` | Force truncation |
| `DOCKAI_TOKEN_LIMIT` | int | `50000` | Auto-truncation threshold |
| `DOCKAI_USE_RAG` | bool | `true` | Enable RAG |
| `DOCKAI_EMBEDDING_MODEL` | string | `all-MiniLM-L6-v2` | Embedding model |
| `DOCKAI_READ_ALL_FILES` | bool | `true` | Read all files |
| `DOCKAI_LLM_CACHING` | bool | `true` | Enable LLM caching |
| `DOCKAI_ENABLE_TRACING` | bool | `false` | Enable tracing |
| `DOCKAI_TRACING_EXPORTER` | string | `console` | Trace exporter |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | string | `http://localhost:4317` | OTLP endpoint |
| `OTEL_SERVICE_NAME` | string | `dockai` | Service name |
| `LANGCHAIN_TRACING_V2` | bool | `false` | LangSmith tracing |
| `LANGCHAIN_API_KEY` | string | - | LangSmith API key |
| `LANGCHAIN_PROJECT` | string | `dockai` | LangSmith project |
| `OLLAMA_BASE_URL` | string | `http://localhost:11434` | Ollama URL |
| `GOOGLE_CLOUD_PROJECT` | string | - | GCP project ID |

---

**Next**: See [LLM Providers](llm-providers.md) for detailed setup guides for each provider.
