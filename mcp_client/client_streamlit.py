from anthropic import Anthropic
from contextlib import AsyncExitStack
from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from pathlib import Path
from typing import Optional
import asyncio
import os
import streamlit as st
import time
load_dotenv()


def load_skills_text(max_chars: int = 12000) -> str:
    """
    Safely load skills.md for prompt injection.
    - Uses a conservative max_chars to avoid prompt bloat.
    - Returns empty string if file missing.
    """
    skills_path = Path(__file__).resolve().parent.parent / "skills.md"  # ../skills.md
    if not skills_path.exists():
        return ""

    text = skills_path.read_text(encoding="utf-8").strip()
    if len(text) > max_chars:
        text = text[:max_chars] + "\n\n...[skills.md truncated]"
    return text
# --------- Async runner for Streamlit ----------
def get_loop() -> asyncio.AbstractEventLoop:
    """Streamlit reruns scripts; keep one event loop in session_state."""
    if "event_loop" not in st.session_state or st.session_state.event_loop.is_closed():
        st.session_state.event_loop = asyncio.new_event_loop()
    return st.session_state.event_loop


def run_async(coro):
    loop = get_loop()
    return loop.run_until_complete(coro)

def log(msg: str):
    st.write(f"🧪 {msg}")

@st.cache_data
def get_skills_text():
    return load_skills_text()
SKILLS_TEXT = load_skills_text()

BASE_SYSTEM_PROMPT = f"""
You are an MCP tool-using assistant.

Below is the project's Skills Contract (skills.md). Follow it strictly when deciding which tools to call and when to stop.

--- BEGIN skills.md ---
{SKILLS_TEXT}
--- END skills.md ---

Hard rules:
- Never call the same tool repeatedly unless the previous attempt failed.
- save_briefing is a side-effect tool: call it at most once per user request.
- After save_briefing succeeds, stop calling tools and produce the final user-facing response.
""".strip()

# --------- MCP Client ----------
class MCPClient:
    def __init__(self):
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()

        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError("Missing ANTHROPIC_API_KEY (set it in .env).")

        self.anthropic = Anthropic(api_key=api_key)

    async def connect_to_server(self, server_script_path: str):
        is_python = server_script_path.endswith(".py")
        is_js = server_script_path.endswith(".js")
        if not (is_python or is_js):
            raise ValueError("Server script must be a .py or .js file")

        command = "python" if is_python else "node"
        server_params = StdioServerParameters(
            command=command,
            args=[server_script_path],
            env=None,
        )

        stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
        self.stdio, self.write = stdio_transport

        self.session = await self.exit_stack.enter_async_context(
            ClientSession(self.stdio, self.write)
        )

        await self.session.initialize()

    async def list_tool_names(self) -> list[str]:
        if not self.session:
            return []
        resp = await self.session.list_tools()
        return [t.name for t in resp.tools]

    async def process_query(self, query: str) -> str:
        messages = [{"role": "user", "content": query}]

        response = await self.session.list_tools()
        available_tools = [{
            "name": tool.name,
            "description": tool.description,
            "input_schema": tool.inputSchema
        } for tool in response.tools]

        final_text_parts = []

        MAX_TOOL_ROUNDS = 12
        rounds = 0

        # ✅ Persist across rounds
        briefing_saved = False
        
        base_system = (
            "You are an MCP agent. Use tools when necessary. "
            "Do not repeat the same tool call unless the previous attempt failed. "
            "Call save_briefing at most once per user request. "
            "After saving, stop calling tools and provide the final user-facing response."
        )
        while True:
            rounds += 1
            if rounds > MAX_TOOL_ROUNDS:
                # ✅ return whatever text we have so far (better UX)
                partial = "\n".join(final_text_parts).strip()
                if partial:
                    return partial + "\n\nStopped: too many tool-calling rounds (possible loop)."
                return "Stopped: too many tool-calling rounds (possible infinite loop)."
            system_prompt = BASE_SYSTEM_PROMPT
            if briefing_saved:
                system_prompt += "\n\nThe briefing has already been saved successfully. Do NOT call any tools. Answer now."

            messages = [m for m in messages if m.get("role") != "system"]
            log("Current message roles: " + str([m.get("role") for m in messages]))
            llm_response = self.anthropic.messages.create(
                model="claude-sonnet-4-5-20250929",
                max_tokens=1000,
                system=system_prompt,
                messages=messages,
                tools=available_tools
            )

            assistant_content = llm_response.content
            messages.append({"role": "assistant", "content": assistant_content})

            tool_uses = [c for c in assistant_content if c.type == "tool_use"]
            text_blocks = [c for c in assistant_content if c.type == "text"]

            for t in text_blocks:
                final_text_parts.append(t.text)

            # ✅ If the model didn’t request tools, we’re done.
            if not tool_uses:
                break

            log(f"LLM returned {len(tool_uses)} tool calls")

            tool_results = []

            # ✅ Execute ALL tool calls from this assistant message
            for tu in tool_uses:
                tool_name = tu.name
                tool_args = tu.input

                log(f"Calling tool: {tool_name} with args {tool_args}")

                t0 = time.time()
                result = await self.session.call_tool(tool_name, tool_args)
                log(f"Tool finished: {tool_name} in {time.time() - t0:.2f}s")

                tool_output = getattr(result, "content", result)

                # Convert MCP result.content to a string
                if isinstance(tool_output, list):
                    out_parts = []
                    for item in tool_output:
                        out_parts.append(getattr(item, "text", str(item)))
                    tool_output_str = "\n".join(out_parts)
                else:
                    tool_output_str = str(tool_output)

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tu.id,
                    "content": tool_output_str
                })

                # ✅ Mark side-effect tool completion AFTER the call succeeds
                if tool_name == "save_briefing":
                    briefing_saved = True
                    # optional: try to extract id if your save tool returns JSON text
                    # saved_briefing_id = ...

            # 🚨 CRITICAL: tool_result must be IMMEDIATELY next message after tool_use
            messages.append({"role": "user", "content": tool_results})

            # ✅ Only AFTER tool_results, we can guide the model to stop tools
            if briefing_saved:
                messages.append({
                    "role": "system",
                    "content": (
                        "The briefing has been successfully saved. "
                        "Do NOT call any more tools. "
                        "Provide the final user-facing response now, including the saved briefing title and id if available."
                    )
                })

        return "\n".join(final_text_parts).strip()


    async def cleanup(self):
        await self.exit_stack.aclose()


