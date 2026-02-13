# DockAI Agents — Complete Guide

## The Pipeline Flow

```
Scan → 1.Analyzer → RAG → 2.Blueprint → 3.Generator → 4.Reviewer → 5.Validator(+6.Error Analyzer)
                                                                          ↓ (on failure)
                                                                    7.Reflector
                                                                          ↓
                                                              Iterative Improver
                                                                          ↓
                                                                    back to Reviewer...
```

---

## 1. Analyzer — "The Brain"

- **File**: `src/dockai/agents/analyzer.py`
- **When**: First agent to run, right after file scanning
- **What it does**: Examines the file tree to detect the tech stack, project type (service vs script), build commands, start commands, runtime version, base image suggestions, health endpoints
- **LLM model key**: `analyzer`
- **Output**: `AnalysisResult` — the foundation every downstream agent depends on

---

## 2. Blueprint — "The Chief Architect"

- **File**: `src/dockai/agents/agent_functions.py` → `create_blueprint()`
- **When**: After Analyzer + RAG file reading
- **What it does**: Creates a strategic build plan — decides multi-stage vs single-stage, base image strategy, static linking, minimal runtime, potential challenges, mitigation strategies. Also detects runtime config (health endpoints, readiness patterns, ports)
- **LLM model key**: `blueprint`
- **Output**: `BlueprintResult` — the architectural plan that guides the Generator

---

## 3. Generator — "The Builder"

- **File**: `src/dockai/agents/generator.py` → `_generate_fresh_dockerfile()`
- **When**: After Blueprint, on the **first attempt** (no prior failures)
- **What it does**: Creates a Dockerfile from scratch following the Blueprint's plan. Fetches verified Docker tags to prevent hallucinated image names. Incorporates expert stack-specific guidance
- **LLM model key**: `generator`
- **Output**: Complete Dockerfile + project type + thought process

---

## 4. Reviewer — "The Security Engineer"

- **File**: `src/dockai/agents/reviewer.py`
- **When**: Immediately after every Generator/Iterative Improver output
- **What it does**: Static security analysis of the Dockerfile — checks for running as root, hardcoded secrets, image tag issues, best practices. If critical issues are found, it generates a corrected Dockerfile
- **LLM model key**: `reviewer`
- **Output**: `SecurityReviewResult` — issues, severity, fixes, optionally a corrected Dockerfile

---

## 5. Validator — (Not an LLM agent, but a pipeline node)

- **File**: `src/dockai/workflow/nodes.py` → `validate_node()`
- **When**: After Reviewer passes the Dockerfile as secure
- **What it does**: Actually **builds** the Docker image, **runs** the container, performs health checks, checks image size. This is code-based validation, not LLM-based
- **Note**: The Validator is listed as one of the 8 "agents" in the architecture but it doesn't use an LLM. It calls the **Error Analyzer** when something fails

---

## 6. Error Analyzer — "The Troubleshooter"

- **File**: `src/dockai/core/errors.py` → `analyze_error_with_ai()`
- **When**: Called **inside** the Validator when a build/run **fails**
- **What it does**: Classifies errors into 3 categories:
  - `PROJECT_ERROR` — user's code is broken (no retry)
  - `DOCKERFILE_ERROR` — Dockerfile can be fixed (retry)
  - `ENVIRONMENT_ERROR` — Docker/system issue (no retry)

  Also provides a specific `dockerfile_fix`, `image_suggestion`, and `readiness_fix`
- **LLM model key**: `error_analyzer`
- **Output**: `ClassifiedError` — determines whether the pipeline should retry or stop

---

## 7. Reflector — "The Post-Mortem Analyst"

- **File**: `src/dockai/agents/agent_functions.py` → `reflect_on_failure()`
- **When**: After Validator fails **and** Error Analyzer says it's retryable
- **What it does**: Deep root-cause analysis of *why* the Dockerfile failed. Examines error logs, the failed Dockerfile, project context, and all previous retry attempts. Produces actionable fixes and decides whether to re-analyze the project, re-plan, or just fix the code
- **LLM model key**: `reflector`
- **Output**: `ReflectionResult` — root cause, specific fixes, confidence, whether to re-analyze/change strategy

---

## 7. Iterative Improver — "The Surgeon"

- **When**: On **retry attempts** (after Reflector), when a previous Dockerfile exists
- **What it does**: Applies precise, surgical fixes to the existing Dockerfile based on the Reflector's diagnosis. Preserves working parts while targeting the specific lines that caused failures
- **File**: `src/dockai/agents/agent_functions.py` → `generate_iterative_dockerfile()`
- **LLM model key**: `iterative_improver`
- **Prompt key**: `iterative_improver`
- **Output**: A corrected Dockerfile with minimal, targeted changes

---

## Similarities & Differences Summary

| Aspect | Analyzer | Blueprint | Generator | Reviewer | Error Analyzer | Reflector | Iterative Improver |
|--------|----------|-----------|-----------|----------|----------------|-----------|-------------------|
| **Uses LLM** | Yes | Yes | Yes | Yes | Yes | Yes | Yes |
| **Runs on happy path** | Yes | Yes | Yes | Yes | No | No | No |
| **Runs on failure** | Maybe (re-analysis) | Maybe (re-plan) | Maybe (fresh retry) | Yes (re-review) | Yes | Yes | Yes |
| **Creates Dockerfiles** | No | No | **Yes** | Patches only | No | No | **Yes** |
| **Analyzes errors** | No | No | No | No | **Yes** | **Yes** | No |
| **Plans strategy** | **Yes** | **Yes** | No | No | No | No | No |

---

## Key Distinctions

- **Error Analyzer vs Reflector**: Error Analyzer does quick triage ("Is this fixable? What type?"). Reflector does deep root-cause analysis ("Why did it fail? What specific changes are needed?"). Error Analyzer runs first; Reflector only runs if Error Analyzer says it's retryable.
- **Generator vs Iterative Improver**: Generator creates Dockerfiles from scratch. Iterative Improver makes surgical fixes to an existing Dockerfile based on error feedback and reflection results.
