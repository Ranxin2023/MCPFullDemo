from dotenv import load_dotenv
from pathlib import Path
import anthropic
import os
# Make sure you update to the newest anthropic package
# python -m pip install -U anthropic
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(env_path)

api_key = os.getenv("ANTHROPIC_API_KEY")
if not api_key:
    raise RuntimeError(f"ANTHROPIC_API_KEY not found. Loaded env from: {env_path}")

client = anthropic.Anthropic(api_key=api_key)

skills = client.beta.skills.list(
    source="anthropic",
    betas=["skills-2025-10-02"],
)

print("✅ skills.list OK. count =", len(skills.data))
print("first few:", [s.id for s in skills.data[:10]])
# List Anthropic-managed Skills
response = client.beta.messages.create(
    model="claude-sonnet-4-5-20250929",
    max_tokens=4096,
    betas=["code-execution-2025-08-25", "skills-2025-10-02"],
    container={
        "skills": [
            {
                "type": "anthropic",
                "skill_id": "docx",
                "version": "latest"
            }
        ]
    },
    messages=[{
        "role": "user",
        "content": "Write a 2-page report on the benefits of renewable energy"
    }],
    tools=[{
        "type": "code_execution_20250825",
        "name": "code_execution"
    }]
)

print(f"response from beta is:\n {response}")