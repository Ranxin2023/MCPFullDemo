import asyncio
import threading
import streamlit as st
from typing import Optional
from contextlib import AsyncExitStack
from pathlib import Path
# import os

from anthropic import Anthropic
from anthropic.lib import files_from_dir
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from dotenv import load_dotenv
from skills_db import SkillsDatabase

load_dotenv()

# -------------------- Async Loop Helper --------------------


class AsyncLoopThread:
    def __init__(self):
        self.loop = None
        self.thread = None
        self._ready = threading.Event()

    def start(self):
        if self.thread and self.thread.is_alive():
            return
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()
        self._ready.wait()  # ✅ no busy-wait

    def _run_loop(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self._ready.set()   # ✅ signal loop is ready
        self.loop.run_forever()

    def run_coroutine(self, coro):
        if not self.loop:
            raise RuntimeError("Async loop not started. Call start() first.")
        fut = asyncio.run_coroutine_threadsafe(coro, self.loop)
        return fut.result()

    def stop(self):
        if self.loop:
            self.loop.call_soon_threadsafe(self.loop.stop)
        if self.thread:
            self.thread.join(timeout=2)

# -------------------- MCP Client with Skills --------------------

class MCPClient:
    def __init__(self, loop_thread: AsyncLoopThread):
        self.session: Optional[ClientSession] = None
        self.anthropic = Anthropic()
        self.loop_thread = loop_thread
        self.exit_stack = AsyncExitStack()
        self.db = SkillsDatabase()  # SQLite database for skills management

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

    def find_local_skills(self, base_path: str = "./.claude/skills") -> list[dict]:
        """
        scan local .claude/skills directory, find all effective skill folders
        
        Returns:
            list of dicts: [{"path": "...", "name": "...", "display_title": "..."}]
        """
        local_skills = []
        base_path = Path(base_path)
        
        if not base_path.exists():
            return local_skills
        
        # traverse all the subfolders
        for skill_dir in base_path.iterdir():
            if skill_dir.is_dir():
                skill_md = skill_dir / "SKILL.md"
                if skill_md.exists():
                    # fetch SKILL.md to obtain name and description
                    try:
                        with open(skill_md, 'r', encoding='utf-8') as f:
                            content = f.read()
                            # simple parse YAML frontmatter
                            if content.startswith('---'):
                                parts = content.split('---', 2)
                                if len(parts) >= 3:
                                    import yaml
                                    metadata = yaml.safe_load(parts[1])
                                    skill_name = metadata.get('name', skill_dir.name)
                                    skill_desc = metadata.get('description', '')
                                else:
                                    skill_name = skill_dir.name
                                    skill_desc = ''
                            else:
                                skill_name = skill_dir.name
                                skill_desc = ''
                        
                        local_skills.append({
                            "path": str(skill_dir),
                            "name": skill_name,
                            "display_title": skill_name.replace('-', ' ').title(),
                            "description": skill_desc
                        })
                    except Exception as e:
                        st.warning(f"Failed to read {skill_dir.name}: {e}")
        
        return local_skills

    def upload_skill(self, skill_path: str, display_title: str) -> str:
        """
        upload a custom skill

        Args:
            skill_path: skill's path(include SKILL.md)
            display_title: skill 's name

        Returns:
            skill_id: uploaded skill ID
        """
        skill = self.anthropic.beta.skills.create(
            display_title=display_title,
            files=files_from_dir(skill_path),
            betas=["skills-2025-10-02"]
        )

        # Update database with uploaded skill ID
        skill_name = display_title.lower().replace(' ', '-')
        self.db.mark_as_uploaded(skill_name, skill.id)

        return skill.id

    def upload_all_local_skills(self, base_path: str = "./.claude/skills") -> dict:
        """
        upload all the skills under .claude/skills/*

        Returns:
            dict: {"successful": [...], "failed": [...], "skipped": [...]}
        """
        local_skills = self.find_local_skills(base_path)
        results = {"successful": [], "failed": [], "skipped": []}

        # Sync local skills to database first
        self.db.sync_local_skills(local_skills)

        # Get existing skills to check for duplicates
        existing_skills = self.list_all_skills()
        existing_titles = {s["display_title"] for s in existing_skills}

        for skill in local_skills:
            # Skip if already exists
            if skill["display_title"] in existing_titles:
                results["skipped"].append({
                    "name": skill["name"],
                    "display_title": skill["display_title"],
                    "reason": "Already uploaded"
                })
                continue

            try:
                skill_id = self.upload_skill(
                    skill_path=skill["path"],
                    display_title=skill["display_title"]
                )
                results["successful"].append({
                    "name": skill["name"],
                    "display_title": skill["display_title"],
                    "skill_id": skill_id
                })
            except Exception as e:
                error_msg = str(e)
                # Handle duplicate errors gracefully
                if "reuse an existing display_title" in error_msg:
                    results["skipped"].append({
                        "name": skill["name"],
                        "display_title": skill["display_title"],
                        "reason": "Already uploaded"
                    })
                else:
                    results["failed"].append({
                        "name": skill["name"],
                        "error": error_msg
                    })

        return results

    def list_all_skills(self) -> list[dict]:
        """
        list all available skills(including official Anthropic's and customer)

        Returns:
            list of dicts with {id, display_title, source}
        """
        skills = self.anthropic.beta.skills.list(
            betas=["skills-2025-10-02"]
        )

        skill_list = [
            {
                "id": skill.id,
                "display_title": skill.display_title,
                "source": skill.source  # "anthropic" or "custom"
            }
            for skill in skills.data
        ]

        # Sync uploaded skills to database
        self.db.sync_uploaded_skills(skill_list)

        return skill_list

    def delete_skill(self, skill_id: str) -> bool:
        """
        Delete a custom skill by ID

        Attempts to delete all versions first, then the skill itself.

        Args:
            skill_id: The skill ID to delete

        Returns:
            bool: True if successful
        """
        try:
            # First, try to list and delete all versions
            try:
                versions = self.anthropic.beta.skills.versions.list(
                    skill_id=skill_id,
                    betas=["skills-2025-10-02"]
                )

                # Try to delete each version
                for version in versions.data:
                    try:
                        self.anthropic.beta.skills.versions.delete(
                            skill_id=skill_id,
                            version=version.version,
                            betas=["skills-2025-10-02"]
                        )
                    except Exception:
                        # Version deletion might fail with 500 or 404 errors (API bug)
                        # Try to continue anyway
                        pass
            except Exception:
                # If version listing/deletion fails, try to delete skill anyway
                pass

            # Now try to delete the skill itself
            # self.anthropic.beta.skills.delete(
            #     skill_id=skill_id,
            #     betas=["skills-2025-10-02"]
            # )

            # Remove from database
            self.db.delete_skill_by_id(skill_id)

            return True

        except Exception as e:
            error_msg = str(e)

            # Provide helpful error message for known API bug
            if "Cannot delete skill with existing versions" in error_msg:
                raise Exception(
                    "⚠️ Anthropic API Bug: Cannot delete this skill due to version conflicts. "
                    "\n\n💡 Good news: This skill is beyond the 8-skill limit, so it's not being used! "
                    "\nYou can safely ignore it, or contact Anthropic support to manually remove it."
                )
            else:
                raise Exception(f"Failed to delete skill: {e}")

    async def ask(self, query: str, available_skills: list[dict] = None) -> str:
        """
        Send query to Claude, supporting MCP tools and Skills.

        ALL available skills are passed to Claude, and Claude automatically
        decides which ones to use based on the user's query.

        Args:
            query: user query
            available_skills: all skills available to Claude, format: [{"type": "anthropic", "skill_id": "pdf", "version": "latest"}]
                            Claude will automatically choose which skills to invoke

        Returns:
            Claude's response
        """
        messages = [{"role": "user", "content": query}]

        # fetch MCP tools
        tools_resp = await self.session.list_tools()
        tools = [{
            "name": t.name,
            "description": t.description,
            "input_schema": t.inputSchema
        } for t in tools_resp.tools]
        
        # add code execution tool（Skills required）
        tools.append({
            "type": "code_execution_20250825",
            "name": "code_execution"
        })

        final_text = []

        # construct API parameters
        api_params = {
            "model": "claude-sonnet-4-5-20250929",
            "max_tokens": 4096,
            "messages": messages,
            "tools": tools,
        }

        # If there are available skills，add relavent parameters(Claude will automatically choose which to use)
        if available_skills:
            api_params["betas"] = ["code-execution-2025-08-25", "skills-2025-10-02"]
            api_params["container"] = {"skills": available_skills}

        # Allow multiple rounds of tool use
        while True:
            # Use beta.messages.create when skills are available, otherwise use regular messages.create
            if available_skills:
                response = self.anthropic.beta.messages.create(**api_params)
            else:
                response = self.anthropic.messages.create(**api_params)

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
                # MCP tool execution
                if tool_block.name != "code_execution":
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
                else:
                    # Code execution tool - handled by Anthropic
                    pass

            # Add assistant response and all tool results to messages
            messages.append({"role": "assistant", "content": response.content})
            if tool_results:
                messages.append({"role": "user", "content": tool_results})

        return "\n".join(final_text)

    async def close(self):
        await self.exit_stack.aclose()

    def get_skills_from_db(self) -> list[dict]:
        """
        Load all skills directly from SQLite database.
        """
        return self.db.get_all_skills()

# -------------------- Streamlit Setup --------------------

st.set_page_config(
    page_title="Claude MCP Agent + Skills",
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

if "available_skills" not in st.session_state:
    st.session_state.available_skills = []

if "local_skills" not in st.session_state:
    st.session_state.local_skills = []

# No need for enabled_skills anymore - all available skills are passed to LLM

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
                with st.spinner("Loading skills..."):
                    skills = client.list_all_skills()
                with st.spinner("Scanning local skills..."):
                    local_skills = client.find_local_skills()
                
                st.session_state.client = client
                st.session_state.connected = True
                st.session_state.tools = tools
                st.session_state.available_skills = skills
                st.session_state.local_skills = local_skills
                st.success(f"✅ Connected! Found {len(tools)} tools, {len(skills)} skills, {len(local_skills)} local skills")
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
            st.session_state.available_skills = []
            st.session_state.local_skills = []
            st.info("Disconnected")

    st.divider()
    
    # -------------------- Skills Management --------------------
    st.subheader("🎯 Skills Management")
    
    if st.session_state.connected:
        # Batch upload all local skills
        with st.expander("📤 Batch Upload Local Skills", expanded=True):
            st.write(f"**Found {len(st.session_state.local_skills)} local skills in `.claude/skills/`:**")
            
            if st.session_state.local_skills:
                for skill in st.session_state.local_skills:
                    st.write(f"• **{skill['display_title']}** (`{skill['name']}`)")
                    if skill.get('description'):
                        st.caption(f"  ↳ {skill['description']}")
                
                if st.button("🚀 Upload All Local Skills", type="primary"):
                    with st.spinner("Uploading all local skills..."):
                        results = st.session_state.client.upload_all_local_skills()
                        
                        if results["successful"]:
                            st.success(f"✅ Successfully uploaded {len(results['successful'])} skills:")
                            for s in results["successful"]:
                                st.write(f"  • {s['display_title']} → `{s['skill_id']}`")

                        if results.get("skipped"):
                            st.info(f"⏭️ Skipped {len(results['skipped'])} skills (already uploaded):")
                            for s in results["skipped"]:
                                st.write(f"  • {s['display_title']} - {s['reason']}")

                        if results["failed"]:
                            st.error(f"❌ Failed to upload {len(results['failed'])} skills:")
                            for f in results["failed"]:
                                st.write(f"  • {f['name']}: {f['error']}")

                        # Refresh skills list
                        skills = st.session_state.client.list_all_skills()
                        st.session_state.available_skills = skills
            else:
                st.info("No local skills found in `.claude/skills/`")
                st.caption("Create skill folders with SKILL.md files to get started")
        
        st.divider()
        
        # Manual upload single skill
        with st.expander("📝 Upload Single Skill"):
            skill_path = st.text_input(
                "Skill folder path",
                value="./.claude/skills/travel-briefing",
                help="Path to folder containing SKILL.md"
            )
            skill_title = st.text_input(
                "Display title",
                value="Travel Briefing",
                help="Name shown in the skills list"
            )
            if st.button("Upload Skill"):
                try:
                    with st.spinner("Uploading skill..."):
                        skill_id = st.session_state.client.upload_skill(skill_path, skill_title)
                        # Refresh skills list
                        skills = st.session_state.client.list_all_skills()
                        st.session_state.available_skills = skills
                    st.success(f"Uploaded! Skill ID: {skill_id}")
                except Exception as e:
                    import traceback
                    st.error(f"Upload failed: {e}")
                    st.code(traceback.format_exc())
        
        st.divider()

        # Database Statistics
        with st.expander("📊 Database Statistics", expanded=False):
            try:
                stats = st.session_state.client.db.get_stats()

                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Skills", stats['total'])
                with col2:
                    st.metric("Uploaded", stats['uploaded'])
                with col3:
                    st.metric("Local Only", stats['total'] - stats['uploaded'])

                st.caption(f"📂 Anthropic: {stats['anthropic']} | ⚙️ Custom: {stats['custom']} | 💾 Local: {stats['local']}")

                # Show all skills from database
                if st.checkbox("Show all database skills", value=False):
                    db_skills = st.session_state.client.db.get_all_skills()
                    if db_skills:
                        st.write("**Skills in Database:**")
                        for skill in db_skills:
                            status = "✅ Uploaded" if skill['is_uploaded'] else "📁 Local"
                            st.write(f"• **{skill['display_title']}** - {status}")
                            if skill['skill_id']:
                                st.caption(f"  ID: `{skill['skill_id']}`")
                            if skill['local_path']:
                                st.caption(f"  Path: `{skill['local_path']}`")
                    else:
                        st.info("No skills in database yet")
            except Exception as e:
                st.error(f"Failed to load database stats: {e}")

        st.divider()

        # Display all available skills (all will be passed to Claude)
        st.write("**Available Skills:**")

        total_skills = len(st.session_state.available_skills)
        if total_skills > 8:
            st.warning(f"⚠️ You have {total_skills} skills, but API limit is 8. Only the first 8 will be used.")
            st.caption("ℹ️ Consider removing some skills or manually selecting which to use.")
        else:
            st.caption("ℹ️ All skills below are automatically available to Claude. Claude will decide which ones to use based on your query.")

        if st.session_state.available_skills:
            for idx, skill in enumerate(st.session_state.available_skills):
                skill_type = skill["source"]  # "anthropic" or "custom"
                display_title = skill["display_title"]

                # Display skill with icon based on type
                icon = "🏢" if skill_type == "anthropic" else "⚙️"

                # Mark skills that won't be used (beyond the 8th)
                if idx >= 8:
                    st.write(f"~~{icon} **{display_title}** `({skill_type})`~~ ❌ *Not used*")
                else:
                    st.write(f"{icon} **{display_title}** `({skill_type})`")

            active_count = min(total_skills, 8)
            st.caption(f"🎯 **{active_count}/{total_skills} skill(s) active**")
        else:
            st.info("No skills available. Upload some skills first!")

        st.divider()

        # Delete skills section
        with st.expander("🗑️ Delete Skills"):
            st.caption("⚠️ You can only delete custom skills. Anthropic-managed skills cannot be deleted.")

            custom_skills = [s for s in st.session_state.available_skills if s["source"] == "custom"]

            if custom_skills:
                st.write(f"**Found {len(custom_skills)} custom skill(s):**")

                for skill in custom_skills:
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.write(f"⚙️ **{skill['display_title']}**")
                        st.caption(f"ID: `{skill['id']}`")
                    with col2:
                        if st.button("Delete", key=f"delete_{skill['id']}"):
                            try:
                                with st.spinner(f"Deleting {skill['display_title']}..."):
                                    # 1️⃣ Delete from DB
                                    st.session_state.client.delete_skill(skill['id'])

                                    # 2️⃣ Reload from DB (NOT Anthropic)
                                    db_skills = st.session_state.client.get_skills_from_db()

                                    # 3️⃣ Convert DB rows → UI format
                                    st.session_state.available_skills = [
                                        {
                                            "id": s["skill_id"],
                                            "display_title": s["display_title"],
                                            "source": s["source"],
                                        }
                                        for s in db_skills
                                        if s["skill_id"]  # only uploaded skills
                                    ]

                                st.success(f"✅ Deleted {skill['display_title']}")
                                st.rerun()

                            except Exception as e:
                                st.error(f"Failed to delete: {e}")
                                
            else:
                st.info("No custom skills to delete")
    else:
        st.write("Not connected")

    st.divider()
    st.subheader("🛠 MCP Tools")
    if st.session_state.connected:
        if st.session_state.tools:
            for tool in st.session_state.tools:
                st.write(f"• {tool}")
        else:
            st.info("No MCP tools available")
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
                    # Convert available skills to the format expected by API
                    # IMPORTANT: API limit is 8 skills maximum
                    skills_for_api = None
                    if st.session_state.available_skills:
                        all_skills = [
                            {
                                "type": skill["source"],
                                "skill_id": skill["id"],
                                "version": "latest"
                            }
                            for skill in st.session_state.available_skills
                        ]

                        # Limit to 8 skills (API constraint)
                        if len(all_skills) > 8:
                            st.warning(f"⚠️ You have {len(all_skills)} skills, but API limit is 8. Using first 8 skills.")
                            skills_for_api = all_skills[:8]
                        else:
                            skills_for_api = all_skills

                    # Pass all available skills to Claude - Claude will decide which to use
                    answer = st.session_state.loop_thread.run_coroutine(
                        st.session_state.client.ask(
                            prompt,
                            available_skills=skills_for_api
                        )
                    )
                except Exception as e:
                    import traceback
                    answer = f"Error: {e}\n\n{traceback.format_exc()}"

            st.markdown(answer)

        st.session_state.chat.append(("assistant", answer))