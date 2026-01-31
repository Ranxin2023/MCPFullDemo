# Agent Skills
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

