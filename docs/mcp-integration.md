# MCP Integration Guide

This guide explains how to use DockAI with the Model Context Protocol (MCP) for conversational Dockerfile generation.

## Table of Contents

- [What is MCP?](#what-is-mcp)
- [Why Use DockAI with MCP?](#why-use-dockai-with-mcp)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage with Claude Desktop](#usage-with-claude-desktop)
- [Usage with Other MCP Clients](#usage-with-other-mcp-clients)
- [Available MCP Tools](#available-mcp-tools)
- [Examples](#examples)
- [Troubleshooting](#troubleshooting)

## What is MCP?

**Model Context Protocol (MCP)** is an open standard that enables AI assistants (like Claude, GPT, etc.) to securely interact with external tools and data sources. It provides a standardized way for AI models to:

- Execute local commands and scripts
- Access file systems
- Call APIs and external services
- Use specialized tools like DockAI

Learn more: [Model Context Protocol Documentation](https://modelcontextprotocol.io)

## Why Use DockAI with MCP?

Using DockAI through MCP provides a **conversational interface** for Dockerfile generation:

### **Traditional CLI Workflow:**
```bash
$ dockai build .
# Generates Dockerfile automatically
```

### **MCP-Enhanced Workflow:**
```
You: Can you dockerize this Node.js project?
Claude: I'll use DockAI to analyze your project and generate a Dockerfile...
        [Executes DockAI via MCP]
        I've created a multi-stage Dockerfile for your Express app with:
        - Node.js 18 Alpine base
        - Health checks on /health endpoint
        - Non-root user configuration
        - Security best practices
        
        Would you like me to explain any part or make adjustments?
```

### **Benefits:**

1. **Natural Language Interface** - Ask questions and get explanations
2. **Iterative Refinement** - "Make it use Python 3.11" → instant adjustment
3. **Contextual Understanding** - Claude can read your code and suggest improvements
4. **Multi-Tool Workflows** - Combine DockAI with other MCP tools
5. **Learning Mode** - Ask "Why did you choose this base image?"

## Prerequisites

### Required

- **Python 3.10+** installed
- **Docker** installed and running
- **DockAI** installed (`pip install dockai-cli`)
- **MCP-compatible client** (Claude Desktop, VSCode with MCP, etc.)
- **LLM API Key** (OpenAI, Google, Anthropic, etc.)

### Recommended

- **uvx** for easier installation:
  ```bash
  curl -LsSf https://astral.sh/uv/install.sh | sh
  ```

## Installation

DockAI can be used as an MCP server in two ways:

### Option 1: Using uvx (Recommended)

**Advantages:**
- No manual installation needed
- Automatic dependency management
- Works immediately

**Configuration** (added to MCP client config):
```json
{
  "mcpServers": {
    "dockai": {
      "command": "uvx",
      "args": ["dockai-cli"]
    }
  }
}
```

### Option 2: Using Installed Package

**Advantages:**
- Faster startup (no download on first run)
- Use specific version

**Installation:**
```bash
pip install dockai-cli
# or
uv pip install dockai-cli
```

**Configuration** (added to MCP client config):
```json
{
  "mcpServers": {
    "dockai": {
      "command": "python",
      "args": ["-m", "dockai.core.mcp_server"]
    }
  }
}
```

## Configuration

### Claude Desktop Configuration

**1. Locate Claude's configuration file:**

```bash
# macOS
~/Library/Application Support/Claude/claude_desktop_config.json

# Windows
%APPDATA%\Claude\claude_desktop_config.json

# Linux
~/.config/Claude/claude_desktop_config.json
```

**2. Edit the configuration file:**

```json
{
  "mcpServers": {
    "dockai": {
      "command": "uvx",
      "args": ["dockai-cli"],
      "env": {
        "OPENAI_API_KEY": "sk-your-api-key-here",
        "DOCKAI_LLM_PROVIDER": "openai"
      }
    }
  }
}
```

**3. Restart Claude Desktop**

### Environment Variables in MCP

You can configure DockAI through environment variables in the MCP config:

```json
{
  "mcpServers": {
    "dockai": {
      "command": "uvx",
      "args": ["dockai-cli"],
      "env": {
        "OPENAI_API_KEY": "sk-...",
        "DOCKAI_LLM_PROVIDER": "openai",
        "DOCKAI_MODEL_ANALYZER": "gpt-4o-mini",
        "DOCKAI_MODEL_GENERATOR": "gpt-4o",
        "MAX_RETRIES": "3",
        "DOCKAI_USE_RAG": "true",
        "DOCKAI_SKIP_SECURITY_SCAN": "false"
      }
    }
  }
}
```

**Security Note:** Avoid putting API keys directly in config files in production. Use environment variables or secret management tools.

### Using Different LLM Providers

**Google Gemini:**
```json
{
  "mcpServers": {
    "dockai": {
      "command": "uvx",
      "args": ["dockai-cli"],
      "env": {
        "GOOGLE_API_KEY": "AIza...",
        "DOCKAI_LLM_PROVIDER": "gemini",
        "DOCKAI_MODEL_ANALYZER": "gemini-1.5-flash",
        "DOCKAI_MODEL_GENERATOR": "gemini-1.5-pro"
      }
    }
  }
}
```

**Anthropic Claude:**
```json
{
  "mcpServers": {
    "dockai": {
      "command": "uvx",
      "args": ["dockai-cli"],
      "env": {
        "ANTHROPIC_API_KEY": "sk-ant-...",
        "DOCKAI_LLM_PROVIDER": "anthropic"
      }
    }
  }
}
```

**Ollama (Local):**
```json
{
  "mcpServers": {
    "dockai": {
      "command": "uvx",
      "args": ["dockai-cli"],
      "env": {
        "DOCKAI_LLM_PROVIDER": "ollama",
        "OLLAMA_BASE_URL": "http://localhost:11434",
        "DOCKAI_MODEL_ANALYZER": "llama3.1",
        "DOCKAI_MODEL_GENERATOR": "llama3.1"
      }
    }
  }
}
```

## Usage with Claude Desktop

### Step 1: Start a Conversation

Open Claude Desktop and start a new conversation:

```
You: I have a Node.js Express project that I need to dockerize. Can you help?
```

### Step 2: Claude Uses DockAI

Claude will automatically detect that it can use DockAI and offer to help:

```
Claude: I can help you create a Dockerfile for your Node.js Express project 
        using DockAI. I'll analyze your project structure and generate an 
        optimized, production-ready Dockerfile.
        
        What's the path to your project?
```

### Step 3: Provide Project Path

```
You: It's in /Users/username/projects/my-express-app
```

### Step 4: DockAI Generates Dockerfile

Claude will use DockAI via MCP:

```
Claude: [Using DockAI tool]
        
        I've analyzed your project and generated a Dockerfile. Here's what 
        I created:
        
        - Multi-stage build with Node.js 18 Alpine
        - Separate builder stage for dependencies
        - Production stage runs as non-root user
        - Health check configured for /health endpoint
        - Optimized layer caching for faster rebuilds
        
        The Dockerfile has been saved to your project directory and validated 
        successfully. The final image size is 142 MB.
        
        Would you like me to explain any specific part?
```

### Step 5: Iterate and Refine

```
You: Can you modify it to use Node.js 20 instead?

Claude: I'll update the Dockerfile to use Node.js 20...
        [Updates and regenerates]
        Done! I've updated the base image to node:20-alpine.
```

## Usage with Other MCP Clients

### VSCode with MCP Extension

**1. Install MCP extension for VSCode**

**2. Configure in `.vscode/mcp.json`:**

```json
{
  "mcpServers": {
    "dockai": {
      "command": "uvx",
      "args": ["dockai-cli"],
      "env": {
        "OPENAI_API_KEY": "${env:OPENAI_API_KEY}"
      }
    }
  }
}
```

**3. Use in VSCode Chat:**

- Open VSCode Chat panel
- Type: `@mcp dockai build .`
- DockAI generates Dockerfile in current workspace

### Custom MCP Client

If you're building your own MCP client:

```python
import mcp

# Connect to DockAI MCP server
client = mcp.Client()
await client.connect("dockai", {
    "command": "uvx",
    "args": ["dockai-cli"]
})

# List available tools
tools = await client.list_tools()
print(tools)  # ['analyze_project', 'generate_dockerfile_content', 'validate_dockerfile', 'run_full_workflow']

# Analyze a project
analysis = await client.call_tool("analyze_project", {
    "path": "/path/to/project"
})
print(analysis)

# Generate a Dockerfile
dockerfile = await client.call_tool("generate_dockerfile_content", {
    "path": "/path/to/project",
    "instructions": "Use Alpine base image"
})
print(dockerfile)

# Run the full workflow (analyze, generate, validate, retry)
result = await client.call_tool("run_full_workflow", {
    "path": "/path/to/project"
})
print(result)
```

## Available MCP Tools

When DockAI is running as an MCP server, it exposes the following tools:

### `analyze_project`

**Description:** Analyzes a project directory to determine Docker requirements without generating a Dockerfile.

**Parameters:**
- `path` (string, required): Absolute path to the project directory

**Returns:**
- A text summary including detected stack, project type, build/start commands, suggested base image, and critical files

### `generate_dockerfile_content`

**Description:** Generates a production-ready Dockerfile for the given project. Does NOT write to disk — returns the Dockerfile content as text.

**Parameters:**
- `path` (string, required): Absolute path to the project directory
- `instructions` (string, optional): Custom instructions (e.g., "Use Alpine", "Expose port 3000")

**Returns:**
- The generated Dockerfile content as a string

**Example:**
```json
{
  "path": "/Users/username/projects/my-app",
  "instructions": "Use Node.js 20 Alpine"
}
```

### `validate_dockerfile`

**Description:** Validates a Dockerfile by building and running it against the project.

**Parameters:**
- `path` (string, required): Absolute path to the project directory (build context)
- `dockerfile_content` (string, required): The Dockerfile content to validate

**Returns:**
- A validation result message (e.g., "Validation Success: ..." or "Validation Failed: ...")

### `run_full_workflow`

**Description:** Executes the full DockAI agentic workflow — identical to the CLI `dockai build` command. Runs the complete pipeline: Scan → Analyze → Plan → Generate → Validate → Fix (up to 3 retries).

**Parameters:**
- `path` (string, required): Absolute path to the project directory
- `instructions` (string, optional): Custom instructions for the agents

**Returns:**
- A summary including the final Dockerfile content, validation status, and retry count

## Examples

### Example 1: Basic Dockerfile Generation

**User:**
```
Generate a Dockerfile for my Python Flask app in ~/projects/flask-api
```

**Claude:**
```
I'll use DockAI to create a Dockerfile for your Flask application.

[Executes: run_full_workflow with path ~/projects/flask-api]

I've created a production-ready Dockerfile for your Flask API with:
- Python 3.11 slim base image
- Multi-stage build for smaller image size
- Gunicorn WSGI server
- Health check on default route
- Non-root user (uid 1000)
- Image size: 89 MB

The Dockerfile passed all validations:
✓ Hadolint: No issues
✓ Trivy: No critical vulnerabilities
✓ Docker build: Successful
✓ Container test: Passed
```

### Example 2: Iterative Refinement

**User:**
```
I need a Dockerfile for my Go API, but it must:
- Use Go 1.21
- Run on port 8080
- Include health checks
- Be under 50MB
```

**Claude:**
```
I'll create a highly optimized Dockerfile for your Go API with those requirements.

[Executes DockAI with custom instructions]

Done! I've generated a Dockerfile that meets all your requirements:

✓ Go 1.21 (golang:1.21-alpine builder)
✓ Port 8080 (EXPOSE 8080)
✓ Health check (/health endpoint)
✓ Final image: 24 MB (from scratch base)

The build uses multi-stage compilation:
1. Builder stage: Compiles Go binary
2. Runtime stage: Copies binary to scratch (minimal image)

Would you like me to explain the optimization techniques used?
```

### Example 3: Explaining Choices

**User:**
```
Why did you choose Alpine over Ubuntu?
```

**Claude:**
```
I chose Alpine Linux as the base image for several reasons:

1. Size: Alpine is ~5MB vs Ubuntu ~77MB
2. Security: Smaller attack surface, fewer packages
3. Performance: Faster pulls and deployments
4. Best Practice: Industry standard for production containers

For your Node.js app, node:18-alpine provides:
- Node.js 18 runtime
- npm/yarn package managers  
- Only essential libraries

This results in:
- Builder stage: ~180MB
- Final image: ~140MB (vs ~350MB with Ubuntu)

Would you like me to switch to Ubuntu if you have specific requirements?
```

### Example 4: Multi-Project Workflow

**User:**
```
I have a monorepo with 3 services:
- frontend (React)
- backend (Node.js)
- worker (Python)

Can you dockerize all of them?
```

**Claude:**
```
I'll create Dockerfiles for each service in your monorepo.

[Executes DockAI for each service]

Done! I've generated optimized Dockerfiles for all three services:

1. frontend/Dockerfile (React)
   - Node.js 18 with nginx for static serving
   - Multi-stage: build → serve
   - Size: 45 MB

2. backend/Dockerfile (Node.js)
   - Node.js 18 Alpine
   - PM2 for process management
   - Size: 156 MB

3. worker/Dockerfile (Python)
   - Python 3.11 slim
   - Celery worker configuration
   - Size: 178 MB

All Dockerfiles are production-ready and validated. Would you like me to 
create a docker-compose.yml to orchestrate them?
```

## Troubleshooting

### Issue: MCP Server Not Found

**Symptom:**
```
Error: Could not connect to MCP server 'dockai'
```

**Solutions:**

1. **Verify uvx/dockai is installed:**
   ```bash
   uvx dockai-cli --version
   # or
   dockai --version
   ```

2. **Check MCP configuration syntax:**
   - Ensure JSON is valid (no trailing commas)
   - Verify quotes are correct
   - Check file is saved

3. **Restart MCP client** (Claude Desktop, VSCode, etc.)

### Issue: API Key Not Working

**Symptom:**
```
Error: OPENAI_API_KEY not found
```

**Solutions:**

1. **Add API key to MCP config:**
   ```json
   "env": {
     "OPENAI_API_KEY": "sk-..."
   }
   ```

2. **Verify API key is valid:**
   ```bash
   curl https://api.openai.com/v1/models \
     -H "Authorization: Bearer sk-..."
   ```

3. **Check environment variable precedence:**
   - MCP config env vars override system env vars
   - System env vars override .env file

### Issue: Dockerfile Generation Fails

**Symptom:**
```
DockAI failed to generate Dockerfile
```

**Solutions:**

1. **Enable verbose mode in MCP config:**
   ```json
   "env": {
     "DOCKAI_VERBOSE": "true"
   }
   ```

2. **Check Docker is running:**
   ```bash
   docker ps
   ```

3. **Verify project path is correct:**
   - Use absolute paths
   - Ensure directory exists
   - Check permissions

### Issue: Slow Performance

**Symptom:**
DockAI takes too long through MCP

**Solutions:**

1. **Use pre-installed package instead of uvx:**
   ```bash
   pip install dockai-cli
   ```
   Then update MCP config:
   ```json
   "command": "dockai"
   ```

2. **Disable validation for faster iteration:**
   ```json
   "env": {
     "DOCKAI_SKIP_HADOLINT": "true",
     "DOCKAI_SKIP_SECURITY_SCAN": "true"
   }
   ```

3. **Use faster LLM models:**
   ```json
   "env": {
     "DOCKAI_MODEL_ANALYZER": "gpt-4o-mini",
     "DOCKAI_MODEL_GENERATOR": "gpt-4o-mini"
   }
   ```

### Issue: MCP Client Doesn't See DockAI Tools

**Symptom:**
Claude doesn't offer to use DockAI

**Solutions:**

1. **Manually trigger tool discovery:**
   ```
   You: Use DockAI to build a Dockerfile for my project
   ```

2. **Check MCP server status** in Claude Desktop:
   - Click Settings → Developer → MCP Servers
   - Verify "dockai" shows as "Connected"

3. **Restart Claude Desktop** completely (Cmd+Q on macOS)

## Best Practices

### 1. Use Environment Variables for Secrets

**Don't:**
```json
{
  "env": {
    "OPENAI_API_KEY": "sk-proj-abc123..."  ❌
  }
}
```

**Do:**
```json
{
  "env": {
    "OPENAI_API_KEY": "${env:OPENAI_API_KEY}"  ✅
  }
}
```

Then set in your shell:
```bash
export OPENAI_API_KEY="sk-proj-..."
```

### 2. Configure Model Selection

Optimize cost vs. quality:

```json
{
  "env": {
    "DOCKAI_MODEL_ANALYZER": "gemini-1.5-flash",    // Fast, cheap
    "DOCKAI_MODEL_GENERATOR": "gemini-1.5-pro",     // High quality
    "DOCKAI_MODEL_REFLECTOR": "gemini-2.0-flash-exp" // Best reasoning
  }
}
```

### 3. Enable Only Needed Validations

For faster iteration during development:

```json
{
  "env": {
    "DOCKAI_SKIP_HADOLINT": "false",        // Keep linting
    "DOCKAI_SKIP_SECURITY_SCAN": "true",    // Skip Trivy (dev only)
    "DOCKAI_SKIP_HEALTH_CHECK": "true"      // Skip health checks
  }
}
```

### 4. Use Verbose Mode for Debugging

When troubleshooting:

```json
{
  "env": {
    "DOCKAI_VERBOSE": "true"
  }
}
```

### 5. Leverage Conversational Context

Take advantage of MCP's conversational nature:

```
You: Create a Dockerfile for my project

Claude: [Creates Dockerfile]

You: Make it use Python 3.11 instead of 3.10

Claude: [Updates Dockerfile]

You: Add Redis as a dependency

Claude: [Adds Redis and updates health checks]

You: Explain why you chose multi-stage builds

Claude: [Provides detailed explanation]
```

## Advanced: MCP + Custom Instructions

Combine MCP with custom instructions for consistent results:

**1. Create `.dockai` file in your project:**

```ini
[instructions_generator]
Company standards:
- Always use Alpine Linux
- Pin all package versions
- Include MAINTAINER label
- Use non-root user with UID 1000
```

**2. Use with MCP:**

```
You: Generate a Dockerfile for this project

Claude: [DockAI automatically picks up .dockai file]
        I've created a Dockerfile following your company standards:
        - Alpine Linux base ✓
        - All versions pinned ✓
        - MAINTAINER label added ✓
        - Running as UID 1000 ✓
```

## Next Steps

- **[Configuration Guide](configuration.md)** - Fine-tune DockAI settings
- **[LLM Providers](llm-providers.md)** - Choose the best provider
- **[Architecture](architecture.md)** - Understand how DockAI works
- **[FAQ](faq.md)** - Common questions and troubleshooting

---

**Questions?** Join the discussion on [GitHub Discussions](https://github.com/itzzjb/dockai/discussions)
