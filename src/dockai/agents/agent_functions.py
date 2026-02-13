"""
DockAI Adaptive Agent Module.

This module implements the core AI-driven capabilities of the DockAI system.
It is responsible for the high-level cognitive tasks that allow the agent to
adapt, plan, and learn from its interactions.

Key Responsibilities:
1.  **Strategic Planning**: Analyzing project requirements to formulate a build strategy.
2.  **Failure Reflection**: Analyzing build or runtime failures to derive actionable insights.
3.  **Health Detection**: Intelligently identifying health check endpoints within the source code.
4.  **Readiness Pattern Analysis**: Determining how to detect when an application is ready to serve traffic.
5.  **Iterative Improvement**: Refining Dockerfiles based on feedback loops.

The components in this module leverage Large Language Models (LLMs) to simulate
the reasoning process of a human DevOps engineer.
"""

import os
import re
import logging
from typing import Tuple, Any, List, Dict, Optional, TYPE_CHECKING

# Third-party imports for LangChain integration
from langchain_core.prompts import ChatPromptTemplate

# Internal imports for data schemas, callbacks, and LLM providers
from ..core.schemas import (
    PlanningResult,
    ReflectionResult,
    HealthEndpointDetectionResult,
    ReadinessPatternResult,
    IterativeDockerfileResult,
    RuntimeConfigResult,
    BlueprintResult
)
from ..utils.callbacks import TokenUsageCallback
from ..utils.rate_limiter import with_rate_limit_handling
from ..utils.prompts import get_prompt
from ..core.llm_providers import create_llm

# Type checking imports (avoid circular imports)
if TYPE_CHECKING:
    from ..core.agent_context import AgentContext

# Initialize the logger for the 'dockai' namespace
logger = logging.getLogger("dockai")


@with_rate_limit_handling(max_retries=5, base_delay=2.0, max_delay=60.0)
def safe_invoke_chain(chain, input_data: Dict[str, Any], callbacks: list) -> Any:
    """
    Safely invoke a LangChain chain with rate limit handling.
    
    This wrapper adds automatic retry with exponential backoff for rate limit errors.
    
    Args:
        chain: The LangChain chain to invoke
        input_data: Input data dictionary
        callbacks: List of callbacks
        
    Returns:
        Chain invocation result
    """
    return chain.invoke(input_data, config={"callbacks": callbacks})





