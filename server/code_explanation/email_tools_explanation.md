# Explanation of `email_tools.py`
## 1. Purpose of `email_tool.py`
- This file defines email-sending tools that can be exposed to an MCP server and safely called by an LLM agent.
- Key goals:
    - Provide **email sending as an MCP tool**
    - Support **multiple providers** (currently Resend)
    - Handle **credentials safely**
    - Validate inputs (to / subject / body)

## 2. Imports and setup
```python
import os
from typing import TYPE_CHECKING, Literal

import resend
from fastmcp import FastMCP

```
### What’s happening here
- `resend`
    - Official SDK for the Resend email service.
- `FastMCP`
    - Used to register tools (`@mcp.tool()`).
- `Literal`
    - Used to restrict provider choices (`"auto"` or `"resend"`).

## 3. `register_tools(...)`
```python
def register_tools(
    mcp: FastMCP,
    credentials: CredentialStoreAdapter | None = None,
) -> None:

```
- This function **registers all email-related MCP tools** onto an MCP server.

## 4. Low-level provider implementation: `_send_via_resend`
```python
def _send_via_resend(...)

```
- This is a **provider-specific adapter**.
- **Responsibilities**
    - Configure API key
    - Build Resend payload
    - Call `resend.Emails.send`
    - Normalize success & error responses
## 5. Credential resolution: `_get_credentials`
```python
def _get_credentials() -> dict:

```
- **Credential priority**:
1. **Injected credential store** (preferred, agent-safe)
2. **Environment variables** (fallback) 

```python
return {
    "resend_api_key": os.getenv("RESEND_API_KEY"),
}

```

- This design allows:
    - Local dev (`.env`)
    - Production secret managers
    - Agent-aware credential validation

## 6. Sender & recipient helpers
### `_resolve_from_email`
```python
from_email > EMAIL_FROM env var

``` 
- Prevents:
    - sending emails without a sender
    - hard-coding sender addresses
### `_normalize_recipients`
- Why this exists:
    - MCP schemas allow both
    - Providers always want a list
    - Empty strings are filtered out
- This makes the tool **LLM-safe**, even with messy input.

## 7. Core logic: `_send_email_impl`
- This is the heart of the file.
```python
def _send_email_impl(...)

```
### Step-by-step flow
1. Resolve sender
2. Normalize recipients
3. Validate:
- at least one recipient
- subject length (RFC 2822)
- HTML body exists
4. Load credentials
5. Choose provider:
- explicit (`"resend"`)
- automatic fallback (`"auto"`)
## 8. MCP tool: `send_email`
```python
@mcp.tool()
def send_email(...)

```
- This exposes **general email sending** to the agent.
### Agent-facing capabilities
- Send transactional emails
- Notifications
- Reports
- Custom HTML emails
### The docstring is critical — it tells the LLM:
- when to use it
- what arguments mean
- what errors look like

## 9. MCP tool: `send_budget_alert_email`
```python
@mcp.tool()
def send_budget_alert_email(...)
```
- This is a **high-level semantic tool**, not just a wrapper.
### What it does
- Computes budget usage %
- Assigns severity:
    - INFO
    - WARNING
    - CRITICAL
    - EXCEEDED
- Generates styled HTML automatically
- Sends the email via `_send_email_impl`
- This is a perfect example of an “agent skill”:
    - one intent → formatting → logic → tool execution

## 10. Why this file is well-designed
### Agent-friendly
- Clear schemas
- Defensive validation
- Deterministic outputs
### MCP-correct
- Uses `@mcp.tool()`
- No side effects at import time
- Tools registered explicitly

## Resend Package
### 1. Protocol Resend uses
- **Primary protocol**:
    - **HTTPS (REST API over HTTP/1.1 or HTTP/2)**
- When you call:
```python
resend.Emails.send({...})
```
- what actually happens is:
```pgsql
POST https://api.resend.com/emails
Authorization: Bearer re_xxx
Content-Type: application/json

```
- You are sending **JSON over HTTPS**.
    - No SMTP session.
    - No mail server handshake.
    - No TCP-level mail protocol.
### 2. What protocol Resend does not expose to you
| **Protocol** | **Used by you?**| **Used internally by Resend?** |
| ------------ | --------------- | ------------------------------ |
| SMTP         | ❌ No          | ✅ Yes (behind the scenes)     |
| REST / HTTPS | ✅ Yes         | ✅ Yes                         |
| Webhooks     | ⚠️ Optional    | ✅                             |
| gRPC         | ❌             | ❌                             |

### 3. Why Resend chose HTTPS instead of SMTP
#### **SMTP is bad for modern apps & agents**
- SMTP requires:
    - stateful connections
    - line-based commands
    - fragile error codes
    - retry logic on the client side
- LLMs and agents are **terrible** at SMTP.
#### HTTPS is ideal for agents
- HTTPS gives you:
    - stateless requests
    - clear error responses
    - retries handled by the service
    - easy auth with API keys
    - structured JSON
- That’s why Resend is such a good fit for MCP + agents.

### 4. What happens after HTTPS inside Resend
- Even though you don’t use SMTP, Resend still does — internally.
```java
Your app (HTTPS)
   ↓
Resend API
   ↓
Resend mail pipeline
   ↓
SMTP → Gmail / Outlook / Yahoo

```
- So SMTP still exists, just **not your problem anymore**.

### 5. How this shows up in your `email_tool.py`
- Your tool is built around this assumption:
    ```python
    _send_via_resend(api_key, to, subject, html, ...)

    ```
    - No connection pooling
    - No SMTP retries
    - No mail queue logic
- Just:
    ```bash
    validate → POST → done

    ```
- That’s why your tool is clean and agent-safe.
### 6. Protocol comparison (mental cheat sheet)
| **Service**      | **Client-facing protocol**|
| ---------------- | ------------------------- |
| SMTP server      | SMTP                      |
| Amazon SES (raw) | SMTP + REST               |
| SendGrid         | REST                      |
| **Resend**       | **REST over HTTPS only**  |

