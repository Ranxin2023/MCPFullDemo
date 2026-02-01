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
# List Anthropic-managed Skills
skills = client.beta.skills.list(
    source="anthropic",
    betas=["skills-2025-10-02"]
)

for skill in skills.data:
    print(f"{skill.id}: {skill.display_title}")