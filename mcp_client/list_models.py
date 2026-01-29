from anthropic import Anthropic
import os
from dotenv import load_dotenv

# Load your API key
load_dotenv()
client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# List models
models = client.models.list()

print("\nAvailable Anthropic models:\n")
for m in models.data:
    print("-", m.id)
