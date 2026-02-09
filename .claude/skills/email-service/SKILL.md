---
name: email-service
description: Send, read, and manage Gmail emails using the Gmail API after prior OAuth authorization.
---

# Email Service (Gmail API)

This skill provides Gmail email functionality using the **Google Gmail API**.

⚠️ **IMPORTANT**  
This skill **requires prior OAuth authorization** and cannot perform authorization by itself.

---

## 🔐 Authorization (Required)

This skill depends on Gmail OAuth credentials that must be generated **outside of the MCP runtime**.

### One-time authorization step (human required)

Before using this skill, you MUST run:

```bash
python authorization/authorize_gmail.py
```

## What this skill can do

### 1️⃣ Read an email
Retrieve the full contents of an email, including headers and body text.

**Typical use cases**
- “Read the latest email from my manager”
- “Open the email with subject ‘Invoice’”

**Tool involved**
- `gmail_read_email`

**Output**
- sender
- recipient
- subject
- date
- plain text body

---

### 2️⃣ Search emails
Search the inbox using keyword-based queries.

**Typical use cases**
- “Find emails about onboarding”
- “Search for unread messages from last week”

**Tool involved**
- `gmail_search_email`

**Notes**
- Supports provider-native search syntax (e.g. Gmail-style queries)

---

### 3️⃣ Send an email
Send a new email message.

**Typical use cases**
- “Email Alice and tell her the meeting is postponed”
- “Send a confirmation email to the client”

**Tool involved**
- `gmail_send_email`

**Requirements**
- At least one recipient
- Subject and body content

---

### 4️⃣ Apply labels to emails
Modify an email by attaching labels (or categories).

**Typical use cases**
- “Label this email as Important”
- “Tag the invoice email as Finance”

**Tool involved**
- `gmail_apply_label`

**Notes**
- Label IDs must already exist in the email provider

---

## When the agent should use this skill

Use this skill whenever the user intent involves:
- reading or summarizing emails
- searching inbox history
- sending messages
- organizing emails via labels

The agent may combine multiple actions into a single workflow, for example:
1. Search emails
2. Read the most relevant result
3. Apply a label
4. Send a reply

---

## Example prompts

- “Check if I received any emails about the interview.”
- “Read the latest email from Amazon and summarize it.”
- “Send an email to Bob saying I’ll reply tomorrow.”
- “Find emails about receipts and label them Finance.”

---

## Boundaries & safety notes

- This skill only operates on **authorized email accounts**
- It does not guess recipients or fabricate messages
- If required information is missing, the agent should ask the user to clarify
- Labels are applied only when explicitly requested

---

## Implementation notes (for developers)

This skill is backed by the following **MCP tools**:

- `gmail_read_email`
- `gmail_search_email`
- `gmail_send_email`
- `gmail_apply_label`

Each tool is exposed independently through MCP.

