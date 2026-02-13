"""Tests for the generator module."""
import pytest
from unittest.mock import patch, MagicMock, PropertyMock
from dockai.agents.generator import generate_dockerfile
from dockai.core.schemas import DockerfileResult, IterativeDockerfileResult
from dockai.core.agent_context import AgentContext


class TestGenerateDockerfile:
    """Test generate_dockerfile function."""
    
    @patch("dockai.agents.generator.TokenUsageCallback")
    @patch("dockai.agents.generator.ChatPromptTemplate")
    @patch("dockai.agents.generator.create_llm")
    def test_generate_fresh_dockerfile(self, mock_create_llm, mock_prompt_class, mock_callback_class):
        """Test generating a fresh Dockerfile."""
        # Set up mock callback
        mock_callback = MagicMock()
        mock_callback.get_usage.return_value = {"total_tokens": 100, "prompt_tokens": 80, "completion_tokens": 20}
        mock_callback_class.return_value = mock_callback
        
        # Set up mock prompt
        mock_prompt = MagicMock()
        mock_prompt_class.from_messages.return_value = mock_prompt
        
        # Set up mock LLM
        mock_llm = MagicMock()
        mock_create_llm.return_value = mock_llm
        
        # Create mock chain that returns our result when invoked
        mock_chain = MagicMock()
        mock_result = DockerfileResult(
            thought_process="Creating optimized Python Dockerfile",
            dockerfile="""FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
USER app
CMD ["python", "app.py"]""",
            project_type="service"
        )
        mock_chain.invoke.return_value = mock_result
        
        # Make | operator return our mock chain
        mock_prompt.__or__.return_value = mock_chain
        
        context = AgentContext(
            analysis_result={"stack": "Python with Flask"},
            file_contents="flask==2.0.0"
        )
        dockerfile, project_type, thought_process, usage = generate_dockerfile(context=context)
        
        assert "FROM python:3.11" in dockerfile
        assert project_type == "service"
    
    @patch("dockai.agents.generator.TokenUsageCallback")
    @patch("dockai.agents.generator.ChatPromptTemplate")
    @patch("dockai.agents.generator.create_llm")
    def test_generate_node_dockerfile(self, mock_create_llm, mock_prompt_class, mock_callback_class):
        """Test generating a Node.js Dockerfile."""
        mock_callback = MagicMock()
        mock_callback.get_usage.return_value = {"total_tokens": 100, "prompt_tokens": 80, "completion_tokens": 20}
        mock_callback_class.return_value = mock_callback
        
        mock_prompt = MagicMock()
        mock_prompt_class.from_messages.return_value = mock_prompt
        
        mock_llm = MagicMock()
        mock_create_llm.return_value = mock_llm
        
        mock_chain = MagicMock()
        mock_result = DockerfileResult(
            thought_process="Creating Node.js Dockerfile with npm",
            dockerfile="""FROM node:20-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production
COPY . .
USER node
CMD ["npm", "start"]""",
            project_type="service"
        )
        mock_chain.invoke.return_value = mock_result
        mock_prompt.__or__.return_value = mock_chain
        
        context = AgentContext(
            analysis_result={"stack": "Node.js with Express"},
            file_contents='{"name": "app", "dependencies": {"express": "4.18.0"}}'
        )
        dockerfile, project_type, thought_process, usage = generate_dockerfile(context=context)
        
        assert "FROM node:20" in dockerfile
        assert "npm" in dockerfile
    
    @patch("dockai.agents.generator.TokenUsageCallback")
    @patch("dockai.agents.generator.ChatPromptTemplate")
    @patch("dockai.agents.generator.create_llm")
    def test_generate_script_dockerfile(self, mock_create_llm, mock_prompt_class, mock_callback_class):
        """Test generating a Dockerfile for a script project."""
        mock_callback = MagicMock()
        mock_callback.get_usage.return_value = {"total_tokens": 100, "prompt_tokens": 80, "completion_tokens": 20}
        mock_callback_class.return_value = mock_callback
        
        mock_prompt = MagicMock()
        mock_prompt_class.from_messages.return_value = mock_prompt
        
        mock_llm = MagicMock()
        mock_create_llm.return_value = mock_llm
        
        mock_chain = MagicMock()
        mock_result = DockerfileResult(
            thought_process="Creating Python script Dockerfile",
            dockerfile="""FROM python:3.11-slim
WORKDIR /app
COPY . .
ENTRYPOINT ["python", "script.py"]""",
            project_type="script"
        )
        mock_chain.invoke.return_value = mock_result
        mock_prompt.__or__.return_value = mock_chain
        
        context = AgentContext(
            analysis_result={"stack": "Python script"},
            file_contents="# Simple Python script"
        )
        dockerfile, project_type, thought_process, usage = generate_dockerfile(context=context)
        
        assert project_type == "script"
        assert "ENTRYPOINT" in dockerfile
    
    @patch("dockai.agents.generator.TokenUsageCallback")
    @patch("dockai.agents.generator.ChatPromptTemplate")
    @patch("dockai.agents.generator.create_llm")
    def test_generate_with_custom_instructions(self, mock_create_llm, mock_prompt_class, mock_callback_class):
        """Test generating with custom instructions."""
        mock_callback = MagicMock()
        mock_callback.get_usage.return_value = {"total_tokens": 100, "prompt_tokens": 80, "completion_tokens": 20}
        mock_callback_class.return_value = mock_callback
        
        mock_prompt = MagicMock()
        mock_prompt_class.from_messages.return_value = mock_prompt
        
        mock_llm = MagicMock()
        mock_create_llm.return_value = mock_llm
        
        mock_chain = MagicMock()
        mock_result = DockerfileResult(
            thought_process="Applied custom alpine requirement",
            dockerfile="""FROM python:3.11-alpine
WORKDIR /app
COPY . .
CMD ["python", "app.py"]""",
            project_type="service"
        )
        mock_chain.invoke.return_value = mock_result
        mock_prompt.__or__.return_value = mock_chain
        
        context = AgentContext(
            analysis_result={"stack": "Python"},
            file_contents="# app",
            custom_instructions="Always use alpine-based images"
        )
        dockerfile, project_type, thought_process, usage = generate_dockerfile(context=context)
        
        assert "alpine" in dockerfile.lower()
    
    @patch("dockai.agents.generator.TokenUsageCallback")
    @patch("dockai.agents.generator.ChatPromptTemplate")
    @patch("dockai.agents.generator.create_llm")
    def test_generate_returns_tuple(self, mock_create_llm, mock_prompt_class, mock_callback_class):
        """Test that generate returns correct tuple structure."""
        mock_callback = MagicMock()
        mock_callback.get_usage.return_value = {"total_tokens": 100, "prompt_tokens": 80, "completion_tokens": 20}
        mock_callback_class.return_value = mock_callback
        
        mock_prompt = MagicMock()
        mock_prompt_class.from_messages.return_value = mock_prompt
        
        mock_llm = MagicMock()
        mock_create_llm.return_value = mock_llm
        
        mock_chain = MagicMock()
        mock_result = DockerfileResult(
            thought_process="Test thought process",
            dockerfile="FROM python:3.11",
            project_type="service"
        )
        mock_chain.invoke.return_value = mock_result
        mock_prompt.__or__.return_value = mock_chain
        
        context = AgentContext(
            analysis_result={"stack": "Python"},
            file_contents="# app"
        )
        result = generate_dockerfile(context=context)
        
        assert isinstance(result, tuple)
        assert len(result) == 4
        dockerfile, project_type, thought_process, usage = result
        assert isinstance(dockerfile, str)
        assert project_type in ["service", "script"]
        assert isinstance(thought_process, str)
    
    @patch("dockai.agents.generator.TokenUsageCallback")
    @patch("dockai.agents.generator.ChatPromptTemplate")
    @patch("dockai.agents.generator.create_llm")
    def test_generate_with_retry_history(self, mock_create_llm, mock_prompt_class, mock_callback_class):
        """Test generation with retry history."""
        mock_callback = MagicMock()
        mock_callback.get_usage.return_value = {"total_tokens": 100, "prompt_tokens": 80, "completion_tokens": 20}
        mock_callback_class.return_value = mock_callback
        
        mock_prompt = MagicMock()
        mock_prompt_class.from_messages.return_value = mock_prompt
        
        mock_llm = MagicMock()
        mock_create_llm.return_value = mock_llm
        
        mock_chain = MagicMock()
        mock_result = DockerfileResult(
            thought_process="Learning from previous failures",
            dockerfile="FROM python:3.11\nRUN apt-get update && apt-get install -y build-essential",
            project_type="service"
        )
        mock_chain.invoke.return_value = mock_result
        mock_prompt.__or__.return_value = mock_chain
        
        retry_history = [
            {"what_was_tried": "slim image", "why_it_failed": "missing build tools"}
        ]
        
        context = AgentContext(
            analysis_result={"stack": "Python with C extensions"},
            file_contents="numpy==1.24.0",
            retry_history=retry_history
        )
        dockerfile, project_type, thought_process, usage = generate_dockerfile(context=context)
        
        assert "build-essential" in dockerfile or "FROM python" in dockerfile
    
    @patch("dockai.agents.generator.TokenUsageCallback")
    @patch("dockai.agents.generator.ChatPromptTemplate")
    @patch("dockai.agents.generator.create_llm")
    def test_generate_with_plan(self, mock_create_llm, mock_prompt_class, mock_callback_class):
        """Test generation with a strategic plan."""
        mock_callback = MagicMock()
        mock_callback.get_usage.return_value = {"total_tokens": 100, "prompt_tokens": 80, "completion_tokens": 20}
        mock_callback_class.return_value = mock_callback
        
        mock_prompt = MagicMock()
        mock_prompt_class.from_messages.return_value = mock_prompt
        
        mock_llm = MagicMock()
        mock_create_llm.return_value = mock_llm
        
        mock_chain = MagicMock()
        mock_result = DockerfileResult(
            thought_process="Following multi-stage plan",
            dockerfile="""FROM python:3.11 AS builder
WORKDIR /app
COPY . .
RUN pip install .

FROM python:3.11-slim
COPY --from=builder /app /app
CMD ["python", "app.py"]""",
            project_type="service"
        )
        mock_chain.invoke.return_value = mock_result
        mock_prompt.__or__.return_value = mock_chain
        
        current_plan = {
            "use_multi_stage": True,
            "base_image_strategy": "Use slim for runtime"
        }
        
        context = AgentContext(
            analysis_result={"stack": "Python"},
            file_contents="# app",
            current_plan=current_plan
        )
        dockerfile, project_type, thought_process, usage = generate_dockerfile(context=context)
        
        assert "FROM" in dockerfile
