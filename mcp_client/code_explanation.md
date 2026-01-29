# Code Explanation for `client.py`
## 🔧 class MCPClient
- This class manages the entire lifecycle — from connection setup to chat interaction and cleanup.
### `__init__(self)`
- Sets up the client environment.
- Creates:
    - `self.session`: A communication session with the MCP server.
    - `self.exit_stack`: Used for proper cleanup of async contexts.
    - `self.anthropic`: Anthropic client initialized with the `ANTHROPIC_API_KEY` from `.env`.

### `connect_to_server(self, server_script_path: str)`
- Connects to a running MCP server (e.g., `weather.py`).
- Steps:
    - Detects whether the server script is Python or Node.js.
    - Constructs a command (either `python <path>` or `node <path>`).
    - Creates `StdioServerParameters` to define how to launch and communicate with the server via standard I/O streams.
    - Establishes a connection using `stdio_client()`.
    - Initializes a `ClientSession` — a two-way communication channel with the server.
    - Lists all available MCP tools by calling `session.list_tools()` (for `weather.py`, that would be `get_alerts` and `get_forecast`).

### `process_query(self, query: str) -> str`
- Handles a full LLM interaction cycle with MCP integration.
- **Step-by-step flow:**
    1. Creates a message list with the user’s input.
    2. Lists all available tools from the MCP server (each tool has a name, description, and JSON schema).
    3. Sends the query to Claude using the Anthropic API (claude-sonnet-4-5-20250929), along with tool definitions.
    4. Claude may respond with:
        - Regular text.
        - A `tool_use` directive (asking to call a specific MCP tool).
- When Claude requests a tool:
    5. The code executes the tool call via self.session.call_tool(tool_name, tool_args).
    6. Displays both the tool being called and its result.
    7. Feeds the tool result back into Claude (tool_result) so the model can continue reasoning.
    8. Appends any additional text or follow-up reasoning to `final_text`.

### `chat_loop(self)`
- Interactive REPL-like loop for user interaction.
    - Prints a startup message.
    - Continuously asks for user queries.
    - Sends each query to `process_query()`.
    - Displays Claude’s full response (including tool usage and results).
    - Type `'quit'` to exit.

### `cleanup(self)`
- Gracefully closes the async resources and connections (`exit_stack.aclose()`).

### `main()`
- The entry point when running `client.py directly` from the command line.
