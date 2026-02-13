# Using DockAI in GitHub Actions

This guide shows you how to integrate DockAI into your GitHub Actions workflows for automated Dockerfile generation.

## Table of Contents

- [Quick Start](#quick-start)
- [Configuration Options](#configuration-options)
- [Example Workflows](#example-workflows)
- [Advanced Usage](#advanced-usage)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)

## Quick Start

Add DockAI to your GitHub Actions workflow in `.github/workflows/dockerize.yml`:

```yaml
name: Generate Dockerfile

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]
  workflow_dispatch:  # Manual trigger

jobs:
  dockerize:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Generate Dockerfile with DockAI
        uses: itzzjb/dockai@v4
        with:
          openai_api_key: ${{ secrets.OPENAI_API_KEY }}
          project_path: '.'

      - name: Upload Dockerfile
        uses: actions/upload-artifact@v4
        with:
          name: dockerfile
          path: Dockerfile
```

### Setup Secrets

1. Go to your repository → **Settings** → **Secrets and variables** → **Actions**
2. Click **New repository secret**
3. Add your API key:
   - Name: `OPENAI_API_KEY`
   - Value: `sk-proj-...`

## Configuration Options

### Minimal Configuration

```yaml
- uses: itzzjb/dockai@v4
  with:
    openai_api_key: ${{ secrets.OPENAI_API_KEY }}
```

### Full Configuration

```yaml
- uses: itzzjb/dockai@v4
  with:
    # LLM Provider
    llm_provider: 'gemini'
    google_api_key: ${{ secrets.GOOGLE_API_KEY }}
    
    # Model Selection
    model_analyzer: 'gemini-1.5-flash'
    model_generator: 'gemini-1.5-pro'
    
    # Validation
    skip_hadolint: 'false'
    skip_security_scan: 'false'
    strict_security: 'true'
    max_image_size_mb: '500'
    
    # Retry
    max_retries: '3'
    
    # RAG
    use_rag: 'true'
    embedding_model: 'all-MiniLM-L6-v2'
    
    # Custom Instructions
    generator_instructions: |
      Always use Alpine Linux.
      Pin all package versions.
      Add MAINTAINER label with team email.
    
    # Observability
    enable_tracing: 'true'
    langchain_tracing_v2: 'true'
    langchain_api_key: ${{ secrets.LANGSMITH_API_KEY }}
```

### Input Parameters Reference

See [`action.yml`](../action.yml) for the complete list of inputs. All inputs from the CLI are available, including:

- **LLM Provider**: `llm_provider`, `openai_api_key`, `google_api_key`, `anthropic_api_key`, etc.
- **Model Selection**: `model_analyzer`, `model_generator`, `model_reflector`, etc.
- **Validation**: `skip_hadolint`, `skip_security_scan`, `strict_security`, etc.
- **Custom Instructions**: `analyzer_instructions`, `generator_instructions`, etc.
- **Custom Prompts**: `prompt_analyzer`, `prompt_generator`, etc.

## Example Workflows

### 1. Generate and Commit Dockerfile

Automatically generate a Dockerfile and commit it to the repository:

```yaml
name: Generate and Commit Dockerfile

on:
  push:
    branches: [ main ]
    paths:
      - 'package.json'
      - 'requirements.txt'
      - 'go.mod'
      - '.github/workflows/dockerize.yml'

jobs:
  dockerize:
    runs-on: ubuntu-latest
    permissions:
      contents: write  # Required for pushing
    steps:
      - uses: actions/checkout@v4

      - name: Generate Dockerfile
        uses: itzzjb/dockai@v4
        with:
          openai_api_key: ${{ secrets.OPENAI_API_KEY }}

      - name: Commit Dockerfile
        run: |
          git config user.name "DockAI Bot"
          git config user.email "bot@dockai.ai"
          git add Dockerfile
          git diff-index --quiet HEAD || git commit -m "chore: update Dockerfile (DockAI)"
          git push
```

### 2. Create Pull Request

Generate a Dockerfile and create a PR for review:

```yaml
name: Generate Dockerfile PR

on:
  workflow_dispatch:
  schedule:
    - cron: '0 0 * * 1'  # Weekly on Monday

jobs:
  dockerize:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Generate Dockerfile
        uses: itzzjb/dockai@v4
        with:
          google_api_key: ${{ secrets.GOOGLE_API_KEY }}
          llm_provider: 'gemini'

      - name: Create Pull Request
        uses: peter-evans/create-pull-request@v5
        with:
          token: ${{ secrets.GITHUB_TOKEN }}
          commit-message: 'chore(docker): update Dockerfile'
          title: 'Update Dockerfile (DockAI)'
          body: |
            This PR updates the Dockerfile using DockAI.
            
            Please review the changes and merge if acceptable.
          branch: dockai/update-dockerfile
          delete-branch: true
```

### 3. Multi-Service Monorepo

Generate Dockerfiles for multiple services:

```yaml
name: Generate Dockerfiles (Monorepo)

on:
  push:
    branches: [ main ]

jobs:
  dockerize:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        service: [frontend, backend, worker]
    steps:
      - uses: actions/checkout@v4

      - name: Generate Dockerfile for ${{ matrix.service }}
        uses: itzzjb/dockai@v4
        with:
          openai_api_key: ${{ secrets.OPENAI_API_KEY }}
          project_path: './services/${{ matrix.service }}'

      - name: Upload Dockerfile
        uses: actions/upload-artifact@v4
        with:
          name: dockerfile-${{ matrix.service }}
          path: services/${{ matrix.service }}/Dockerfile
```

### 4. Build and Push Docker Image

Generate Dockerfile, build image, and push to registry:

```yaml
name: Build and Push Docker Image

on:
  push:
    branches: [ main ]
    tags: [ 'v*' ]

jobs:
  dockerize-and-build:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write
    steps:
      - uses: actions/checkout@v4

      - name: Generate Dockerfile
        uses: itzzjb/dockai@v4
        with:
          openai_api_key: ${{ secrets.OPENAI_API_KEY }}
          skip_security_scan: 'false'  # Enable security scan
          strict_security: 'true'      # Fail on vulnerabilities

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Login to GitHub Container Registry
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Extract metadata
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: ghcr.io/${{ github.repository }}
          tags: |
            type=ref,event=branch
            type=semver,pattern={{version}}
            type=semver,pattern={{major}}.{{minor}}

      - name: Build and push
        uses: docker/build-push-action@v5
        with:
          context: .
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
```

### 5. Cost Optimization Strategy

Use cheap models for analysis, powerful for generation:

```yaml
- name: Generate Dockerfile (Cost Optimized)
  uses: itzzjb/dockai@v4
  with:
    llm_provider: 'gemini'
    google_api_key: ${{ secrets.GOOGLE_API_KEY }}
    
    # Use Flash for analysis (cheap)
    model_analyzer: 'gemini-1.5-flash'
    
    # Use Pro for generation (quality)
    model_generator: 'gemini-1.5-pro'
    
    # Use experimental model for reflection (free)
    model_reflector: 'gemini-2.0-flash-exp'
```

## Advanced Usage

### Conditional Execution

Only run DockAI when dependencies change:

```yaml
on:
  push:
    paths:
      - 'package.json'
      - 'requirements.txt'
      - 'go.mod'
      - 'Cargo.toml'
```

### Matrix Strategy for Multiple Providers

Test with different providers:

```yaml
strategy:
  matrix:
    provider:
      - name: openai
        key_var: OPENAI_API_KEY
      - name: gemini
        key_var: GOOGLE_API_KEY

steps:
  - uses: itzzjb/dockai@v4
    with:
      llm_provider: ${{ matrix.provider.name }}
      openai_api_key: ${{ secrets[matrix.provider.key_var] }}
```

### Custom Instructions from Repository

Store instructions in a file:

```yaml
- name: Load custom instructions
  id: instructions
  run: |
    echo "content<<EOF" >> $GITHUB_OUTPUT
    cat .dockai/generator_instructions.txt >> $GITHUB_OUTPUT
    echo "EOF" >> $GITHUB_OUTPUT

- uses: itzzjb/dockai@v4
  with:
    openai_api_key: ${{ secrets.OPENAI_API_KEY }}
    generator_instructions: ${{ steps.instructions.outputs.content }}
```

### Observability with LangSmith

Track all runs in LangSmith:

```yaml
- uses: itzzjb/dockai@v4
  with:
    openai_api_key: ${{ secrets.OPENAI_API_KEY }}
    
    # Enable LangSmith tracing
    langchain_tracing_v2: 'true'
    langchain_api_key: ${{ secrets.LANGSMITH_API_KEY }}
    langchain_project: 'dockai-ci'
```

## Best Practices

### 1. Use Repository Secrets

Never hardcode API keys:

```yaml
# ❌ Bad
with:
  openai_api_key: 'sk-proj-abc123'

# ✅ Good
with:
  openai_api_key: ${{ secrets.OPENAI_API_KEY }}
```

### 2. Pin Action Version

Use a specific version, not `@main`:

```yaml
# ❌ Bad (breaks on updates)
uses: itzzjb/dockai@main

# ✅ Good
uses: itzzjb/dockai@v4

# ✅ Better (specific patch version)
uses: itzzjb/dockai@v4.0.7
```

### 3. Enable Security Scanning

Always enable security checks in CI:

```yaml
with:
  skip_hadolint: 'false'
  skip_security_scan: 'false'
  strict_security: 'true'
```

### 4. Review Before Merging

Use PRs for review:

```yaml
- uses: peter-evans/create-pull-request@v5
  # ... creates PR for review
```

Don't auto-commit to `main` without review!

### 5. Cache Docker Layers

Speed up builds with layer caching:

```yaml
- uses: docker/build-push-action@v5
  with:
    cache-from: type=gha
    cache-to: type=gha,mode=max
```

### 6. Limit Retries in CI

Reduce costs and CI time:

```yaml
with:
  max_retries: '2'  # Default is 3
```

## Troubleshooting

### "Error: API key not found"

**Solution:** Add the secret to your repository:
1. Go to Settings → Secrets → Actions
2. Add `OPENAI_API_KEY` or your provider's key

### "Docker build failed"

The generated Dockerfile is invalid. Check:
1. Action logs for error details
2. Try running locally: `dockai build . --verbose`
3. Review the reflection output

### "Rate limit exceeded"

This is the most common issue when using OpenAI's free or lower-tier API in GitHub Actions.

**Root Causes:**
- OpenAI free tier has very strict rate limits (especially for GPT-4o)
- Multiple concurrent workflow runs hitting the API simultaneously
- RAG embedding generation adds to request count
- Retries amplify the problem (5 retries = 5x requests)

**Solutions (in order of effectiveness):**

#### 1. Switch to Gemini (Recommended) 🌟

```yaml
- uses: itzzjb/dockai@v4
  with:
    llm_provider: 'gemini'
    google_api_key: ${{ secrets.GOOGLE_API_KEY }}
    model_analyzer: 'gemini-1.5-flash'
    model_generator: 'gemini-1.5-pro'
```

**Why this works:**
- Gemini free tier: 1,500 requests/day
- OpenAI free tier: Much lower limits (varies by tier)
- Gemini has similar quality to GPT-4o for Dockerfile generation

#### 2. Add Concurrency Control

Prevent multiple workflow runs from hitting the API at once:

```yaml
concurrency:
  group: dockai-${{ github.ref }}
  cancel-in-progress: false  # Queue, don't cancel
```

Add this to your job or workflow level.

#### 3. Reduce Retries

Fail fast instead of retrying 5 times:

```yaml
with:
  max_retries: '1'  # Default is 3
```

#### 4. Upgrade OpenAI Tier

If you must use OpenAI, upgrade to Tier 1 or higher for better rate limits.

#### 5. Conditional Execution

Only run on specific file changes:

```yaml
on:
  push:
    paths:
      - 'package.json'
      - 'requirements.txt'
      - 'src/**'
```

#### 6. Add Manual Retry Logic (Last Resort)

```yaml
- uses: itzzjb/dockai@v4
  id: dockai_attempt1
  continue-on-error: true
  with:
    openai_api_key: ${{ secrets.OPENAI_API_KEY }}
  timeout-minutes: 15

- name: Wait and retry if failed
  if: failure()
  run: sleep 60

- name: Retry DockAI
  if: failure()
  uses: itzzjb/dockai@v4
  with:
    openai_api_key: ${{ secrets.OPENAI_API_KEY }}
```

### "Permission denied" when pushing

Add write permissions:

```yaml
permissions:
  contents: write
```

### Action times out

Increase timeout:

```yaml
- uses: itzzjb/dockai@v4
  timeout-minutes: 20  # Default is usually 10
```

Or skip validation for faster execution:

```yaml
with:
  skip_hadolint: 'true'
  skip_security_scan: 'true'
```

## Cost Estimates

GitHub Actions usage:

| Workflow | Frequency | DockAI Time | GitHub Minutes | LLM Cost |
|----------|-----------|-------------|----------------|----------|
| On every push | 10/day | 1 min | 10 min/day | $0.50/day |
| PR only | 2/day | 1 min | 2 min/day | $0.10/day |
| Weekly | 1/week | 1 min | 4 min/month | $0.30/month |

**Free Tier:**
- GitHub: 2,000 minutes/month (Free tier)
- Gemini: 1,500 requests/day (Free tier)

**Recommendation:** Use Gemini for CI to stay in free tiers.

## Examples Repository

For more examples, see:
- [DockAI Examples](https://github.com/itzzjb/dockai/tree/main/examples)
- [GitHub Actions Marketplace](https://github.com/marketplace/actions/dockai)

---

**Next**: See [Configuration](configuration.md) for detailed environment variable reference.
