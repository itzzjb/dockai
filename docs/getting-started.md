# Getting Started with DockAI

This guide will help you get up and running with DockAI in minutes.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [First Run](#first-run)
- [Understanding the Output](#understanding-the-output)
- [Common Use Cases](#common-use-cases)
- [Troubleshooting](#troubleshooting)

## Prerequisites

Before installing DockAI, ensure you have:

### Required

1. **Python 3.10 or higher**
   ```bash
   python --version  # Should show 3.10+
   ```

2. **Docker** installed and running
   ```bash
   docker --version
   docker ps  # Should connect successfully
   ```

3. **LLM API Key** from at least one provider:
   - [OpenAI](https://platform.openai.com/api-keys) (Recommended for beginners)
   - [Google AI Studio](https://aistudio.google.com/app/apikey) (Best cost/performance)
   - [Anthropic](https://console.anthropic.com/settings/keys)
   - [Azure OpenAI](https://portal.azure.com/)
   - [Ollama](https://ollama.com/) (Free, local)

### Optional

- **Hadolint**: Dockerfile linter
  ```bash
  # macOS
  brew install hadolint
  
  # Linux
  wget https://github.com/hadolint/hadolint/releases/latest/download/hadolint-Linux-x86_64
  chmod +x hadolint-Linux-x86_64
  sudo mv hadolint-Linux-x86_64 /usr/local/bin/hadolint
  ```

- **Trivy**: Container security scanner
  ```bash
  # macOS
  brew install aquasecurity/trivy/trivy
  
  # Linux
  wget -qO - https://aquasecurity.github.io/trivy-repo/deb/public.key | sudo apt-key add -
  echo "deb https://aquasecurity.github.io/trivy-repo/deb $(lsb_release -sc) main" | sudo tee /etc/apt/sources.list.d/trivy.list
  sudo apt update && sudo apt install trivy
  ```

## Installation

### Option 1: Install from PyPI (Recommended)

```bash
pip install dockai-cli
```

Verify installation:
```bash
dockai version
# Should output: DockAI v4.0.7
```

### Option 2: Install from Source

```bash
# Clone the repository
git clone https://github.com/itzzjb/dockai.git
cd dockai

# Install in development mode
pip install -e .

# Or install with test dependencies
pip install -e ".[test]"
```

### Option 3: Using UV (Faster)

```bash
# Install uv if you don't have it
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install DockAI
uv pip install dockai-cli
```

## Configuration

### Step 1: Set Up Your LLM Provider

Choose one provider and set the required environment variables:

#### OpenAI (Default)

```bash
export OPENAI_API_KEY="sk-..."
```

#### Google Gemini

```bash
export GOOGLE_API_KEY="AIza..."
export DOCKAI_LLM_PROVIDER="gemini"
```

#### Anthropic Claude

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
export DOCKAI_LLM_PROVIDER="anthropic"
```

#### Azure OpenAI

```bash
export AZURE_OPENAI_API_KEY="..."
export AZURE_OPENAI_ENDPOINT="https://your-resource.openai.azure.com/"
export AZURE_OPENAI_API_VERSION="2024-02-15-preview"
export DOCKAI_LLM_PROVIDER="azure"

# Model deployments (use your deployment names)
export DOCKAI_MODEL_ANALYZER="gpt-4o-mini"
export DOCKAI_MODEL_GENERATOR="gpt-4o"
```

#### Ollama (Local, Free)

```bash
# First, install and start Ollama
ollama serve

# Pull a model
ollama pull llama3

# Configure DockAI
export DOCKAI_LLM_PROVIDER="ollama"
export OLLAMA_BASE_URL="http://localhost:11434"
export DOCKAI_MODEL_ANALYZER="llama3"
export DOCKAI_MODEL_GENERATOR="llama3"
```

### Step 2: Optional Configuration

```bash
# Skip security scanning for faster iteration
export DOCKAI_SKIP_SECURITY_SCAN="true"
export DOCKAI_SKIP_HADOLINT="true"

# Adjust retry limits
export MAX_RETRIES="3"

# Enable verbose logging
# (Use --verbose flag instead when running)
```

### Step 3: Create .env File (Optional but Recommended)

For persistent configuration, create a `.env` file in your project:

```bash
# .env
OPENAI_API_KEY=sk-...
DOCKAI_LLM_PROVIDER=openai
DOCKAI_SKIP_SECURITY_SCAN=false
MAX_RETRIES=3
```

DockAI will automatically load this file.

## First Run

### Basic Usage

```bash
# Navigate to your project
cd /path/to/your/project

# Generate Dockerfile
dockai build .
```

That's it! DockAI will:
1. Scan your project
2. Analyze the technology stack
3. Generate a Dockerfile
4. Validate it with Docker
5. Save it to `./Dockerfile`

### Example: Node.js Express App

```bash
# Create a sample project
mkdir my-express-app && cd my-express-app
npm init -y
npm install express

# Create app.js
cat > app.js << 'EOF'
const express = require('express');
const app = express();
const port = process.env.PORT || 3000;

app.get('/', (req, res) => {
  res.send('Hello World!');
});

app.get('/health', (req, res) => {
  res.status(200).json({ status: 'ok' });
});

app.listen(port, () => {
  console.log(`Server running on port ${port}`);
});
EOF

# Generate Dockerfile
dockai build .
```

**Expected Output:**

```
🔍 Scanning project...
✓ Found 3 files

🧠 Analyzing project with AI...
✓ Detected: Node.js Express application
✓ Entry point: app.js
✓ Dependencies: package.json
✓ Start command: node app.js

📖 Reading files with RAG (3 relevant chunks)...
✓ Context retrieved (8,234 tokens)

🏗️ Creating architectural blueprint...
✓ Multi-stage build planned
✓ Base image: node:18-alpine
✓ Health endpoint: /health

🔨 Generating Dockerfile...
✓ Dockerfile created (32 lines)

🔍 Reviewing security...
✓ No critical issues found

🧪 Validating with Docker...
✓ Image built successfully (142 MB)
✓ Hadolint: 0 errors, 0 warnings
✓ Trivy: 0 critical, 0 high vulnerabilities
✓ Container started (ID: abc123...)
✓ Health check passed (200 OK)

✅ Dockerfile generated successfully!
   Location: ./Dockerfile
   Image size: 142 MB
   
💰 Token Usage:
   Total: 12,450 tokens
   - Analyzer: 1,200 input, 300 output
   - Blueprint: 2,500 input, 800 output
   - Generator: 4,000 input, 1,200 output
```

### View the Generated Dockerfile

```bash
cat Dockerfile
```

**Sample Output:**

```dockerfile
# Build stage
FROM node:18-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production

# Production stage
FROM node:18-alpine
WORKDIR /app

# Copy dependencies from builder
COPY --from=builder /app/node_modules ./node_modules

# Copy application code
COPY . .

# Set NODE_ENV to production
ENV NODE_ENV=production

# Expose the application port
EXPOSE 3000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD node -e "require('http').get('http://localhost:3000/health', (r) => process.exit(r.statusCode === 200 ? 0 : 1))"

# Run as non-root user
USER node

# Start the application
CMD ["node", "app.js"]
```

## Understanding the Output

### Workflow Stages

DockAI runs through several stages, each indicated by an emoji:

| Emoji | Stage | Description |
|-------|-------|-------------|
| 🔍 | **Scan** | Fast directory traversal, builds file tree |
| 🧠 | **Analyze** | AI detects project type, stack, entry points |
| 📖 | **Read Files** | RAG retrieves relevant context |
| 🏗️ | **Blueprint** | AI plans build strategy and runtime config |
| 🔨 | **Generate** | AI writes the Dockerfile |
| 🔍 | **Review** | Security audit (optional, auto-skipped for scripts) |
| 🧪 | **Validate** | Docker build + Hadolint + Trivy + health check |
| 🤔 | **Reflect** | (Only on failure) AI analyzes errors and decides next steps |

### Success Indicators

- ✓ **Green checkmarks**: Step completed successfully
- ✗ **Red X**: Step failed (followed by detailed error)
- ⚠️ **Yellow warning**: Non-critical issue

### Error Handling

If validation fails, DockAI will:

1. **Reflect**: AI analyzes the error
2. **Decide**: 
   - Retry with a fixed Dockerfile
   - Re-analyze the project (if misunderstood)
   - Give up (if max retries reached)
3. **Retry**: Generate new Dockerfile and validate again

Example retry output:

```
🧪 Validating with Docker...
✗ Build failed: npm ERR! missing script: start

🤔 Reflecting on failure...
✓ Root cause: Missing start script in package.json
✓ Strategy: Add explicit start command

🔨 Generating improved Dockerfile (attempt 2/3)...
✓ Dockerfile updated

🧪 Validating with Docker...
✓ Build successful!
```

## Common Use Cases

### 1. Generate Dockerfile for Python Flask App

```bash
cd my-flask-app
dockai build .
```

DockAI will detect:
- Python version from `runtime.txt` or code
- Flask framework
- WSGI server (gunicorn recommended)
- Dependencies from `requirements.txt` or `pyproject.toml`

### 2. Multi-Language Project (e.g., Next.js + Python API)

```bash
# Generate for frontend
cd frontend
dockai build .

# Generate for backend
cd ../backend
dockai build .
```

Each Dockerfile will be tailored to its specific stack.

### 3. Custom Model Selection (Cost Optimization)

```bash
# Use cheaper models for analysis, powerful for generation
export DOCKAI_MODEL_ANALYZER="gpt-4o-mini"
export DOCKAI_MODEL_GENERATOR="gpt-4o"
export DOCKAI_MODEL_REFLECTOR="gemini-1.5-pro"

dockai build .
```

### 4. Skip Validation for Quick Iteration

```bash
# Faster generation, but no validation
export DOCKAI_SKIP_HADOLINT="true"
export DOCKAI_SKIP_SECURITY_SCAN="true"
export DOCKAI_SKIP_HEALTH_CHECK="true"

dockai build .
```

### 5. Strict Security Mode

```bash
# Fail on any vulnerability
export DOCKAI_STRICT_SECURITY="true"

dockai build .
```

### 6. Custom Instructions

```bash
# Add organization-specific requirements
export DOCKAI_GENERATOR_INSTRUCTIONS="Always use Alpine Linux. Pin all package versions. Include a maintainer label."

dockai build .
```

## Troubleshooting

### Issue: "OpenAI API key not found"

**Solution:**
```bash
export OPENAI_API_KEY="sk-..."
# Or create .env file with OPENAI_API_KEY=sk-...
```

### Issue: "Docker not found or not running"

**Solution:**
```bash
# Check if Docker is installed
docker --version

# Start Docker daemon (macOS/Windows)
# Open Docker Desktop

# Linux
sudo systemctl start docker
```

### Issue: "Build failed: Image exceeds size limit"

**Solution:**
```bash
# Increase the limit
export DOCKAI_MAX_IMAGE_SIZE_MB="1000"

# Or disable the check
export DOCKAI_MAX_IMAGE_SIZE_MB="0"

dockai build .
```

### Issue: "Rate limit exceeded" (OpenAI)

**Solution:**
- Wait a few minutes and retry
- Use a different provider (Gemini has higher free tier)
- Reduce retries: `export MAX_RETRIES="1"`

### Issue: "Generated Dockerfile doesn't work"

**Debugging steps:**

1. **Enable verbose logging:**
   ```bash
   dockai build . --verbose
   ```

2. **Check reflection output:** Look for the 🤔 Reflect stage to see what the AI identified as the issue

3. **Manually inspect the Dockerfile:** Sometimes the AI needs a hint
   ```bash
   # Add custom instructions
   export DOCKAI_GENERATOR_INSTRUCTIONS="Use Python 3.11. Install dependencies with pip install -r requirements.txt."
   dockai build .
   ```

4. **File an issue:** [GitHub Issues](https://github.com/itzzjb/dockai/issues) with:
   - Project type (language, framework)
   - Generated Dockerfile
   - Error logs (`--verbose` output)

### Issue: "RAG indexing is slow"

**Solution:**
```bash
# Use a smaller, faster embedding model
export DOCKAI_EMBEDDING_MODEL="paraphrase-MiniLM-L3-v2"

dockai build .
```

For very large projects (> 5000 files), indexing may take 10-20 seconds. This is a one-time cost per run.

## Next Steps

- **[Configuration Guide](configuration.md)**: Explore all 100+ configuration options
- **[Architecture](architecture.md)**: Understand how DockAI works under the hood
- **[LLM Providers](llm-providers.md)**: Detailed setup for each provider
- **[GitHub Actions](github-actions.md)**: Automate Dockerfile generation in CI/CD
- **[FAQ](faq.md)**: Common questions and advanced topics

---

**Happy Dockerizing! 🐳🤖**
