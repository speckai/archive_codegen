# Testing Agent Functions

## Setup Steps

1. Install Git Submodules

   - Run `git submodule update --init --recursive` to make eval_repos available

2. Configure Environment

   - Copy `.env.example` to `.env` in the issue-tracker-eval-repo directory
   - Update values in `.env` as needed
   - (optional) Set Jupyter Notebook root to the project root (${workspaceFolder}) in VSCode Workspace Settings

3. Add Debug Decorators

   - Add `@debug_agent_function` decorator to functions you want to test
   - Review other agent tests for examples of decorator usage
   - Include any required session data in the debug_data dictionary:
     ```python
     # Example: Adding chat history for ContextAgent
     "chat.history": [message.model_dump_json() for message in self.task.chat.history]
     ```

4. Install api as a package
   - Run `uv pip install -e .` in the api directory

## Running Tests

1. Execute Test Harness

   ```bash
   uv run -m src.agents.tests.test_harness
   ```

   I prefer running all of these with the debugger attached. You can use the "Python: Current File" launch configuration:

   ```json
   {
     "name": "Python: Current File",
     "type": "debugpy",
     "request": "launch",
     "program": "${file}",
     "cwd": "${workspaceFolder}",
     "env": {
       "PYTHONPATH": "${workspaceFolder}"
     },
     "console": "integratedTerminal"
   }
   ```

2. Locate Debug Data

   - Debug data is saved to `.debug/<AgentName>/<FunctionName>/<Timestamp>/debug_data.json`
   - Example path: `.debug/ContextAgent/get_new_change_message/20241226_211804/debug_data.json`

3. Create Test Cases
   - Use debug data to mock agent behavior
   - Reference `context_agent_test.ipynb` for examples of mocking and testing agents