# --------- Streamlit UI ----------
st.set_page_config(page_title="MCP Client (Streamlit)", layout="centered")
st.title("MCP Client (Streamlit)")

# init state
if "mcp_client" not in st.session_state:
    st.session_state.mcp_client = None
if "connected" not in st.session_state:
    st.session_state.connected = False
if "tool_names" not in st.session_state:
    st.session_state.tool_names = []
if "chat" not in st.session_state:
    st.session_state.chat = []  # list of (role, text)


with st.sidebar:
    st.header("Connection")
    server_path = st.text_input(
        "Server script path",
        value="../server/main.py",
        help="Path to your MCP server script (.py or .js)",
    )

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Connect", type="primary"):
            try:
                st.session_state.mcp_client = MCPClient()
                run_async(st.session_state.mcp_client.connect_to_server(server_path))
                st.session_state.connected = True
                st.session_state.tool_names = run_async(
                    st.session_state.mcp_client.list_tool_names()
                )
                st.success("Connected!")
            except Exception as e:
                st.session_state.connected = False
                st.session_state.tool_names = []
                st.error(f"Connect failed: {e}")

    with col2:
        if st.button("Disconnect"):
            try:
                if st.session_state.mcp_client is not None:
                    run_async(st.session_state.mcp_client.cleanup())
            except Exception:
                pass
            st.session_state.mcp_client = None
            st.session_state.connected = False
            st.session_state.tool_names = []
            st.info("Disconnected.")

    st.divider()
    st.subheader("Tools")
    if st.session_state.connected:
        st.write(st.session_state.tool_names)
    else:
        st.write("Not connected.")


# render chat history
for role, text in st.session_state.chat:
    with st.chat_message(role):
        st.markdown(text)

# chat input
prompt = st.chat_input("Ask something (e.g., 'Search web for MCP tutorials')")

if prompt:
    if not st.session_state.connected or st.session_state.mcp_client is None:
        st.error("Please connect to the server first.")
    else:
        st.session_state.chat.append(("user", prompt))
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    answer = run_async(st.session_state.mcp_client.process_query(prompt))
                except Exception as e:
                    answer = f"Error: {e}"
            st.markdown(answer)

        st.session_state.chat.append(("assistant", answer))
