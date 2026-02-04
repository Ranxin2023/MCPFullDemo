# Agent Skills
## Table Of Contents
- [What are Skills?](#what-are-skills)
    - [Overview](#overview)
    - [How SKills Work](#how-skills-work)
    - [The `Skill.md` File](#the-skillmd-file)
        - [SKILL.md = YAML frontmatter + Markdown body](#1-skillmd--yaml-frontmatter--markdown-body)
        - [Required Frontmatter Fields](#2-required-frontmatter-fields)
- [Agent Skils Diagram](#agent-skills-diagram)
    - [Core System Prompt](#1-core-system-prompt)
    - [Equipped Skills (blue tags)](#2-equipped-skills-blue-tags)
    - [Equipped MCP Servers](#3-equipped-mcp-servers)
- [Skills Speficication](#skills-specification)
    - [The Name Field (Identity + Filesystem Contract)](#1-the-name-field-identity--filesystem-contract)
    - [The Description Field (Routing Intelligence)](#2-the-description-field-routing-intelligence)
    - [License Field (Legal + Reuse Clarity)](#3-license-field-legal--reuse-clarity)
- [How Skills Work](#how-skills-work-1)
    - [Claude is Not “just a prompt” Anymore](#1-claude-is-not-just-a-prompt-anymore)
    - [Progressive Disclosure (Why This Matters)](#2-progressive-disclosure-why-this-matters)
    - [Three Types of Skill Content → Three Loading Levels](#3-three-types-of-skill-content--three-loading-levels)
        - [Level 1: Metadata (always loaded)](#level-1-metadata-always-loaded)
    - [How Claude Actually Loads These (Step-By-Step)](#4-how-claude-actually-loads-these-step-by-step)
- [Where Skills Work](#where-skills-work)
    - [Claude API (most powerful, most explicit)](#1-claude-api-most-powerful-most-explicit)
    - [Claude Code (local, filesystem-based)](#2-claude-code-local-filesystem-based)
    - [Claude Agent SDK (programmatic agents)](#3-claude-agent-sdk-programmatic-agents)
- [Integrate Skills Into Your Agent](#integrate-skills-into-your-agent)
    - [Integration Approaches](#integration-approaches)
        - [Filesystem-Based Agents (the “full power” model)](#1-filesystem-based-agents-the-full-power-model)
        - [Tool-Based Agents (the Constrained Model)](#2-tool-based-agents-the-constrained-model)
    - [The 5-Step Lifecycle](#the-5-step-lifecycle)
        - [Discover Skills](#step-1-discover-skills)
        - [Load Metadata at Startup](#step-2-load-metadata-at-startup)
        - [Match User Tasks to Skills](#step-3-match-user-tasks-to-skills)
        - [Activate Skills](#step-4-activate-skills)
        - [Execute scripts / access resources](#step-5-execute-scripts--access-resources)

## What are skills?
### Overview
#### What is an “Agent Skill”
- Agent Skills are a lightweight, open format for extending AI agent capabilities with specialized knowledge and workflows.
- A skill is a packaged capability you give to an AI agent so it knows:
    - What it is good at
    - How to do a specific task
    - What rules, steps, or references to follow
    - What code to run

#### Why Skill Exist
- Without skills, an agent:
    - Only has general reasoning
    - Needs long prompts every time
    - Forgets structured workflows
    - Has no persistent task identity
- With skills:
    - Knowledge is **modular**
    - Behavior is **repeatable**
    - Instructions are **versioned**
    - Tools + instructions stay **aligned**
### How skills work
#### Skills use progressive disclosure to manage context efficiently
- Progressive disclosure means:
    - Don’t load everything upfront
    - Only reveal more details when they’re actually needed

#### The 3 phases of how skills work
1. Discovery (startup phase)
- At startup, agents load only the name and description of each available skill
- **What actually happens here**
    - When your agent boots:
        - It does NOT read every `SKILL.md`
        - It only loads:
            - `name`
            - `description`
        - That’s it.
    - Example:
    ```json
    [
        {
            "name": "Weather Analyst",
            "description": "Get US weather forecasts and alerts"
        },
        {
            "name": "Web Scraper",
            "description": "Extract readable content from webpages"
        }
    ]

    ```
- **Why this is critical**
    - Keeps startup fast
    - Keeps base prompt small
    - Prevents instruction overload
    - Lets the agent decide relevance instead of guessing

2. **Activation (matching phase)**
- When a task matches a skill’s description, the agent reads the full `SKILL.md`
- What triggers activation?
    - “What’s the weather in San Diego?”
    - “Scrape this webpage”
    - “Search for recent AI news”
- The agent:
    - 1. Compares the query
    - 2. Matches it against skill descriptions
    - 3. Chooses the most relevant skill
    - 4. Loads the full `SKILL.md` into context
3. **Execution (doing the work)**
- The agent follows the instructions, optionally loading files or executing code
- The agent will:
    - Follow the workflow defined in `SKILL.md`
    - Decide which tools to call
    - Use references if mentioned
    - Respect constraints (format, safety, validation)
- Important clarification
    - Skills **do not execute tools themselves**.

#### So the flow is:
```sql
User question
   ↓
Skill activated
   ↓
Skill instructions guide reasoning
   ↓
Agent calls MCP tools
   ↓
Tools return results
   ↓
Agent formats output per skill rules

```
### The `SKILL.md` File
#### 1. SKILL.md = YAML frontmatter + Markdown body
- A SKILL.md file has two parts:
    - **A) YAML “frontmatter” (the metadata header)**
        - It’s the block at the very top between --- lines:
        ```yaml
        ---
        name: pdf-processing
        description: Extract text and tables from PDF files, fill forms, merge documents.
        ---

        ```
        - What this is for:
            - The agent can load just this during **Discovery** (startup).
            - It enables **fast routing**: “Do I have a skill relevant to PDFs?”
    - **B) Markdown body (the actual instructions)**
        - Everything after the frontmatter is just normal Markdown:
        ```md
        # PDF Processing

        ## When to use this skill
        Use this skill when the user needs to work with PDF files...

        ## How to extract text
        1. Use pdfplumber...

        ## How to fill forms
        ...

        ```
        - What this is for:
            - Loaded during Activation
            - Gives the agent step-by-step workflow + rules + output format

#### 2. Required frontmatter fields
- The screenshot says the required fields are:
    - `name`: “A short identifier”
    - `description`: “When to use this skill”
- `name` best practices
    - short, stable, lowercase/kebab-case is common
    - should be unique across skills
    - should not be a whole sentence
    - ✅ good: `pdf-processing`, `web-scrape`, `weather-alerts`
    - ❌ bad: `How to process PDFs skill v2 final`
- `description` best practices  
    - This is extremely important because it drives **matching**.
    - A good description:
        - says when to use it (user intent)
        - lists typical tasks
        - uses keywords the user might say

#### 3. What goes in the Markdown body (and why)
- Recommended sections
1. **When to use this skill**
- triggers/keywords
- what problems it solves
2. **Inputs to ask for / assumptions**
- what info you need from the user
3. **Workflow**
- numbered steps the agent should follow
4. **Tool usage rules (if tools exist)**
- which tools to call
- when to call them
- constraints (rate limits, safety, validation)
5. **Output format**
- bullet list / JSON / table / short summary + details

#### 4. Why this format is useful (the 3 advantages)
- **Self-documenting**
    - Humans can read it easily:
        - reviewers can audit it
        - teammates can improve it
        - debugging is straightforward (“the instruction says X”)
- **Extensible**
    - You can start simple:
        - just text instructions
    - …and later expand:
        - add scripts/
        - add references/
        - add templates/assets/
        - add examples
    - So skills can scale from “tiny” to “production-grade”.
- **Portable**
    - A skill is “just files”.
    - That means:
        - easy to version in Git
        - easy to share between projects
        - easy to copy/paste into a new agent

#### 5. How this relates to your MCP agent + tools (important)
- In your MCP setup:
    - MCP tools are real functions (`@mcp.tool()`) that execute.
    - `SKILL.md` is the **policy + workflow** that tells the LLM how and when to call those tools.
- So a solid pattern is:
    - Tool docstrings explain what the function does
    - `SKILL.md` explains how to solve the whole task end-to-end
#### 6. A concrete example for YOUR project (Weather + Web tools)
- Here’s a “good” `SKILL.md` style for your MCP tools:
```md
---
name: web-research
description: Search the web for up-to-date info and summarize results with sources. Use for current events, docs lookup, comparisons, and verification.
---

# Web Research

## When to use this skill
Use when the user asks for:
- latest info, news, prices, releases
- “look this up”, “verify”, “find sources”
- links or citations

## Tools
- web_search(query, num_results, country)

## Workflow
1. Turn the user request into 1–3 search queries.
2. Call web_search.
3. Extract the key points from the top results.
4. Return a structured summary:
   - 3–5 bullet takeaways
   - list of sources (title + url)
5. If results conflict, note the disagreement instead of guessing.

```
## Agent Skills Diagram
![Agent Skils Computer](images/agent_skills_computer.png)
### 1. Core system prompt
- This is the agent’s baseline personality and rules.
- Examples:
    - “You are a helpful assistant”
    - Safety rules
    - Output tone
    - High-level behavior constraints
### 2. Equipped Skills (blue tags)
- Examples shown:
    - bigquery
    - docx
    - nda-review
    - pdf
    - pptx
    - xlsx
- These are **skills you’ve installed** for this agent.
### 3. Equipped MCP servers
- Examples:
    - MCP server 1
    - MCP server 2
    - MCP server 3
- These are **external capability providers**.
### 4. Remote MCP servers
- Shown at the bottom:
    - “Remote MCP servers (elsewhere on the internet)”
- This highlights:
    - MCP servers do not live inside the agent
    - They can be local or remote
    - They expose tools via a standard protocol
### 5. Bash / Python / Node.js
- These represent:
    - Execution runtimes available to the agent
    - Languages the agent can use if needed
- Important:
    - The agent does not invent these
    - They’re provided by the environment
- Examples:
    - Bash: file ops, CLI tools
    - Python: scripts, parsing, automation
    - Node.js: JS tooling, web tasks

### 6. File system (critical part)
- This is where skills **physically live**.
- The green note says:
    - “Contents of skill directories live in the agent computer’s file system”
- That means:
    - Each skill is a real folder
    - Not just text in a prompt
    - The agent can read them when activated
### Skills as directories (blue boxes)

## Skills Specification
![Skill Spefication](./images/skill_specification.png)
### 1. The `name` field (identity + filesystem contract)
- **The required name field**
- The name is not just a label — it’s an identifier that must stay consistent across the system.
- Think of it as:
    - a package name
    - a command name
    - a directory name
    - a routing key
#### 1.1 Length rule (1–64 characters)
- Must be 1–64 characters

- Why:
    - Short enough for prompts and logs
    - Long enough to be descriptive
    - 
#### 1.2 Allowed characters (lowercase alphanumeric + hyphen)
- May only contain unicode lowercase alphanumeric characters and hyphens (`a-z`, `0-9`, `-`)
- Why this exists:
    - Safe across filesystems
    - Safe in URLs
    - Safe in JSON/YAML
    - Easy to tokenize for LLMs
- No spaces, no underscores, no uppercase.

#### 1.3 Must not start or end with `-`
- Must not start or end with hyphen
- Why:
    - Prevents ambiguous parsing
    - Avoids ugly edge cases (`-skill`, `skill-`)
    - Matches package naming conventions (npm, pip, docker)

#### 1.4 No consecutive hyphens (`--`)
- Must not contain consecutive hyphens
- Why:
    - Prevents accidental separators
    - Avoids parsing ambiguity
    - Encourages readable names
- Instead of:
    ```css
    pdf--processing

    ```
- Use:
    ```css
    pdf-processing

    ```

#### 1.5 Must match the parent directory name (very important)
- Must match the parent directory name
- This is the filesystem ↔ metadata binding.
- Example:
    - 

### 2. The description field (routing intelligence)
- **The required `description` field**
- This field is how the agent decides to activate the skill.
- If the description is bad, the skill is effectively invisible.
#### 2.1 Length rule (1–1024 characters)
- Must be 1–1024 characters
- Why:
    - Enough space for meaningful intent description
    - Prevents prompt bloat
    - Forces concise writing
#### 2.2 Must describe BOTH “what” and “when”
- Should describe both what the skill does and when to use it
- This is the most common mistake.
- Bad description only says what:
    - “Extracts text from PDFs.”
- Good description says what + when:
    - “Extracts text and tables from PDF files. Use when the user needs to read, analyze, or process PDF documents.”
#### 2.3 Should include keywords (critical for matching)
- Should include specific keywords that help agents identify relevant tasks
- The agent matches user intent ↔ description text.
- So include:
    - verbs users say
    - file types
    - task types
    - synonyms
- For PDFs:
    - extract
    - fill forms
    - tables
    - merge
    - split
    - OCR
    
### 3. `license` field (legal + reuse clarity)
- **The optional `license` field specifies the license applied to the skill**
- **What this field is for**
    - This field answers one simple question:
        - “Under what legal terms can this skill be used, copied, or modified?”
    - Remember: a skill may include:
        - instructions
        - code (.py, .sh)
        - templates
        - reference docs
    - Those are **copyrightable assets**.
- Why the spec recommends keeping it short
    - “Either the name of a license or the name of a bundled license file”
    - This is deliberate:
        - The frontmatter stays compact
        - Full legal text lives elsewhere
        - Machines don’t need legal prose
    - Example from the screenshot:
    ```yaml
    license: Proprietary. LICENSE.txt has complete terms

    ```
    - Meaning:
        - This skill is **not open source**
        - Full terms are in `LICENSE.txt` in the skill directory
### 4. `compatibility` field (environment contract)
#### Rules from the spec
- Must be **1–500 characters**
- Only include it **if requirements exist**
- Used to declare:
    - runtime assumptions
    - system packages
    - network access
    - 
## How Skills Work
### 1. Claude is not “just a prompt” anymore
- “Claude operates in a virtual machine with filesystem access…”
- This means: 
    - Claude can:
        - read files
        - execute scripts
        - load docs on demand
    - Skills are **real directories**
    - Instructions are **persistent files**
- Think of it like:
    - Onboarding docs for a new engineer, stored in a repo — not pasted into Slack every time.

### 2. Progressive disclosure (why this matters)
- “Claude loads information in stages as needed”
- Without this:
    - Every skill would blow up context
    - You’d be limited to ~3–5 skills
    - Instructions would conflict
- With progressive disclosure:
    - You can install dozens or hundreds of skills
    - Only the relevant one enters context
    - Heavy resources never enter context at all
### 3. Three types of skill content → three loading levels
#### Level 1: Metadata (always loaded)
- **What it is**
    - YAML frontmatter from `SKILL.md`
    - Only:
        - name
        - description
        - (plus optional metadata fields)
    - Example:
        ```yaml
        name: pdf-processing
        description: Extract text and tables from PDF files, fill forms, merge documents.

        ```
    - When it loads
        - **At agent startup**
        - Included in the **system prompt**
#### Level 2: Instructions (loaded when triggered)
- **What it is**
    - The **Markdown** body of `SKILL.md`
    - Workflows
    - Best practices
    - Guidance
- Example:
    ```md
    ## Quick start
    Use pdfplumber to extract text from PDFs...

    ```
- **When it loads**
    - **Only after the user request matches the skill description**
    - Loaded by reading `SKILL.md` from disk
- **Token cost**
    - Under ~5k tokens
    - Only for the active skill

#### Level 3: Resources and code (loaded as needed)
- This is the power move.
- **What lives here**
    - Extra markdown files:
        - `FORMS.md`
        - `REFERENCE.md`
    - Scripts:
        - `fill_form.py`
        - `validate.py`
    - Schemas
    - Templates
    - Examples
- Directory example:
```markdown
pdf-skill/
├── SKILL.md
├── FORMS.md
├── REFERENCE.md
└── scripts/
    └── fill_form.py

```
- How these are loaded (key detail)
    - They are NOT loaded into context by default.
    - Instead: Claude
        - reads files when referenced
        - runs scripts via bash
    - Scripts execute without consuming context tokens
- This is why the table says:
    - Token cost: effectively unlimited
### 4. How Claude actually loads these (step-by-step)
#### Step 1 — Metadata match
- Claude compares:
    - user request
    - all skill descriptions
- Finds:
    - `pdf-processing`
#### Step 2 — Instruction load
- Claude:
    - reads `skills/pdf-processing/SKILL.md`
    - loads Markdown body into context
#### Step 3 — Resource access
- Instruction says:
    - “For advanced form filling, see FORMS.md”
- Claude:
    - reads `FORMS.md` from disk
    - or runs `fill_form.py` via bash
- Only then is it used.

## Where Skills Work
### 1. Claude API (most powerful, most explicit)
- What it supports
    - Pre-built Agent Skills
    - Custom Skills
    - Both behave identically at runtime
- The difference is **how you reference them**.
### 2. Claude Code (local, filesystem-based)
#### What it supports
- ✅ Custom Skills only
- ❌ Pre-built Skills
#### How Skills work here
- “Create Skills as directories with SKILL.md files. Claude discovers and uses them automatically.”
- This is the most developer-friendly model.
    - Skills live in your local filesystem
    - No API uploads
    - No skill IDs
    - No headers
    - Just folders + `SKILL.md`

- Claude Code:
    - scans skill directories
    - loads `{name, description}`
    - activates skills automatically
#### Key property
- “Custom Skills in Claude Code are filesystem-based and don’t require API uploads.”
- This is perfect for local MCP-style development.

### 3. Claude Agent SDK (programmatic agents)
#### What it supports
- ✅ Custom Skills
- Filesystem-based configuration

#### Where skills live
- “Create Skills as directories with SKILL.md files in `.claude/skills/`”
- This directory is the **canonical location** for SDK-based agents.
- Example:
```objectivec
.claude/
  skills/
    web-research/
      SKILL.md
    weather/
      SKILL.md

```
#### How to enable them
- “Enable Skills by including skill in your allowed-tools configuration.”
- This is a **security gate**:
    - Skills are treated like tools
    - You must explicitly allow them
- Once enabled:
    - Skills are auto-discovered at runtime
    
### 4. Claude.ai (web UI)
- **What it supports**
    - ✅ Pre-built Skills
    - ✅ Custom Skills
- Pre-built Skills (automatic)
    - “These Skills are already working behind the scenes”
- When you:
    - create documents
    - edit spreadsheets
    - work with PDFs
- Claude is already using skills like:
    - `docx`
    - `pptx`
    - `xlsx`
- You just don’t see them.
### 5. Critical differences summarized
| **Environment** |  **Skills type**   | **How loaded**    | Shared?    | **Best for**        |
| --------------- | ------------------ | ----------------- | ---------- | ------------------- |
| Claude API      | Pre-built + Custom | API + headers     | Org-wide   | Production, SaaS    |
| Claude Code     | Custom only        | Filesystem        | Local      | Dev, MCP-like work  |
| Agent SDK       | Custom only        | `.claude/skills/` | App-scoped | Programmatic agents |
| Claude.ai       | Both               | UI upload         | Per-user   | Power users         |

## Integrate skills into your agent
### Integration Approaches
#### 1. Filesystem-based agents (the “full power” model)
- “Operate within a computer environment (bash/unix)”
- **What this really means**
    - Your agent:
        - Has access to a **real or virtual machine**
        - Can run shell commands
        - Can read files from disk
        - Can execute scripts
    - Skills exist as **real directories** on disk.
    - Example:
    ```bash
    skills/
        pdf-processing/
            SKILL.md
            FORMS.md
            scripts/fill_form.py

    ```
- **How skills activate in this model**
    - “Skills are activated when models issue shell commands like `cat /path/to/my-skill/SKILL.md`”
    - This is critical:
        - The **model itself decides** when to load a skill
        - It does so by reading the file via bash
        - That read is what brings instructions into context
    - So activation looks like:
        ```sql
        User asks → model decides → model reads SKILL.md → instructions enter context

        ```
#### 2. Tool-based agents (the constrained model)
- “Function without a dedicated computer environment”
- **What this really means**
    - Your agent:
        - Cannot run bash
        - Cannot read arbitrary files
        - Cannot execute scripts directly
    - Instead, **you provide tools** that simulate these actions.

- **How skills work here**
    - You (the developer) implement tools like:
        - `load_skill_metadata(skill_name)`
        - `load_skill_instructions(skill_name)`
        - `run_skill_script(skill_name, script_name)`
        - `read_skill_resource(skill_name, file)`
    - The model:
        - Calls tools
        - Tools fetch skill content
        - Tools return results
    - So you manually recreate what a filesystem would give you for free.
- **Tradeoffs**
    - ✅ Works in restricted environments
    - ❌ More engineering work
    - ❌ Less flexible
    - ❌ Harder to scale
    - ❌ Easy to leak tokens

### The 5-step lifecycle
#### Step 1: Discover skills
- “Discover skills in configured directories”
- What this means:
    - Scan one or more directories
    - Each subdirectory = one skill
    - Look for `SKILL.md`
- Example logic:
```text
for each folder in skills/:
  if SKILL.md exists → register skill

```
#### Step 2: Load metadata at startup
- “Load metadata (name and description) at startup”
- Important:
    - Only YAML frontmatter
    - NOT the full instructions
- This gives you:
    - Skill registry
    - Routing signals
    - No context explosion
- At this point the agent only knows:
    - “These skills exist, and this is when to use them.”
#### Step 3: Match user tasks to skills
- “Match user tasks to relevant skills”
- This is pure intent matching.
- The agent compares:
    - User request
    - Skill descriptions
- This can be:
    - LLM reasoning
    - Keyword matching
    - Embeddings
    - Hybrid logic
#### Step 4: Activate skills
- “Activate skills by loading full instructions”
- This is the key transition.
- Activation means:
    - Read `SKILL.md` body
    - Bring workflows into context
    - Constrain behavior
- Only now does the skill “take control”.
#### Step 5: Execute scripts / access resources
- “Execute scripts and access resources as needed”
- This is Level 3:
    - Run code
    - Read references
    - Call MCP tools
    - Fetch data
- Execution happens **outside the prompt**, results come back in.