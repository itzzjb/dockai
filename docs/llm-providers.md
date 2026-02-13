# LLM Providers Setup Guide

This guide provides detailed setup instructions for each supported LLM provider.

## Table of Contents

- [OpenAI](#openai)
- [Google Gemini](#google-gemini)
- [Anthropic Claude](#anthropic-claude)
- [Azure OpenAI](#azure-openai)
- [Ollama (Local)](#ollama-local)
- [Provider Comparison](#provider-comparison)
- [Troubleshooting](#troubleshooting)

## OpenAI

OpenAI is the default provider and offers the most reliable performance.

### Setup

1. **Create an account** at [platform.openai.com](https://platform.openai.com/)
2. **Add payment method** (requires credit card)
3. **Generate API key** at [platform.openai.com/api-keys](https://platform.openai.com/api-keys)
4. **Set environment variable:**

```bash
export OPENAI_API_KEY="sk-proj-..."
```

### Recommended Models

| Agent | Model | Cost (per 1M tokens) | Notes |
|-------|-------|---------------------|-------|
| Analyzer | `gpt-4o-mini` | $0.15 input / $0.60 output | Fast, cheap |
| Blueprint | `gpt-4o` | $5.00 input / $15.00 output | Best reasoning |
| Generator | `gpt-4o` | $5.00 input / $15.00 output | High quality |
| Reflector | `o1-mini` | $3.00 input / $12.00 output | Best for reflection |

### Configuration

```bash
export OPENAI_API_KEY="sk-proj-..."
export DOCKAI_LLM_PROVIDER="openai"  # Default, can be omitted

# Use all GPT-4o mini for cost savings
export DOCKAI_MODEL_ANALYZER="gpt-4o-mini"
export DOCKAI_MODEL_GENERATOR="gpt-4o-mini"
export DOCKAI_MODEL_REFLECTOR="gpt-4o-mini"
```

### Enterprise Features

For organization accounts:

```bash
export OPENAI_API_KEY="sk-proj-..."
export OPENAI_ORG_ID="org-..."
```

## Google Gemini

Google Gemini offers the best cost-to-performance ratio and has a generous free tier.

### Setup

1. **Get API key** at [aistudio.google.com](https://aistudio.google.com/app/apikey)
2. **Set environment variables:**

```bash
export GOOGLE_API_KEY="AIza..."
export DOCKAI_LLM_PROVIDER="gemini"
```

### Free Tier

- **1,500 requests per day** (Gemini 1.5 Flash)
- **50 requests per day** (Gemini 1.5 Pro)
- **No credit card required**

Perfect for getting started!

### Recommended Models

| Agent | Model | Cost (per 1M tokens) | Notes |
|-------|-------|---------------------|-------|
| Analyzer | `gemini-1.5-flash` | $0.075 input / $0.30 output | Very fast, cheap |
| Blueprint | `gemini-1.5-pro` | $3.50 input / $10.50 output | Excellent reasoning |
| Generator | `gemini-1.5-pro` | $3.50 input / $10.50 output | High quality |
| Reflector | `gemini-2.0-flash-exp` | Free (experimental) | Cutting edge |

### Configuration

```bash
export GOOGLE_API_KEY="AIza..."
export DOCKAI_LLM_PROVIDER="gemini"

# Default models (recommended)
export DOCKAI_MODEL_ANALYZER="gemini-1.5-flash"
export DOCKAI_MODEL_GENERATOR="gemini-1.5-pro"
export DOCKAI_MODEL_REFLECTOR="gemini-2.0-flash-exp"
```

### Vertex AI (GCP)

For enterprise deployments with Vertex AI:

```bash
export GOOGLE_API_KEY="..."           # Service account key
export GOOGLE_CLOUD_PROJECT="your-project-id"
export DOCKAI_LLM_PROVIDER="gemini"
```

**Note:** DockAI uses the Gemini API, not Vertex AI directly. For full Vertex AI support, use service account authentication.

## Anthropic Claude

Anthropic's Claude models offer strong reasoning and safety features.

### Setup

1. **Create account** at [console.anthropic.com](https://console.anthropic.com/)
2. **Add credits** (minimum $5)
3. **Generate API key** at [console.anthropic.com/settings/keys](https://console.anthropic.com/settings/keys)
4. **Set environment variables:**

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
export DOCKAI_LLM_PROVIDER="anthropic"
```

### Recommended Models

| Agent | Model | Cost (per 1M tokens) | Notes |
|-------|-------|---------------------|-------|
| Analyzer | `claude-3-5-haiku-latest` | Check pricing | Fast, cheap |
| Blueprint | `claude-sonnet-4-20250514` | Check pricing | Best reasoning |
| Generator | `claude-sonnet-4-20250514` | Check pricing | Excellent quality |
| Reflector | `claude-sonnet-4-20250514` | Check pricing | Strong reflection |

### Configuration

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
export DOCKAI_LLM_PROVIDER="anthropic"

# Recommended models
export DOCKAI_MODEL_ANALYZER="claude-3-5-haiku-latest"
export DOCKAI_MODEL_GENERATOR="claude-sonnet-4-20250514"
export DOCKAI_MODEL_REFLECTOR="claude-sonnet-4-20250514"
```

### Claude Features

- **Large Context**: Claude supports up to 200k tokens
- **Safety**: Built-in safety features reduce harmful outputs
- **Code Quality**: Excellent at understanding and generating code

## Azure OpenAI

Azure OpenAI is ideal for enterprise customers already using Azure.

### Setup

1. **Create Azure OpenAI resource** in [Azure Portal](https://portal.azure.com/)
2. **Deploy models** (e.g., gpt-4o-mini, gpt-4o)
3. **Get credentials:**
   - API Key: In "Keys and Endpoint" section
   - Endpoint: `https://your-resource.openai.azure.com/`
4. **Set environment variables:**

```bash
export AZURE_OPENAI_API_KEY="..."
export AZURE_OPENAI_ENDPOINT="https://your-resource.openai.azure.com/"
export AZURE_OPENAI_API_VERSION="2024-02-15-preview"
export DOCKAI_LLM_PROVIDER="azure"
```

### Model Deployments

Azure uses **deployment names**, not model names. You must create deployments in the Azure Portal first.

**Example:**
- Deployment: `gpt-4o-mini-deployment` → Model: `gpt-4o-mini`
- Deployment: `gpt-4o-deployment` → Model: `gpt-4o`

### Configuration

```bash
export AZURE_OPENAI_API_KEY="..."
export AZURE_OPENAI_ENDPOINT="https://your-resource.openai.azure.com/"
export AZURE_OPENAI_API_VERSION="2024-02-15-preview"
export DOCKAI_LLM_PROVIDER="azure"

# Use YOUR deployment names
export DOCKAI_MODEL_ANALYZER="gpt-4o-mini-deployment"
export DOCKAI_MODEL_GENERATOR="gpt-4o-deployment"
export DOCKAI_MODEL_REFLECTOR="gpt-4o-deployment"
```

### Azure Features

- **Enterprise Security**: VNet integration, private endpoints
- **Compliance**: HIPAA, SOC 2, ISO 27001
- **SLA**: 99.9% uptime guarantee
- **Regional Deployment**: Deploy in your preferred Azure region

## Ollama (Local)

Ollama allows you to run LLMs locally for free. Perfect for offline work or proprietary code.

### Setup

1. **Install Ollama:**

```bash
# macOS
brew install ollama

# Linux
curl -fsSL https://ollama.com/install.sh | sh

# Windows
# Download from https://ollama.com/download
```

2. **Start Ollama server:**

```bash
ollama serve
```

3. **Pull a model:**

```bash
# Recommended: Llama 3.1
ollama pull llama3.1

# Or other models
ollama pull qwen2.5
ollama pull codellama
```

4. **Configure DockAI:**

```bash
export DOCKAI_LLM_PROVIDER="ollama"
export OLLAMA_BASE_URL="http://localhost:11434"
export DOCKAI_MODEL_ANALYZER="llama3.1"
export DOCKAI_MODEL_GENERATOR="llama3.1"
```

### Recommended Models

| Model | Size | Quality | Speed | Notes |
|-------|------|---------|-------|-------|
| `llama3.1` | 8B | Good | Fast | Best all-around |
| `qwen2.5` | 7B | Excellent | Fast | Great for code |
| `codellama` | 13B | Good | Medium | Specialized for code |
| `llama3.1:70b` | 70B | Excellent | Slow | Requires powerful GPU |

### Configuration

```bash
export DOCKAI_LLM_PROVIDER="ollama"
export OLLAMA_BASE_URL="http://localhost:11434"

# Use same model for all agents (simplest)
export DOCKAI_MODEL_ANALYZER="llama3.1"
export DOCKAI_MODEL_GENERATOR="llama3.1"
export DOCKAI_MODEL_REFLECTOR="llama3.1"
```

### Performance Tips

- **Use GPU**: Ollama automatically uses GPU if available (NVIDIA, AMD, Apple Silicon)
- **Smaller models**: 7B-13B models work well for most projects
- **Increase context**: Some models support larger context
  ```bash
  # In Ollama Modelfile
  PARAMETER num_ctx 8192
  ```

### Limitations

- **Quality**: Local models are generally less capable than GPT-4 or Gemini 1.5 Pro
- **Speed**: Depends on your hardware (slower than cloud APIs on CPU)
- **Context**: Smaller context windows (4k-8k vs. 128k+)

**Recommendation:** Use Ollama for experimentation or if you have privacy concerns. For production, cloud models offer better quality.

## Provider Comparison

| Feature | OpenAI | Gemini | Anthropic | Azure OpenAI | Ollama |
|---------|--------|--------|-----------|--------------|--------|
| **Free Tier** | No | Yes (generous) | No | No | Yes (local) |
| **Quality** | ★★★★★ | ★★★★★ | ★★★★★ | ★★★★★ | ★★★☆☆ |
| **Speed** | ★★★★☆ | ★★★★★ | ★★★★☆ | ★★★★☆ | ★★☆☆☆ |
| **Cost (per run)** | $0.05 | $0.02 | $0.07 | $0.05 | $0.00 |
| **Context Size** | 128k | 1M | 200k | 128k | 8k-128k |
| **Privacy** | Cloud | Cloud | Cloud | Cloud | Local |
| **Best For** | General use | Cost-conscious | Safety-critical | Enterprise | Offline/Privacy |

## Troubleshooting

### "API key not found"

**OpenAI:**
```bash
export OPENAI_API_KEY="sk-proj-..."
echo $OPENAI_API_KEY  # Verify it's set
```

**Gemini:**
```bash
export GOOGLE_API_KEY="AIza..."
export DOCKAI_LLM_PROVIDER="gemini"
```

### "Rate limit exceeded"

**OpenAI:**
- Wait a few minutes
- Upgrade to pay-as-you-go (remove free tier limits)

**Gemini:**
- Free tier: 1500 requests/day (Flash), 50/day (Pro)
- Upgrade to paid tier for higher limits

**Workaround:**
```bash
export MAX_RETRIES="1"  # Reduce retries
```

### "Model not found" (Azure)

Azure uses deployment names, not model names:

```bash
# Wrong
export DOCKAI_MODEL_GENERATOR="gpt-4o"

# Correct (use your deployment name)
export DOCKAI_MODEL_GENERATOR="gpt-4o-deployment"
```

### "Connection refused" (Ollama)

Ensure Ollama is running:

```bash
ollama serve  # Start in one terminal
# In another terminal:
dockai build .
```

Or run as background service:

```bash
# macOS (launchd)
brew services start ollama

# Linux (systemd)
sudo systemctl start ollama
```

### "Authentication failed"

**OpenAI/Anthropic:**
- Verify API key is correct (no extra spaces)
- Check if account has credits

**Azure:**
- Verify endpoint URL (must include `https://`)
- Check API key permissions

**Gemini:**
- Ensure API key is from [aistudio.google.com](https://aistudio.google.com/), not GCP

### Mixed Providers

You can use different providers for different agents (not recommended, but possible):

```bash
export DOCKAI_LLM_PROVIDER="openai"
export OPENAI_API_KEY="sk-..."

# Override specific agents to use Gemini
export DOCKAI_MODEL_REFLECTOR="gemini-1.5-pro"
export GOOGLE_API_KEY="AIza..."
```

DockAI will auto-detect the provider based on the model name.

---

**Next**: See [Configuration](configuration.md) for advanced model configuration options.
