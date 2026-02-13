# FAQ - Frequently Asked Questions

## General

### What is DockAI?

DockAI is an AI-powered framework that automatically generates production-ready Dockerfiles for any codebase. It uses Large Language Models (LLMs) and Retrieval-Augmented Generation (RAG) to understand your project and create optimized, secure Dockerfiles.

### How is DockAI different from template-based generators?

DockAI doesn't use templates. Instead, it:
- **Understands your code** using RAG and AST analysis
- **Reasons about the best approach** using AI
- **Adapts to failures** by analyzing errors and trying new strategies
- **Validates everything** with Docker, Hadolint, and Trivy

### Is DockAI free?

DockAI itself is free and open-source (MIT License). However, you need an API key from an LLM provider:
- **Free Tier Available**: Google Gemini, Ollama (local)
- **Paid**: OpenAI, Anthropic, Azure OpenAI

Typical cost per generation: $0.02 - $0.10 depending on the model.

### What languages/frameworks does DockAI support?

DockAI supports virtually any language or framework:
- **JavaScript/TypeScript**: Node.js, React, Next.js, Vue, Angular, etc.
- **Python**: Flask, Django, FastAPI, etc.
- **Go**: Any Go application
- **Java**: Spring Boot, Maven, Gradle
- **Ruby**: Rails, Sinatra
- **PHP**: Laravel, Symfony
- **.NET**: ASP.NET Core
- **And more**: Rust, Elixir, Scala, etc.

If the project has code, DockAI can dockerize it!

## Usage

### Can I use DockAI for monorepos or multi-language projects?

Yes! Run DockAI separately for each component:

```bash
# Frontend
cd frontend
dockai build .

# Backend
cd ../backend
dockai build .
```

Each will get a tailored Dockerfile. For true monorepo support (single Dockerfile with multiple services), this is planned for a future release.

### Can DockAI update an existing Dockerfile?

Yes! If a `Dockerfile` already exists, DockAI will:
1. Read and analyze the existing Dockerfile
2. Use it as a reference when generating a new one
3. Preserve good patterns and fix issues

The existing Dockerfile is included in the RAG context automatically.

### How do I customize the generated Dockerfile?

You have several options:

**1. Custom Instructions (Recommended):**
```bash
export DOCKAI_GENERATOR_INSTRUCTIONS="Always use Alpine Linux. Pin all versions."
dockai build .
```

**2. Iterative Refinement:**
Edit the generated Dockerfile, run DockAI again. It will analyze your changes.

**3. Custom Prompts (Advanced):**
Completely replace agent prompts via environment variables or `.dockai/prompts/` files.

### Can I run DockAI in CI/CD?

Absolutely! DockAI is designed for automation:

**GitHub Actions:**
```yaml
- uses: itzzjb/dockai@v4
  with:
    openai_api_key: ${{ secrets.OPENAI_API_KEY }}
```

**GitLab CI, Jenkins, etc.:**
```bash
pip install dockai-cli
dockai build .
```

See [GitHub Actions Guide](github-actions.md) for details.

### How long does it take to generate a Dockerfile?

Typical times:
- **Small projects** (\< 50 files): 30-40 seconds
- **Medium projects** (50-500 files): 50-70 seconds
- **Large projects** (\> 500 files): 70-120 seconds

Bottlenecks:
- **RAG indexing**: 2-5 seconds (one-time per run)
- **LLM calls**: 3-10 seconds per agent
- **Docker build**: 20-60 seconds (validation)

To speed up iteration, skip validation:
```bash
export DOCKAI_SKIP_HADOLINT="true"
export DOCKAI_SKIP_SECURITY_SCAN="true"
```

## Technical

### What is RAG and why does DockAI use it?

**RAG (Retrieval-Augmented Generation)** is a technique where relevant context is retrieved from a knowledge base before sending it to the LLM.

**Why DockAI uses RAG:**
- **Precision**: Better Dockerfiles due to relevant context
- **Better Quality**: LLM gets focused context, not 10,000 lines of irrelevant code
- **Scalability**: Works on large projects (1000+ files)

**How it works in DockAI:**
1. Index all files with semantic embeddings
2. When generating, search for files relevant to the task
3. Send only top-k relevant chunks to the LLM

### Can I disable RAG?

RAG is always enabled in the CLI. The `DOCKAI_USE_RAG` environment variable is only used in the GitHub Action. When using the CLI, RAG is the default and only strategy — if RAG indexing fails, it automatically falls back to a simple "read all text files until token limit" strategy.

