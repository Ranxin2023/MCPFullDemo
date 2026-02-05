import asyncio
import threading
import streamlit as st
from typing import Optional
from contextlib import AsyncExitStack
# from concurrent.futures import Future

from anthropic import Anthropic
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from dotenv import load_dotenv

load_dotenv()

# -------------------- Async Loop Helper --------------------

class AsyncLoopThread:
    """Manages a persistent event loop in a background thread"""
    def __init__(self):
        self.loop = None
        self.thread = None

    def start(self):
        if self.thread is not None:
            return
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()
        # Wait for loop to be ready
        while self.loop is None:
            pass

    def _run_loop(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    def run_coroutine(self, coro):
        """Run a coroutine in the background loop and return the result"""
        if self.loop is None:
            self.start()
        future = asyncio.run_coroutine_threadsafe(coro, self.loop)
        return future.result()

    def stop(self):
        if self.loop:
            self.loop.call_soon_threadsafe(self.loop.stop)
        if self.thread:
            self.thread.join(timeout=5)

# -------------------- MCP Client --------------------

class MCPClient:
    def __init__(self, loop_thread: AsyncLoopThread):
        self.session: Optional[ClientSession] = None
        self.anthropic = Anthropic()
        self.loop_thread = loop_thread
        self.exit_stack = AsyncExitStack()

    async def connect(self, server_script_path: str):
        is_python = server_script_path.endswith(".py")
        is_js = server_script_path.endswith(".js")

        if not (is_python or is_js):
            raise ValueError("Server script must be .py or .js")

        command = "python" if is_python else "node"

        params = StdioServerParameters(
            command=command,
            args=[server_script_path],
            env=None,
        )

        stdio_transport = await self.exit_stack.enter_async_context(
            stdio_client(params)
        )
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

    async def ask(self, query: str) -> str:
        messages = [{"role": "user", "content": query}]

        tools_resp = await self.session.list_tools()
        tools = [{
            "name": t.name,
            "description": t.description,
            "input_schema": t.inputSchema
        } for t in tools_resp.tools]

        final_text = []

        # Allow multiple rounds of tool use
        while True:
            response = self.anthropic.messages.create(
                model="claude-sonnet-4-5-20250929",
                max_tokens=1000,
                messages=messages,
                tools=tools,
            )

            # Collect text and tool_use blocks
            tool_use_blocks = []
            for block in response.content:
                if block.type == "text":
                    final_text.append(block.text)
                elif block.type == "tool_use":
                    tool_use_blocks.append(block)

            # If no tool use, we're done
            if not tool_use_blocks:
                break

            # Execute all tools and collect results
            tool_results = []
            for tool_block in tool_use_blocks:
                result = await self.session.call_tool(tool_block.name, tool_block.input)

                tool_output = ""
                if isinstance(result.content, list):
                    tool_output = "\n".join(
                        getattr(x, "text", str(x)) for x in result.content
                    )
                else:
                    tool_output = str(result.content)

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_block.id,
                    "content": tool_output,
                })

            # Add assistant response and all tool results to messages
            messages.append({"role": "assistant", "content": response.content})
            messages.append({"role": "user", "content": tool_results})

        return "\n".join(final_text)

    async def close(self):
        await self.exit_stack.aclose()


# -------------------- Streamlit Setup --------------------

st.set_page_config(
    page_title="Claude MCP Agent",
    layout="wide",
)

st.title("🤖 Claude MCP Agent (Skills Enabled)")

# -------------------- Session State --------------------

if "loop_thread" not in st.session_state:
    st.session_state.loop_thread = AsyncLoopThread()
    st.session_state.loop_thread.start()

if "client" not in st.session_state:
    st.session_state.client = None

if "connected" not in st.session_state:
    st.session_state.connected = False

if "tools" not in st.session_state:
    st.session_state.tools = []

if "chat" not in st.session_state:
    st.session_state.chat = []  # list of (role, text)

# -------------------- Sidebar (Connection Panel) --------------------

with st.sidebar:
    st.header("🔌 MCP Server")

    server_path = st.text_input(
        "Server script",
        value="./server/main.py",
    )

    col1, col2 = st.columns(2)

    with col1:
        if st.button("Connect", type="primary"):
            try:
                client = MCPClient(st.session_state.loop_thread)
                with st.spinner("Connecting to server..."):
                    st.session_state.loop_thread.run_coroutine(
                        client.connect(server_path)
                    )
                with st.spinner("Loading tools..."):
                    tools = st.session_state.loop_thread.run_coroutine(
                        client.list_tool_names()
                    )
                st.session_state.client = client
                st.session_state.connected = True
                st.session_state.tools = tools
                st.success(f"Connected! Found {len(st.session_state.tools)} tools")
            except Exception as e:
                import traceback
                st.error(f"Connection failed: {e}")
                st.code(traceback.format_exc())

    with col2:
        if st.button("Disconnect"):
            try:
                if st.session_state.client:
                    st.session_state.loop_thread.run_coroutine(
                        st.session_state.client.close()
                    )
            except Exception:
                pass
            st.session_state.client = None
            st.session_state.connected = False
            st.session_state.tools = []
            st.info("Disconnected")

    st.divider()
    st.subheader("🛠 Tools")
    if st.session_state.connected:
        st.write(st.session_state.tools)
    else:
        st.write("Not connected")

# -------------------- Chat UI --------------------

for role, text in st.session_state.chat:
    with st.chat_message(role):
        st.markdown(text)

prompt = st.chat_input("Ask me something…")

if prompt:
    if not st.session_state.connected or not st.session_state.client:
        st.error("Please connect to the MCP server first.")
    else:
        # User message
        st.session_state.chat.append(("user", prompt))
        with st.chat_message("user"):
            st.markdown(prompt)

        # Assistant response
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    answer = st.session_state.loop_thread.run_coroutine(
                        st.session_state.client.ask(prompt)
                    )
                except Exception as e:
                    import traceback
                    answer = f"Error: {e}\n\n{traceback.format_exc()}"

            st.markdown(answer)

        st.session_state.chat.append(("assistant", answer))
