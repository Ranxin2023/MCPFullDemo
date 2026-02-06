# Explanation of `client_streamlit.py`
## 1) What this file is
### client_streamlit.py is a Streamlit UI that:
- Connects to an MCP server over stdio (launches `python <server_script>` or `node <server_script>`).
- Fetches the server’s **MCP tools** (`session.list_tools()`).
- Fetches **Anthropic Skills** (official + your custom uploaded skills).

## 2) `AsyncLoopThread`: why it exists
- Streamlit is not asyncio-native. All Streamlit callbacks (st.button, st.chat_input, etc.) run in a synchronous execution model, which means you cannot directly await asynchronous functions such as:
    - `await session.call_tool(...)`
    - `await connect(...)`
    - `await anthropic.messages.create(...)`
- However, MCP servers and Anthropic APIs are asynchronous by design and require an active `asyncio` event loop.
- To bridge this gap, the application uses `AsyncLoopThread`.
### What AsyncLoopThread Does
- AsyncLoopThread runs one persistent asyncio event loop in a dedicated background thread and provides a safe way for Streamlit’s synchronous code to execute asynchronous MCP and Claude operations.
- Specifically, it:
    - Creates a **daemon background thread**
    - Initializes a **single asyncio event loop** inside that thread
    - **Blocks the main thread until the loop is ready** using a `threading.Event` (no busy-wait)
    - Keeps the event loop alive indefinitely using `run_forever()`
### Key Methods (Based on the Actual Code)
- `start()`
    - Starts the background thread and **waits until the event loop is created**.
    - If the thread is already running, it safely returns without creating another loop.
- `_run_loop()`
    - Runs inside the background thread:
        - Creates a new asyncio event loop
        - Registers it with `asyncio.set_event_loop`
        - Signals readiness to the main thread via `_ready.set()`
        - Keeps the loop alive using `loop.run_forever()`
- `run_coroutine(coro)`
    - Submits a coroutine to the background event loop using `asyncio.run_coroutine_threadsafe(...)` and blocks until the coroutine completes, returning its result to the caller.
- `stop()`
    - Requests the event loop to stop and joins the background thread with a timeout for graceful shutdown.
    
## 3) `MCPClient`: your “brain” that connects MCP + Claude + Skills
### This class manages:
- MCP session lifecycle
- Listing tools
- Skill discovery & upload
- Sending a user prompt to Claude with **tools + skills**, then handling tool calls
### `__init__`
- Key fields:
    - `self.session`: MCP session after connecting
    - `self.anthropic = Anthropic()` : Anthropic client (reads env like `ANTHROPIC_API_KEY` via `load_dotenv()` at top)
    - `self.exit_stack = AsyncExitStack()`: ensures stdio transport + session get closed cleanly
    - `self.uploaded_skills`: maps display_title → skill.id (local bookkeeping)

### `connect(server_script_path)`
- Detects `.py` or `.js`
- Builds `StdioServerParameters(command="python"/"node", args=[server_script_path])`
- Creates the stdio transport via `stdio_client(params)`
- Creates `ClientSession(self.stdio, self.write)`
- Calls `await self.session.initialize()`
- **Effect**: your Streamlit app can now call MCP tools from the server.

### `list_tool_names()`
- Calls `session.list_tools()`
- Returns `[tool.name, ...]` for sidebar display

## 4) Skill management functions
### `find_local_skills(base_path="./.claude/skills")`
- Scans `.claude/skills/*/SKILL.md` and tries to extract YAML frontmatter metadata:
    - Looks for folders under `base_path`
    - For each folder, if `SKILL.md` exists:
        - Reads file
        - If it starts with `---`, it splits and parses YAML
    - Extracts:
        - `name`
        - `description`
    - Builds a list of:
        ```py
        {
        "path": "...",
        "name": "...",
        "display_title": "...",  # title-cased
        "description": "..."
        }

        ```

### `upload_skill(skill_path, display_title)`
- Uploads a local skill folder to Anthropic:
    - `anthropic.beta.skills.create(display_title=..., files=files_from_dir(skill_path), betas=["skills-2025-10-02"])`
    - Stores the returned `skill.id` into `self.uploaded_skills`
- **Important**: This is **Anthropic Skills** API (not MCP). The “skill folder” must include `SKILL.md` and any referenced files.

## 5) The core: `ask(query, available_skills=None)`
### Step A — build messages
- Starts with:
```py
messages = [{"role": "user", "content": query}]
```
### Step B — fetch MCP tools and convert to Anthropic tool schema
- It calls:
```py
tools_resp = await self.session.list_tools()

```
- Then builds:
```py
tools = [{
  "name": t.name,
  "description": t.description,
  "input_schema": t.inputSchema
} for t in tools_resp.tools]

```
### Step C — add code execution tool (required for skills workflows)
```
api_params["betas"] = ["code-execution-2025-08-25", "skills-2025-10-02"]
api_params["container"] = {"skills": available_skills}

```
### Step D — choose API mode (beta vs normal)
- If `available_skills` is provided, it uses:
    - `anthropic.beta.messages.create`
    - and sets:
    ```py
    api_params["betas"] = ["code-execution-2025-08-25", "skills-2025-10-02"]
    api_params["container"] = {"skills": available_skills}

    ```

## 6) Streamlit UI layout
### Page config + title
- Wide layout, title: “Claude MCP Agent (Skills Enabled)”.
### Session state keys
- It stores: 
    - `loop_thread` (background asyncio loop)
    - `client` (MCPClient instance)
    - `connected`
    - `tools` (tool names)
    - `available_skills` (remote skills list)
    - `local_skills` (scanned local skills)
    - `chat` (chat history tuples)

### Sidebar: “MCP Server”
- Text input `server_path` default `./server/main.py`
- Buttons:
    - 
### Sidebar: “Skills Management”
- Only shown when connected:
    - Batch upload expander:
        - shows local skills found
        - Upload All button → calls `upload_all_local_skills()`
        - refreshes remote skills list afterward
    - Manual upload expander:
        - input path + display title
        - Upload Skill button → `upload_skill(...)` and refresh skills list
    - Displays all available skills:
        - icon for anthropic vs custom
        - note: “All skills are automatically available”
### Chat area
- Replays history with `st.chat_message(role)`
- `st.chat_input(...)` for new prompt
- On prompt:
    - 1. Add user message to history
    - 2. Convert skills into API format:
    ```py
    skills_for_api = [{
    "type": skill["source"],
    "skill_id": skill["id"],
    "version": "latest"
    } ...]

    ```
    - 3. Calls `client.ask(prompt, available_skills=skills_for_api)`
    - 4. Renders assistant response and stores in history
    