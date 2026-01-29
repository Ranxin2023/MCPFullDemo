import asyncio
import os
from typing import Optional
from contextlib import AsyncExitStack

import streamlit as st
from dotenv import load_dotenv
from anthropic import Anthropic

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

load_dotenv()


# --------- Async runner for Streamlit ----------
def get_loop() -> asyncio.AbstractEventLoop:
    """Streamlit reruns scripts; keep one event loop in session_state."""
    if "event_loop" not in st.session_state or st.session_state.event_loop.is_closed():
        st.session_state.event_loop = asyncio.new_event_loop()
    return st.session_state.event_loop


def run_async(coro):
    loop = get_loop()
    return loop.run_until_complete(coro)


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
        if not self.session:
            raise RuntimeError("Not connected. Click Connect first.")

        messages = [{"role": "user", "content": query}]

        # tools schema for Anthropic
        resp = await self.session.list_tools()
        available_tools = [
            {"name": t.name, "description": t.description, "input_schema": t.inputSchema}
            for t in resp.tools
        ]

        llm_response = self.anthropic.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=1000,
            messages=messages,
            tools=available_tools,
        )

        final_text = []
        assistant_message_content = []

        for content in llm_response.content:
            if content.type == "text":
                final_text.append(content.text)
                assistant_message_content.append(content)

            elif content.type == "tool_use":
                tool_name = content.name
                tool_args = content.input

                result = await self.session.call_tool(tool_name, tool_args)

                # show tool output
                tool_output = getattr(result, "content", None)
                if isinstance(tool_output, list):
                    parts = []
                    for item in tool_output:
                        parts.append(getattr(item, "text", str(item)))
                    tool_output_str = "\n".join(parts)
                elif isinstance(tool_output, str):
                    tool_output_str = tool_output
                else:
                    tool_output_str = str(tool_output)

                final_text.append(f"[Tool result: {tool_name}]\n{tool_output_str}")

                # continue conversation with tool_result
                assistant_message_content.append(content)
                messages.append({"role": "assistant", "content": assistant_message_content})
                messages.append(
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "tool_result",
                                "tool_use_id": getattr(content, "id", "unknown_id"),
                                "content": getattr(result, "content", str(result)),
                            }
                        ],
                    }
                )

                llm_response = self.anthropic.messages.create(
                    model="claude-sonnet-4-5-20250929",
                    max_tokens=1000,
                    messages=messages,
                    tools=available_tools,
                )

                if hasattr(llm_response.content[0], "text"):
                    final_text.append(llm_response.content[0].text)
                else:
                    final_text.append(str(llm_response.content[0]))

        return "\n".join(final_text)

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
        value="server/tools/weather_tools.py",
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