### What embedding model does DockAI use?

**Default:** `all-MiniLM-L6-v2` (sentence-transformers)
- 384-dimensional vectors
- Runs locally (no API cost)
- Fast (~500 sentences/sec on CPU)

**Alternatives:**
```bash
# Higher quality, slower
export DOCKAI_EMBEDDING_MODEL="all-mpnet-base-v2"

# Faster, smaller
export DOCKAI_EMBEDDING_MODEL="paraphrase-MiniLM-L3-v2"
```

### How does DockAI handle secrets?

DockAI **never** sends your secrets to the LLM:
- `.env` files are read for structure, not values
- Hardcoded secrets in code **are sent** (because they're in the code!)
- The Reviewer agent **detects** hardcoded secrets and warns you

**Best Practice:** Use environment variables, not hardcoded secrets.

### Can I use a local LLM?

Yes! Use Ollama:

```bash
ollama serve
ollama pull llama3

export DOCKAI_LLM_PROVIDER="ollama"
export DOCKAI_MODEL_ANALYZER="llama3"
export DOCKAI_MODEL_GENERATOR="llama3"

dockai build .
```

**Note:** Local models (even large ones) are generally less capable than cloud models like GPT-4 or Gemini 1.5 Pro. Expect lower quality.

### How much does DockAI cost per run?

Approximate costs (varies by project size):

| Provider | Model | Analyzer | Generator | Total |
|----------|-------|----------|-----------|-------|
| **OpenAI** | gpt-4o-mini + gpt-4o | $0.01 | $0.04 | **$0.05** |
| **Google** | gemini-1.5-flash + pro | $0.002 | $0.015 | **$0.02** |
| **Anthropic** | claude-3-5-haiku + claude-sonnet-4 | $0.01 | $0.06 | **$0.07** |
| **Ollama** | llama3 (default) | $0 | $0 | **$0** |

**Token Usage (Typical):**
- Analyzer: 1,200 input + 300 output
- Blueprint: 2,500 input + 800 output
- Generator: 4,000 input + 1,200 output
- Total: ~10,000 tokens

With retries, expect 1.5-2x tokens.

### Does DockAI send my code to third parties?

**Yes, if using cloud LLMs** (OpenAI, Google, Anthropic, Azure):
- File contents and analysis are sent to the LLM provider
- Covered by their privacy policies (OpenAI, Google, etc.)
- Data is **not** used for training (as of 2024 API terms)

**No, if using Ollama**:
- Everything runs locally
- No external API calls

**Recommendation:** Use cloud LLMs for public/open-source projects. Use Ollama for proprietary code if you have concerns.

## Troubleshooting

### Why does DockAI keep failing on my project?

Common reasons:

1. **Unusual project structure**: DockAI works best with conventional layouts (e.g., `package.json` at root for Node.js)
2. **Missing dependencies**: Ensure `requirements.txt`, `package.json`, `go.mod`, etc. are present
3. **Complex build process**: Multi-step builds, custom scripts may confuse the AI
4. **Max retries reached**: Try increasing `MAX_RETRIES`

**Debugging:**
```bash
dockai build . --verbose
```

Look at the reflection output (🤔 stage) to see what the AI identified as the issue.

### Why is the generated Dockerfile huge?

Possible causes:
1. **Base image choice**: AI selected a large base image (e.g., `ubuntu:latest` instead of `alpine`)
2. **Unnecessary dependencies**: Installing dev tools in production stage

**Solutions:**
```bash
# Guide the AI
export DOCKAI_GENERATOR_INSTRUCTIONS="Use Alpine Linux. Multi-stage build. Minimal dependencies."
dockai build .

# Or set size limit
export DOCKAI_MAX_IMAGE_SIZE_MB="200"
```

### DockAI generated a Dockerfile but it doesn't work when I run it manually

This usually means the validation passed but there's a runtime issue not caught by health checks.

**Common issues:**
- **Environment variables not set**: Add to `docker run` or use `--env-file`
- **Volumes not mounted**: Check if the app needs persistent data
- **Port mapping**: Use `-p 3000:3000` when running

**Debug:**
```bash
docker build -t myapp .
docker run -it --rm myapp  # Interactive mode to see errors
```

### Can DockAI generate Dockerfiles for Lambdas/serverless?

Not optimally. DockAI is designed for containerized applications (web apps, APIs, background workers).

For AWS Lambda, use the AWS-provided base images and tools. DockAI might generate a working Dockerfile, but it won't be optimized for Lambda's specific requirements.

### Why does RAG indexing take so long?

RAG indexing uses CPU-based embeddings, which can be slow for very large projects.

**Solutions:**
1. **Use a faster model:**
   ```bash
   export DOCKAI_EMBEDDING_MODEL="paraphrase-MiniLM-L3-v2"
   ```

2. **Reduce file count:** Add more patterns to `.gitignore` or `.dockerignore`

3. **Use `.dockerignore`** to exclude large non-essential directories (e.g., `data/`, `logs/`)

Typical indexing times:
- 100 files: ~1 second
- 500 files: ~3 seconds
- 2000 files: ~10 seconds

### How do I report a bug?

1. **Check existing issues**: [GitHub Issues](https://github.com/itzzjb/dockai/issues)
2. **Run with verbose logging:**
   ```bash
   dockai build . --verbose > debug.log 2>&1
   ```
3. **File a new issue** with:
   - Project type (language, framework)
   - Generated Dockerfile (if applicable)
   - Error logs from `debug.log`
   - DockAI version (`dockai version`)

## Best Practices

### What's the recommended workflow for using DockAI?

1. **Initial Generation:**
   ```bash
   dockai build .
   ```

2. **Review the Dockerfile:** Understand what was generated and why

3. **Test locally:**
   ```bash
   docker build -t myapp .
   docker run -p 3000:3000 myapp
   ```

4. **Iterate with instructions** if needed:
   ```bash
   export DOCKAI_GENERATOR_INSTRUCTIONS="Use Node 20. Add health check timeout of 10s."
   dockai build .
   ```

5. **Commit to version control**

6. **Automate in CI/CD** (optional)

### Should I commit the generated Dockerfile?

**Yes!** The Dockerfile is source code. Commit it to version control.

Benefits:
- **Reproducibility**: Anyone can build the same image
- **Review**: Team can review Dockerfile changes
- **Rollback**: Revert to previous version if needed

### Can I use DockAI for production?

**Yes, with review!** DockAI generates production-ready Dockerfiles, but:

1. **Always review** the generated Dockerfile
2. **Test thoroughly** in staging
3. **Monitor** in production (resource usage, security)
4. **Understand** what was generated (don't blindly trust AI)

DockAI is a tool to accelerate development, not replace engineering judgment.

### How do I keep my Dockerfiles up to date?

Re-run DockAI periodically:

```bash
# Every few months, or when you upgrade dependencies
dockai build .
```

DockAI will incorporate the existing Dockerfile and suggest improvements.

**Automation idea:** Run DockAI in CI, create a PR if the Dockerfile changes.

## Advanced

### Can I extend DockAI with custom agents?

Not currently in v4.0, but this is planned for a future release.

**Workaround:** Use custom prompts to completely override agent behavior.

### Can I use DockAI to generate docker-compose.yml?

Not yet. DockAI v4.0 only generates `Dockerfile`.

**Planned for v4.1:**
- `docker-compose.yml` generation
- `.dockerignore` generation

### How does DockAI decide when to reanalyze vs. retry?

The Reflector agent uses reasoning to decide:

**Retry (generate_node):**
- Build failed due to fixable Dockerfile issue
- Missing instruction (e.g., `EXPOSE`)
- Incorrect base image version

**Reanalyze (analyze_node):**
- Fundamental misunderstanding (e.g., thought it was Node.js but it's Python)
- Entry point completely wrong
- Missing critical context

**Give Up:**
- Max retries reached
- Unsolvable issue (e.g., project requires manual setup)

### Can I contribute to DockAI?

Absolutely! DockAI is open-source.

**Ways to contribute:**
- **Report bugs**: [GitHub Issues](https://github.com/itzzjb/dockai/issues)
- **Suggest features**: [GitHub Discussions](https://github.com/itzzjb/dockai/discussions)
- **Submit PRs**: See [CONTRIBUTING.md](../CONTRIBUTING.md)
- **Improve docs**: Documentation PRs are always welcome!

### What's next for DockAI?

**Roadmap for v4.1 - v5.0:**
- Docker Compose generation
- .dockerignore generation
- Persistent RAG index (cache embeddings)
- Web UI
- Plugin system
- Multi-Dockerfile projects (monorepo support)
- Advanced optimization advisor

Follow progress on [GitHub](https://github.com/itzzjb/dockai).

---

**Have a question not answered here?** [Ask in GitHub Discussions](https://github.com/itzzjb/dockai/discussions)
