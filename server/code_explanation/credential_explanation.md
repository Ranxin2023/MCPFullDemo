# Explanation of `credentials.py`
## 1. What problem credentials.py solves
- In MCP projects, different tools may need secrets (API keys, tokens). You want:
    - A **single place** to define which credentials exist
    - A consistent way to **read credentials** (env, `.env`, test overrides)
    - A way to **validate** only the credentials needed by specific tools
    - Nice, actionable error messages when keys are missing
- That’s exactly what CredentialManager provides.

## 2. Key types/classes in the file
### `CredentialError`
- A custom exception for missing required credentials.
    - Raised by `validate_for_tools()`, `validate_for_node_types()`, and `validate_startup()`
    - Makes it easy to try/except and print a clean message