# Demo3 - Simple AI Agent

## Project Overview

**Version**: 1.0.0  
**Type**: Simple AI Agent Example  
**Purpose**: Demonstration of basic AI agent implementation using OpenRouter API

## Quick Summary

Demo3 is a minimal example of an AI agent that can execute tasks using the ReAct (Reasoning + Acting) pattern. It showcases the fundamental concepts of agent-based development without the complexity of multi-agent orchestration.

## Core Components

### 1. Agent Implementation (`agent.py`)
- **ReAct Loop**: Implements thought → action → observation cycle
- **Tool Execution**: Supports basic tool calls (file operations, shell commands)
- **LLM Integration**: Uses OpenRouter API for reasoning
- **Project Management**: Creates and manages project directories

### 2. Prompt Template (`prompt_template.py`)
- **System Prompts**: Defines agent behavior and capabilities
- **Tool Descriptions**: Documents available tools for the agent
- **Task Instructions**: Templates for agent task execution

## Key Features

- ✅ Single-agent architecture
- ✅ ReAct pattern implementation
- ✅ OpenRouter API integration
- ✅ File and shell tool support
- ✅ Project directory management
- ✅ Simple prompt engineering

## Project Structure

```
Demo3/
├── agent.py              # Main agent implementation
├── prompt_template.py    # Prompt templates and tool definitions
├── requirements.txt      # Python dependencies
├── pyproject.toml       # Python project configuration
├── .env.example         # Environment variable template
└── README.md            # Setup and usage instructions
```

## Configuration

### Environment Variables
```bash
OPENROUTER_API_KEY=sk-or-v1-...  # Your OpenRouter API key
```

### Dependencies
- Python 3.12+
- openai (for OpenRouter client)
- Additional packages in `requirements.txt`

## Usage Pattern

```bash
# Setup
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

# Configure
cp .env.example .env
# Edit .env with your OpenRouter API key

# Run
python agent.py [PROJECT_DIRECTORY]
```

## Architecture Patterns

### 1. ReAct Loop
```
User Input → Thought → Action → Observation → Repeat until task complete
```

### 2. Tool System
- **File Tools**: Read, write, modify files
- **Shell Tools**: Execute system commands
- **Custom Tools**: Extensible tool framework

### 3. LLM Integration
- **Provider**: OpenRouter (configurable)
- **Model**: GPT-4 or compatible
- **Pattern**: Zero-shot reasoning with tool descriptions

## Design Principles

1. **Simplicity**: Minimal code, clear structure
2. **Extensibility**: Easy to add new tools
3. **Demonstrative**: Shows core concepts without complexity
4. **Self-contained**: Single file agent implementation

## Comparison with Demo4

| Feature | Demo3 | Demo4 (AgentManager) |
|---------|-------|---------------------|
| Architecture | Single agent | Multi-agent orchestration |
| Complexity | Simple (~200 lines) | Enterprise (~10K+ lines) |
| Task Handling | Sequential | Parallel with dependencies |
| State Management | In-memory | Database + Redis |
| UI | CLI only | Tkinter Dashboard |
| Deployment | Script | Docker Compose |
| Use Case | Learning/Demo | Production workflows |

## Learning Objectives

- Understand agent reasoning patterns
- Implement basic tool system
- Work with LLM APIs
- Structure agent prompts
- Handle task execution flow

## Future Enhancements

- [ ] Add more tool types
- [ ] Implement memory/context management
- [ ] Add streaming output
- [ ] Create web interface
- [ ] Add evaluation metrics

## Related Projects

- **Demo4**: Full multi-agent system with orchestration
- **AgentManager**: Production-ready agent framework

---

**Last Updated**: November 18, 2025  
**Status**: Stable
