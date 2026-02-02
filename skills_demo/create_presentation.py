from dotenv import load_dotenv
from pathlib import Path
import anthropic
import json
import os
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(env_path)

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
if not ANTHROPIC_API_KEY:
    raise RuntimeError(f"ANTHROPIC_API_KEY not found. Loaded env from: {env_path}")
client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

# Test 1: Basic API call (should work)
try:
    response = client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=1024,
        messages=[{"role": "user", "content": "Hello"}]
    )
    print("✓ Basic API works")
except Exception as e:
    print(f"✗ Basic API failed: {e}")

# Test 2: Code execution only
try:
    response = client.beta.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=1024,
        betas=["code-execution-2025-08-25"],
        messages=[{"role": "user", "content": "Calculate 2+2"}],
        tools=[{"type": "code_execution_20250825", "name": "code_execution"}]
    )
    print("✓ Code execution works")
except Exception as e:
    print(f"✗ Code execution failed: {e}")

# Test 3: Skills API without code execution
try:
    response = client.beta.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=1024,
        betas=["skills-2025-10-02", "files-api-2025-04-14"],
        container=json.dumps({  # Convert dict to JSON string
            "skills": [
                {
                    "type": "anthropic",
                    "skill_id": "pptx",
                    "version": "latest"
                }
            ]
        }),
        messages=[{"role": "user", "content": "Hello"}]
    )
    print("✓ Skills API works")
except Exception as e:
    print(f"✗ Skills API failed: {e}")