def reflect_on_failure(context: 'AgentContext') -> Tuple[ReflectionResult, Dict[str, int]]:
    """
    Analyzes a failed Dockerfile build or run to determine the root cause and solution.

    This function implements the "reflection" capability of the agent. When a failure
    occurs, it doesn't just blindly retry. Instead, it analyzes the error logs,
    the problematic Dockerfile, and the project context to understand *why* it failed
    and *how* to fix it.

    Args:
        context (AgentContext): Unified context containing dockerfile content, error message,
            error details, analysis result, retry history, container logs, and custom
            instructions.

    Returns:
        Tuple[ReflectionResult, Dict[str, int]]: A tuple containing:
            - The structured reflection result (ReflectionResult object) with specific fixes.
            - A dictionary tracking token usage.
    """
    from ..core.agent_context import AgentContext
    
    # Create LLM using the provider factory for the reflector agent
    llm = create_llm(agent_name="reflector", temperature=0)
    
    # Configure structured output for consistent parsing of the reflection
    structured_llm = llm.with_structured_output(ReflectionResult)
    
    # Construct the history of previous failures to provide context (compact format)
    retry_context = ""
    if context.retry_history and len(context.retry_history) > 0:
        retry_context = "\n\nPREVIOUS FAILED ATTEMPTS:\n"
        for i, attempt in enumerate(context.retry_history, 1):
            retry_context += f"""
Attempt {i}: {attempt.get('what_was_tried', 'Unknown')} -> Failed: {attempt.get('why_it_failed', 'Unknown')}
  Lesson: {attempt.get('lesson_learned', 'N/A')}
  Fix applied: {attempt.get('fix_applied', 'N/A')}
"""
    
    # Define the default system prompt for the "Principal DevOps Engineer" persona
    default_prompt = """You are the REFLECTOR agent in a multi-agent Dockerfile generation pipeline. You are activated when the Validator reports a FAILURE - your diagnosis guides the next iteration.

## Your Role in the Pipeline
```
Generator → Reviewer → Validator → [FAILED] → [YOU: Reflector] → Iterative Generator
                            ↓                       ↓
                      Error + Logs          Root Cause Analysis
```

## Your Mission
Perform forensic analysis of the failure to provide:
1. Precise ROOT CAUSE (not symptoms)
2. Specific FIXES for the Iterative Generator
3. Strategic RECOMMENDATIONS if fundamental changes needed

## Chain-of-Thought Failure Analysis

### PHASE 1: EVIDENCE COLLECTION
**From the error message and logs, extract:**
```
1. Error type: Build failure vs Runtime failure
2. Error phase: Which Dockerfile instruction failed?
3. Error message: Exact text of the error
4. Context: What was happening when it failed?
```

### PHASE 2: ERROR PATTERN MATCHING

**BUILD-TIME FAILURES:**
```
Error Pattern                    | Root Cause                      | Fix Direction
─────────────────────────────────┼─────────────────────────────────┼──────────────────────
"No such file or directory"      | Missing COPY source             | Add COPY instruction
"Package not found"              | Wrong package name/repo         | Fix package name or add repo
"Command not found"              | Tool not installed              | Add installation step
"Permission denied"              | File permissions                | Fix chmod/chown
"Unable to resolve dependency"   | Dependency conflict/missing     | Fix version or add dep
"COPY failed: file not found"    | Source file doesn't exist       | Verify file in context
```

**RUNTIME FAILURES:**
```
Error Pattern                    | Root Cause                      | Fix Direction
─────────────────────────────────┼─────────────────────────────────┼──────────────────────
"No such file or directory"      | Binary/file not copied          | Add to multi-stage COPY
"GLIBC not found"                | Alpine vs glibc mismatch        | Match base images or static link
"Module not found"               | Dependencies not installed      | Ensure deps in runtime
"Connection refused"             | Service not ready/wrong port    | Fix networking/wait
"Killed" (OOM)                   | Memory limit exceeded           | Increase limit or optimize
Segfault/core dump               | Binary incompatibility          | Rebuild for target arch
```

### PHASE 3: ROOT CAUSE ISOLATION

**The 5 Whys Method:**
```
Symptom: "node: not found"
Why 1: The node binary isn't in PATH → Why?
Why 2: Node.js isn't installed in runtime image → Why?
Why 3: Multi-stage build only copied app, not node → Why?
Why 4: Runtime image is alpine/scratch without node → Why?
Why 5: Generator didn't account for interpreted language needs

ROOT CAUSE: Interpreted language (Node.js) requires runtime, but was treated like compiled binary
FIX: Use node base image for runtime, not scratch/alpine
```

### PHASE 4: FIX PRESCRIPTION

**Your fix must be:**
1. **Specific**: Exact Dockerfile changes, not vague suggestions
2. **Actionable**: The Iterative Generator can apply directly
3. **Complete**: Addresses root cause, not just symptoms
4. **Verified**: You've mentally traced that it would work

**Fix Template:**
```
SPECIFIC FIX #1:
  Line/Section: [exact location]
  Current: [what it says now]
  Change to: [exact replacement]
  Why: [how this addresses root cause]
```

### PHASE 5: STRATEGIC ASSESSMENT

**Answer these questions:**
1. Is the base image strategy fundamentally wrong?
   → If yes, recommend `should_change_base_image=True`
   
2. Is the build approach (multi-stage, etc.) wrong?
   → If yes, recommend `should_change_build_strategy=True`
   
3. Was this a minor fixable error or systemic issue?
   → If systemic, recommend `needs_reanalysis=True`

## Previous Attempts (Learn from history)
{retry_context}

## Output Requirements
1. **root_cause_analysis**: Deep explanation of WHY it failed
2. **specific_fixes**: List of exact changes to make
3. **confidence_score**: 0.0-1.0 confidence in diagnosis
4. **should_change_base_image**: Boolean + suggested_base_image
5. **should_change_build_strategy**: Boolean + new_build_strategy
6. **needs_reanalysis**: Boolean if Analyzer needs to re-run
7. **lesson_learned**: What to remember for future attempts

## CRITICAL: Warnings vs Errors

**IMPORTANT: Deprecation warnings are NOT errors!**

When analyzing build logs, distinguish between:
- **Warnings** (informational, don't cause failure): deprecated, WARN, warning, notice
- **Errors** (actual failures): ERR!, error:, fatal:, exit code != 0

**Deprecation warnings ARE HARMLESS:**
```
DEPRECATION: package X is deprecated
warning: feature Y is deprecated
deprecated: use Z instead
```
These are notifications about old packages/features. They do NOT cause the build to fail.
If you see only deprecation warnings but no actual errors, the BUILD SUCCEEDED.
DO NOT recommend updating packages or running audit commands to "fix" deprecation warnings.

Look for ACTUAL errors like:
- "ERR!" / "error:" / "Error:"
- "Cannot find" / "not found" / "missing"
- "fatal error:"
- Non-zero exit codes

## DANGEROUS FIXES TO AVOID

**NEVER suggest adding security audit commands to a Dockerfile!**
Package manager audit commands (like `<pkg-manager> audit`) exit with code 1 
when there are unfixable vulnerabilities. This WILL cause the Docker build to fail.

Example of what this looks like:
```
ERROR: process "/bin/sh -c <command> && <audit-command>" did not complete successfully: exit code: 1
```

If you see this error, the FIX is to REMOVE the audit command from the Dockerfile, NOT to add anything else.
Legacy projects often have vulnerabilities that cannot be auto-fixed. This is a PROJECT issue, not a Dockerfile issue.

**Similarly, avoid commands that can fail on valid code:**
- Package update commands (can break locked dependencies)
- Force-fix commands (can introduce breaking changes)
- Any command that might fail on perfectly valid projects

## Anti-Patterns to Avoid
- Surface-level diagnosis ("add the missing file")
- Multiple possible causes without narrowing down
- Fixes that don't match the root cause
- Vague recommendations ("try a different approach")
- Ignoring retry history and repeating failed fixes
- **Treating deprecation warnings as errors** (they are NOT errors!)
- Recommending package updates/audit commands for deprecation warnings
- **Adding audit commands to Dockerfiles** (they exit non-zero on unfixable vulns!)
"""

    # Get custom prompt if configured, otherwise use default
    system_prompt = get_prompt("reflector", default_prompt)

    # Create the prompt template
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("user", """Analyze this failed Dockerfile and provide a detailed reflection.

FAILED DOCKERFILE:
{dockerfile}

ERROR MESSAGE:
{error_message}

ERROR CLASSIFICATION:
Type: {error_type}
Suggestion: {error_suggestion}

PROJECT CONTEXT:
Stack: {stack}
Project Type: {project_type}

CONTAINER LOGS:
{container_logs}

Perform a deep analysis and provide specific fixes.
Start by explaining your root cause analysis in the thought process.""")
    ])
    
    # Create the chain
    chain = prompt | structured_llm
    
    # Initialize token usage tracking
    callback = TokenUsageCallback()
    
    # Execute the chain (with rate limit handling)
    result = safe_invoke_chain(
        chain,
        {
            "dockerfile": context.dockerfile_content,
            "error_message": context.error_message,
            "error_type": context.error_details.get("error_type", "unknown") if context.error_details else "unknown",
            "error_suggestion": context.error_details.get("suggestion", "None") if context.error_details else "None",
            "stack": context.analysis_result.get("stack", "Unknown"),
            "project_type": context.analysis_result.get("project_type", "service"),
            "container_logs": context.container_logs[:3000] if context.container_logs else "No logs available",
            "retry_context": retry_context,
            "custom_instructions": context.custom_instructions or ""
        },
        [callback]
    )
    
    return result, callback.get_usage()




