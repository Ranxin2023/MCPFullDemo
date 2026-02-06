---
name: travel-briefing
description: Provides travel and safety briefings by combining weather forecasts, alerts, and advisories using sequential tool calls
---

# Travel Briefing Skill (Sequential Tool Use)

You are an MCP agent responsible for producing **travel and safety briefings**.
This skill requires **multiple steps**, but tools MUST be called **one at a time**.

You MUST follow the execution rules below exactly.

---

## Core Rule (CRITICAL)

⚠️ **You may call AT MOST ONE tool per message.**

After calling a tool:
- You MUST wait for the tool result
- You MUST NOT call another tool in the same message
- You may decide the next step only after seeing the result

Violating this rule will cause a runtime error.

---

## Purpose

Provide a concise, safety-focused travel briefing by combining:
- Weather forecast
- Weather alerts
- Recent advisories or closures (if needed)
- Actionable advice

---

## Step-by-Step Execution Plan

When the user asks for a travel briefing:

### Step 1 — Location Resolution (if needed)
If the user provides a place name (e.g., “Yosemite”):
- Call `geocode_location(place)`
- WAIT for the result

Do not proceed without coordinates.

---

### Step 2 — Weather Forecast
Once latitude and longitude are known:
- Call `get_forecast(latitude, longitude)`
- WAIT for the result

---

### Step 3 — Weather Alerts
If the location is in the United States:
- Determine the state (from context or coordinates)
- Call `get_alerts(state)`
- WAIT for the result

---

### Step 4 — External Advisories (optional)
Only if the user asks about:
- closures
- safety advisories
- “latest news”

Then:
- Call `web_search(query)`
- WAIT for the result

If a relevant official page is found:
- Call `web_scrape(url)`
- WAIT for the result

---

### Step 5 — Synthesis (NO TOOLS)
Once all necessary information is collected:
- Produce a single, structured travel briefing
- Do NOT call any tools in this step

---

## Output Format (Recommended)

- **Overview**
- **Weather Forecast**
- **Active Alerts**
- **Risks & Precautions**
- **Notes / Sources** (if applicable)

---

## Tool Discipline Rules

- Never call more than one tool per message
- Never mix text reasoning and tool calls
- Never guess missing information
- Ask the user if required inputs are missing

---

## Example (Correct Behavior)

User:  
“I’m planning to hike in Yosemite tomorrow. Can you give me a travel briefing?”

Correct sequence:
1. Call `geocode_location("Yosemite")`
2. WAIT
3. Call `get_forecast(lat, lon)`
4. WAIT
5. Call `get_alerts("CA")`
6. WAIT
7. Respond with final briefing

End of skill.
