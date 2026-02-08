# Testing Agents

This directory contains multiple agent implementations for testing and development.

## Structure

```
testing/
├── pyproject.toml          # Shared Poetry configuration
├── poetry.lock             # Locked dependencies
├── adk/                    # ADK framework agents
│   └── iterative_writing/  # Iterative writing agent
└── [future agents...]      # Add more agent frameworks/folders here
```

## Setup

1. Install dependencies with Poetry:
   ```bash
   cd testing
   poetry install
   ```

2. Set up environment variables (create a `.env` file in this directory if needed):
   ```
   OPENAI_API_KEY=your-openai-api-key
   ```

## Running Agents

### ADK Agents

To run ADK web interface for agents in the `adk/` directory:

```bash
cd testing/adk
poetry run adk web .
```

This will start a web server at http://localhost:8000 where you can select and interact with agents.

## Adding New Agents

To add a new agent:

1. Create a new subdirectory under the appropriate framework folder (e.g., `adk/new_agent/`)
2. Add your agent code with an `agent.py` file that exports `root_agent`
3. Dependencies are shared via the Poetry configuration at this level

## Dependencies

All agents share the same Poetry environment defined in `pyproject.toml`. To add new dependencies:

```bash
cd testing
poetry add <package-name>
```