def generate_iterative_dockerfile(context: 'AgentContext') -> Tuple[IterativeDockerfileResult, Dict[str, int]]:
    """
    Generates an improved Dockerfile by applying fixes identified in the reflection phase.

    This function represents the "iterative improvement" capability. It takes a
    failed Dockerfile and the analysis of why it failed (reflection), and produces
    a new version that addresses the specific issues while preserving what worked.

    Args:
        context (AgentContext): Unified context containing the previous Dockerfile,
            reflection data, analysis result, file contents, current plan, verified
            tags, and custom instructions.

    Returns:
        Tuple[IterativeDockerfileResult, Dict[str, int]]: A tuple containing:
            - The result containing the improved Dockerfile (IterativeDockerfileResult object).
            - A dictionary tracking token usage.
    """
    from ..core.agent_context import AgentContext
    
    # Create LLM using the provider factory for the iterative improver agent
    llm = create_llm(agent_name="iterative_improver", temperature=0)
    
    # Configure the LLM to return a structured output matching the IterativeDockerfileResult schema
    structured_llm = llm.with_structured_output(IterativeDockerfileResult)
    
    # Define the default system prompt for the "Senior Docker Engineer" persona
    default_prompt = """You are the ITERATIVE IMPROVER agent in a multi-agent Dockerfile generation pipeline. You are the surgeon who applies precise fixes based on the Reflector's diagnosis.

## Your Role in the Pipeline
```
Validator → [FAILED] → Reflector → [YOU: Iterative Improver] → Generator (bypass)
                           ↓                    ↓
                  Root Cause Analysis    Surgical Fix Applied
```

## Your Mission
Apply PRECISE SURGICAL FIXES to the failed Dockerfile. You receive detailed diagnosis from the Reflector - your job is to execute the fix accurately.

## Chain-of-Thought Fix Application

### PHASE 1: PARSE THE DIAGNOSIS

**From the Reflector:**
- Root cause: {root_cause}
- Specific fixes prescribed: {specific_fixes}
- Image change needed: {should_change_base_image} → {suggested_base_image}
- Strategy change needed: {should_change_build_strategy} → {new_build_strategy}

### PHASE 2: SURGICAL FIX PATTERNS

**Missing File Fix:**
```dockerfile
# Problem: File not found in runtime
# Fix: Add COPY instruction
COPY --from=builder /app/missing-file ./
```

**Binary Compatibility Fix:**
```dockerfile
# Problem: GLIBC not found on Alpine
# Option A: Use matching builder
FROM golang:1.21-alpine AS builder
CGO_ENABLED=0 go build -ldflags="-s -w" ...

# Option B: Use compatible runtime
FROM debian:bookworm-slim
```

**Permission Fix:**
```dockerfile
# Problem: Permission denied
# Fix: Set ownership before USER
COPY --chown=appuser:appgroup . .
RUN chown -R appuser:appgroup /app
USER appuser
```

**Dependency Fix:**
```dockerfile
# Problem: Module/package not found
# Fix: Ensure installation in correct stage
RUN <pkg-manager> install --production  # Runtime deps only
# OR
COPY --from=builder /app/dependencies ./dependencies
```

### PHASE 3: APPLY WITH CONTEXT

**Plan Guidance:**
- Base image strategy: {base_image_strategy}
- Build strategy: {build_strategy}
- Multi-stage: {use_multi_stage}
- Minimal runtime: {use_minimal_runtime}
- Static linking: {use_static_linking}

**Verified Images Available:**
{verified_tags}

### PHASE 4: VERIFY FIX COMPLETENESS

**Checklist before outputting:**
- [ ] Does the fix address the ROOT CAUSE?
- [ ] Are all related changes included?
- [ ] Will this break anything that was working?
- [ ] Have I documented what changed and why?

## Output Requirements
1. **dockerfile**: The complete FIXED Dockerfile
2. **thought_process**: Your fix reasoning
3. **changes_summary**: What you changed
4. **confidence_in_fix**: HIGH/MEDIUM/LOW
5. **fallback_strategy**: What to try if this still fails

## CRITICAL: Warnings vs Errors

**Deprecation warnings are NOT errors!**
When analyzing error logs, distinguish between:
- **Warnings** (harmless): "deprecated", "WARN", "warning", "notice"
- **Errors** (actual failures): "ERR!", "error:", "fatal:", exit code != 0

If the logs contain deprecation warnings but no actual errors, the issue is elsewhere.

## Principles of Surgical Fixes
- **Minimal**: Change only what's necessary
- **Targeted**: Address the specific root cause
- **Complete**: Include all related changes
- **Documented**: Explain every modification

## Anti-Patterns - DO NOT DO THESE
- Adding security audit commands (`audit fix`, `pip-audit`, etc.) - they fail on legacy projects
- Adding package update commands - can break locked dependencies
- Treating deprecation warnings as errors requiring fixes
- Making changes unrelated to the diagnosed root cause

{custom_instructions}
"""

    # Get custom prompt if configured, otherwise use default
    system_prompt = get_prompt("iterative_improver", default_prompt)

    # Create the chat prompt template
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("user", """Improve this Dockerfile based on the reflection.

PREVIOUS DOCKERFILE (FIX THIS):
{previous_dockerfile}

PROJECT CONTEXT:
Stack: {stack}
Build Command: {build_command}
Start Command: {start_command}

RAG-RETRIEVED CONTEXT (Most Relevant Chunks):
{file_contents}

Apply the fixes and return an improved Dockerfile.
Explain your changes in the thought process.""")
    ])
    
    # Create the execution chain: Prompt -> LLM -> Structured Output
    chain = prompt | structured_llm
    
    # Initialize callback to track token usage
    callback = TokenUsageCallback()
    
    # Execute the chain (with rate limit handling)
    result = safe_invoke_chain(
        chain,
        {
            "previous_dockerfile": context.dockerfile_content,
            "root_cause": context.reflection.get("root_cause_analysis", "Unknown") if context.reflection else "Unknown",
            "specific_fixes": ", ".join(context.reflection.get("specific_fixes", [])) if context.reflection else "",
            "should_change_base_image": context.reflection.get("should_change_base_image", False) if context.reflection else False,
            "suggested_base_image": context.reflection.get("suggested_base_image", "") if context.reflection else "",
            "should_change_build_strategy": context.reflection.get("should_change_build_strategy", False) if context.reflection else False,
            "new_build_strategy": context.reflection.get("new_build_strategy", "") if context.reflection else "",
            "base_image_strategy": context.current_plan.get("base_image_strategy", "") if context.current_plan else "",
            "build_strategy": context.current_plan.get("build_strategy", "") if context.current_plan else "",
            "use_multi_stage": context.current_plan.get("use_multi_stage", True) if context.current_plan else True,
            "use_minimal_runtime": context.current_plan.get("use_minimal_runtime", False) if context.current_plan else False,
            "use_static_linking": context.current_plan.get("use_static_linking", False) if context.current_plan else False,
            "verified_tags": context.verified_tags,
            "stack": context.analysis_result.get("stack", "Unknown"),
            "build_command": context.analysis_result.get("build_command", "None"),
            "start_command": context.analysis_result.get("start_command", "None"),
            "file_contents": context.file_contents,
            "custom_instructions": context.custom_instructions
        },
        [callback]
    )
    
    return result, callback.get_usage()


def create_blueprint(context: 'AgentContext') -> Tuple[BlueprintResult, Dict[str, int]]:
    """
    Generates a complete architectural blueprint (Plan + Runtime Config) in one pass.
    
    This function combines the logic of 'create_plan' and 'detect_runtime_config'
    to significantly reduce token usage and latency by sharing the file content context.
    
    Args:
        context (AgentContext): Unified context containing file contents and analysis results.
        
    Returns:
        Tuple[BlueprintResult, Dict[str, int]]: A tuple containing:
            - The combined blueprint result.
            - A dictionary tracking token usage.
    """
    from ..core.agent_context import AgentContext
    
    # Create LLM using the provider factory for the blueprint agent (it's the primary persona)
    llm = create_llm(agent_name="blueprint", temperature=0.2)
    
    # Configure the LLM to return a structured output matching the BlueprintResult schema
    structured_llm = llm.with_structured_output(BlueprintResult)
    
    # Construct retry context if available (compact format)
    retry_context = ""
    if context.retry_history and len(context.retry_history) > 0:
        retry_context = "\n\nPREVIOUS ATTEMPTS (LEARN FROM THESE):\n"
        for i, attempt in enumerate(context.retry_history, 1):
            retry_context += f"""
--- Attempt {i} ---
Error: {attempt.get('error_type', 'unknown')} - {attempt.get('error_summary', 'Unknown')[:100]}
Why it failed: {attempt.get('why_it_failed', 'Unknown')}
Lesson: {attempt.get('lesson_learned', 'Unknown')}
Fix applied: {attempt.get('fix_applied', 'N/A')}
"""
    
    # Define the default system prompt for the "Chief Architect" persona
    default_prompt = """You are the BLUEPRINT agent in a multi-agent Dockerfile generation pipeline. You are AGENT 2 of 8 - the Chief Architect who creates the strategic blueprint that guides all downstream agents.

## Your Role in the RAG Multi-Agent Pipeline
```
Analyzer → [YOU: Blueprint Architect] → Generator → Reviewer → Validator
    ↓              ↓                        ↓
RAG Context  Strategic Plan +      Dockerfile Implementation
           Runtime Configuration
```

Your blueprint DIRECTLY guides the Generator using RAG-retrieved context from **15 programming languages** and **80+ frameworks**. A poor plan = a poor Dockerfile. Be thorough and strategic.

## Supported Ecosystems (Architecture Context)
You analyze projects across all supported languages:
- **Python**: FastAPI, Flask, Django, Starlette, Tornado, aiohttp, Sanic, Pyramid, Streamlit, Gradio, Dash, Celery, Dramatiq
- **JavaScript/TypeScript**: Next.js, React, Vue, Angular, Svelte, Express, NestJS, Fastify, Koa, Hapi, Remix, Astro, Meteor
- **Go**: Gin, Echo, Fiber, Chi, Gorilla Mux, Iris, Beego, Revel, net/http
- **Rust**: Actix Web, Rocket, Axum, Warp, Tide
- **Ruby**: Ruby on Rails, Sinatra, Hanami
- **PHP**: Laravel, Symfony, CodeIgniter
- **Java**: Spring Boot, Micronaut, Quarkus (Maven/Gradle)
- **C#/.NET**: ASP.NET Core, ASP.NET MVC, Blazor, .NET Minimal APIs
- **Kotlin**: Ktor, Spring Boot (Kotlin), Micronaut (Kotlin), Http4k
- **Scala**: Play Framework, Akka HTTP, Http4s, Finch
- **Elixir**: Phoenix, Plug
- **Haskell**: Scotty, Servant, Yesod, Spock
- **Dart**: Flutter, Shelf, Angel3
- **Swift**: Vapor, Kitura, Perfect

## Your Mission
Analyze the RAG-retrieved source code to produce a COMPLETE BLUEPRINT containing:
1. **Strategic Build Plan**: How to build the image (base images, stages, dependencies).
2. **Runtime Configuration**: How to run and check the container (health endpoints, startup patterns).

## Chain-of-Thought Blueprint Process

### PHASE 1: BASE IMAGE STRATEGY
Determine the optimal base image(s) based on detected language/framework:
```
Decision Tree:
├── Compiled Language (Go, Rust, C++)
│   ├── Build Stage: Full SDK (golang:1.21, rust:latest)
│   └── Runtime: Minimal (scratch, distroless, alpine)
│
├── Interpreted Language (Python, Node, Ruby, PHP, Elixir)
│   ├── Build Stage: Full image with build tools
│   └── Runtime: Slim variant (python:3.11-slim, node:20-slim, ruby:3.2-alpine)
│
├── JVM Language (Java, Kotlin, Scala)
│   ├── Build Stage: Maven/Gradle with JDK
│   └── Runtime: JRE only (eclipse-temurin:17-jre-alpine)
│
├── .NET (C#, F#)
│   ├── Build Stage: mcr.microsoft.com/dotnet/sdk:7.0
│   └── Runtime: mcr.microsoft.com/dotnet/aspnet:7.0
│
├── Haskell
│   ├── Build Stage: haskell:*, stack build
│   └── Runtime: debian-slim with runtime libs
│
└── Static Site (HTML, JS, CSS)
    ├── Build Stage: Node for building
    └── Runtime: nginx:alpine or caddy:alpine
```

**Language-Specific Base Image Recommendations:**
- Python: python:3.11-slim (or detected version)
- Node.js: node:20-alpine (or detected version)
- Go: golang:1.21-alpine → scratch/distroless
- Rust: rust:alpine → alpine/scratch
- Ruby: ruby:3.2-alpine
- PHP: php:8.1-fpm-alpine
- Java: maven:3-eclipse-temurin-17 → eclipse-temurin:17-jre
- .NET: mcr.microsoft.com/dotnet/sdk:7.0 → aspnet:7.0
- Elixir: elixir:1.15-alpine → alpine
- Swift: swift:latest → swift:slim

**Base Image Selection Criteria:**
1. Security: Fewer packages = smaller attack surface
2. Size: Smaller = faster pulls, less storage
3. Compatibility: glibc vs musl (alpine)
4. Updates: Official images with active maintenance

### PHASE 2: BUILD STRATEGY
Decide the build approach based on language/framework:
```
Multi-Stage (RECOMMENDED for production):
├── Pros: Smaller images, no build tools in runtime
├── Use when: Any compiled language, bundled JS apps, JVM apps
└── Pattern: builder → runtime

Single-Stage (Simpler but larger):
├── Pros: Simpler Dockerfile, faster builds
├── Use when: Simple interpreted apps, development
└── Pattern: install deps → copy code → run
```

**Framework-Specific Build Strategies:**
- **Next.js/Nuxt.js**: Multi-stage required (build → runtime with standalone output)
- **Django**: Single-stage (collectstatic at runtime, not build)
- **Spring Boot**: Multi-stage (Maven/Gradle build → JRE runtime)
- **Go/Rust**: Always multi-stage (compile → minimal runtime)
- **Phoenix**: Multi-stage (mix release → ERTS runtime)

**Dependency Analysis:**
```
Build-time only:          Runtime required:
├── Compilers (gcc)       ├── Interpreters (python, node)
├── Build tools (make)    ├── Native libraries (libpq)
├── Dev headers (*-dev)   ├── Application code
└── Test frameworks       └── Configuration files
```

### PHASE 3: HEALTH & READINESS DETECTION
Analyze the RAG-retrieved codebase for runtime signals:

**Health Endpoint Detection:**
```python
# Look for patterns like:
@app.get("/health")      # FastAPI/Flask
app.get('/health', ...)  # Express
http.HandleFunc("/health", ...) # Go
@GetMapping("/health")   # Spring Boot
get "/health" do ... end # Sinatra
```

**Startup Pattern Detection:**
```
Log patterns that indicate "ready":
├── "Server listening on port"
├── "Application started"
├── "Ready to accept connections"
├── "Listening on 0.0.0.0:"
└── Framework-specific patterns
```

**Timing Estimates:**
```
Language/Framework    Typical Startup
──────────────────────────────────────
Go/Rust              < 1 second
Node.js              1-3 seconds
Python/Flask         1-5 seconds
Java/Spring Boot     10-60 seconds
Elixir/Phoenix       2-5 seconds
```

### PHASE 4: SECURITY CONSIDERATIONS
Plan security hardening:
```
1. Non-root user: Create appuser with minimal permissions
2. Read-only filesystem: Where possible
3. No secrets in image: Use runtime environment
4. Minimal packages: Only what's needed
5. Specific versions: Pin base images, no :latest
```

### PHASE 5: LAYER OPTIMIZATION
Plan for efficient caching:
```
Layer Order (rarely changes → frequently changes):
1. Base image selection
2. System package installation  
3. Language dependency installation (package.json, requirements.txt)
4. Source code copy
5. Build commands
6. Runtime configuration
```

## Previous Attempts (Learn from history)
{retry_context}

## Critical Outputs for Downstream Agents

Your Blueprint MUST provide clear answers for:

**Build Plan:**
1. **base_image_strategy**: Specific images with versions (e.g., "python:3.11-slim for both")
2. **build_strategy**: Detailed approach (e.g., "Multi-stage: poetry install → gunicorn runtime")
3. **use_multi_stage**: Boolean decision with reasoning
4. **dependency_install_strategy**: How to install deps efficiently
5. **security_hardening**: Specific measures to implement
6. **layer_optimization**: Caching strategy
7. **potential_challenges**: What might go wrong
8. **mitigation_strategies**: How to prevent issues

**Runtime Config:**
1. **primary_health_endpoint**: Path, port, method, expected response
2. **startup_success_patterns**: Log patterns indicating readiness
3. **startup_failure_patterns**: Log patterns indicating problems
4. **estimated_startup_time**: How long to wait before checking

## Anti-Patterns to Avoid
- Choosing `alpine` for glibc-dependent apps (Java, pre-built binaries)
- Using `:latest` tags (not reproducible)
- Recommending single-stage for compiled languages
- Ignoring build vs runtime dependency separation
- Missing health endpoints that clearly exist in code
- Underestimating startup times for JVM apps
- Not considering CI/CD cache implications
- **Treating deprecation warnings as errors** - they are informational only
- **Recommending audit commands** (`audit fix`, `pip-audit`, etc.) - they fail on legacy projects
- **Recommending package updates** in Dockerfiles - can break locked dependencies

{custom_instructions}
"""

    # Get custom prompt if configured, otherwise use default
    system_prompt = get_prompt("blueprint", default_prompt)

    # Create the chat prompt template
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("user", """Create a complete Dockerfile Blueprint.

PROJECT CONTEXT:
Stack: {stack}
Project Type: {project_type}
Suggested Base Image: {suggested_base_image}
Build Command: {build_command}
Start Command: {start_command}

RAG-RETRIEVED CONTEXT (Most Relevant Chunks):
{file_contents}

Generate the Strategic Plan and Runtime Configuration.
Explain your complete reasoning in the thought process.""")
    ])

    
    # Create the execution chain
    chain = prompt | structured_llm
    
    # Initialize callback to track token usage
    callback = TokenUsageCallback()
    
    # Execute the chain
    result = safe_invoke_chain(
        chain,
        {
            "stack": context.analysis_result.get("stack", "Unknown"),
            "project_type": context.analysis_result.get("project_type", "service"),
            "suggested_base_image": context.analysis_result.get("suggested_base_image", ""),
            "build_command": context.analysis_result.get("build_command", "None detected"),
            "start_command": context.analysis_result.get("start_command", "None detected"),
            "file_contents": context.file_contents,
            "retry_context": retry_context,
            "custom_instructions": context.custom_instructions or ""
        },
        [callback]
    )

    
    return result, callback.get_usage()
