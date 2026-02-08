---
name: email-sender
description: Send emails using Resend API with support for general messages and specialized budget alerts
---

# Email Sender Skill

You are an agent operating in an MCP environment with access to email sending tools.
Your responsibility is to send emails using the provided tools when requested.

You MUST use the available email tools when the user asks to send emails.
Do not simulate or pretend to send emails - always call the actual tool.

---

## Purpose

The `email-sender` skill provides email sending capabilities through the Resend API. It supports both general-purpose email sending and specialized budget alert notifications with automatic formatting.

## Core Capabilities

1. **General Email Sending**
   - Send HTML emails to single or multiple recipients
   - Support for CC and BCC
   - Configurable sender address
   - Full HTML content support

2. **Budget Alert Notifications**
   - Automated budget threshold alerts
   - Severity-based formatting (INFO, WARNING, CRITICAL, EXCEEDED)
   - Pre-formatted HTML templates with color-coded alerts
   - Percentage calculation and visual presentation

## Available Tools

### send_email

Send a general-purpose email with full customization.

**Use when:**
- The user asks to send an email
- Notifications need to be delivered
- Reports or summaries should be emailed
- Any email communication is requested

**Parameters:**
- `to` (required): Recipient email address(es). Can be a single string or list of strings.
  - Example: `"user@example.com"` or `["user1@example.com", "user2@example.com"]`
- `subject` (required): Email subject line (1-998 characters per RFC 2822)
- `html` (required): Email body as HTML string
- `from_email` (optional): Sender email address. Falls back to `EMAIL_FROM` environment variable if not provided.
- `provider` (optional): Email provider to use. Default is `"auto"` (tries Resend).
  - Options: `"auto"`, `"resend"`
- `cc` (optional): CC recipient(s). Single string or list of strings.
- `bcc` (optional): BCC recipient(s). Single string or list of strings.

**Returns:**
```python
{
    "success": True,
    "provider": "resend",
    "id": "message_id_here",
    "to": ["recipient@example.com"],
    "subject": "Subject here"
}
```

**Error Response:**
```python
{
    "error": "Error message here",
    "help": "Helpful guidance (optional)"
}
```

**Rules:**
- Always call this tool when the user requests to send an email
- Do not fabricate or simulate email sending
- Check the response for errors before confirming success to the user
- If sender email is not provided, ensure EMAIL_FROM environment variable is set

---

### send_budget_alert_email

Send a pre-formatted budget alert notification with automatic severity calculation and styling.

**Parameters:**
- `to` (required): Recipient email address(es)
- `budget_name` (required): Name of the budget (e.g., "Marketing Q1", "Development Budget")
- `current_spend` (required): Current spending amount (float)
- `budget_limit` (required): Budget limit amount (float)
- `currency` (optional): Currency code. Default: `"USD"`
- `from_email` (optional): Sender email address. Falls back to `EMAIL_FROM` environment variable.
- `provider` (optional): Email provider. Default: `"auto"`
- `cc` (optional): CC recipient(s)
- `bcc` (optional): BCC recipient(s)

**Automatic Severity Calculation:**
- **EXCEEDED** (≥100%): Red color (#dc2626) - Budget has been exceeded
- **CRITICAL** (≥90%): Orange color (#ea580c) - Budget is critically high
- **WARNING** (≥75%): Yellow color (#ca8a04) - Budget usage approaching limit
- **INFO** (<75%): Blue color (#2563eb) - Budget usage is normal

**Generated Email Format:**
```
Subject: [SEVERITY] Budget Alert: {budget_name} at {percentage}%

Body:
- Budget name
- Current spend with currency
- Budget limit with currency
- Usage percentage (color-coded)
```

**Use when:**
- Budget thresholds are reached
- Automated financial monitoring
- Expense tracking alerts
- Cost management notifications

**Rules:**
- Always call this tool when the user requests a budget alert email
- Let the tool calculate severity and format the email automatically
- Do not manually create budget alert HTML - use this specialized tool

---

## Mandatory Rules

⚠️ **CRITICAL - You MUST follow these rules:**

1. **Always use tools for email operations**
   - When the user asks to send an email, call `send_email` or `send_budget_alert_email`
   - Never simulate or pretend to send emails without calling the tool
   - Never tell the user an email was sent without actually calling the tool

2. **Verify required information before calling**
   - Check if `to`, `subject`, and `html` are provided (for send_email)
   - If missing, ask the user for the required information
   - Remind user about EMAIL_FROM or from_email if not set

3. **Always check tool response**
   - After calling the tool, check for `error` key in response
   - Only confirm success to the user if no error exists
   - If error exists, explain the error and help resolve it

4. **Handle errors gracefully**
   - If credentials are missing, explain how to set RESEND_API_KEY and EMAIL_FROM
   - If validation fails, explain what's wrong and ask for corrections
   - Never leave the user unsure whether the email was sent

---

## Configuration Requirements

### Environment Variables

**Required:**
- `RESEND_API_KEY`: Your Resend API key (get one at https://resend.com/api-keys)
- `EMAIL_FROM`: Default sender email address (must be verified in Resend)

**Example:**
```bash
export RESEND_API_KEY="re_123456789"
export EMAIL_FROM="notifications@yourdomain.com"
```

### Sender Email Verification

Before sending emails, you must verify your sender domain or email address in Resend:
1. Go to https://resend.com/domains
2. Add and verify your domain
3. Use an email address from that verified domain

---

## Usage Rules

### CRITICAL: Required Information

1. **Always check for sender address:**
   - If `from_email` is not provided, ensure `EMAIL_FROM` environment variable is set
   - If neither is available, the tool will return an error

2. **Validate recipients:**
   - At least one recipient email is required
   - Empty strings are filtered out automatically

3. **Subject validation:**
   - Must be between 1-998 characters
   - Cannot be empty

4. **HTML content:**
   - Required for `send_email`
   - Can be simple text wrapped in HTML tags: `<p>Your message</p>`

### Error Handling

**Always check the response for the `error` key before considering the email sent:**

```python
result = send_email(...)
if "error" in result:
    # Handle error - email was NOT sent
    print(f"Error: {result['error']}")
    if "help" in result:
        print(f"Help: {result['help']}")
else:
    # Success - email was sent
    print(f"Email sent successfully: {result['id']}")
```

**Common Errors:**
- `"Sender email is required"` - Set `from_email` parameter or `EMAIL_FROM` env variable
- `"At least one recipient email is required"` - Provide valid recipient email(s)
- `"Subject must be 1-998 characters"` - Check subject length
- `"Email body (html) is required"` - Provide HTML content
- `"Resend credentials not configured"` - Set `RESEND_API_KEY` environment variable
- `"Resend API error: ..."` - API-specific error from Resend service

---

## Usage Strategies

### Strategy 1: Simple Notification Email

Use for basic text notifications:

```python
send_email(
    to="user@example.com",
    subject="Your Order Has Shipped",
    html="<p>Your order #12345 has been shipped and will arrive in 3-5 business days.</p>"
)
```

### Strategy 2: HTML-Formatted Email

Use for rich content with formatting:

```python
send_email(
    to=["user1@example.com", "user2@example.com"],
    subject="Weekly Report",
    html="""
    <div style="font-family: sans-serif;">
        <h1>Weekly Report</h1>
        <p>Here are the highlights for this week:</p>
        <ul>
            <li>Sales: $50,000</li>
            <li>New Customers: 120</li>
            <li>Satisfaction: 95%</li>
        </ul>
    </div>
    """,
    from_email="reports@company.com"
)
```

### Strategy 3: Email with CC/BCC

Use for keeping others informed:

```python
send_email(
    to="recipient@example.com",
    subject="Project Update",
    html="<p>The project is on track for completion next week.</p>",
    cc="manager@example.com",
    bcc=["stakeholder1@example.com", "stakeholder2@example.com"]
)
```

### Strategy 4: Budget Alert

Use for automated budget monitoring:

```python
send_budget_alert_email(
    to="finance@company.com",
    budget_name="Marketing Q1 2026",
    current_spend=92000.50,
    budget_limit=100000.00,
    currency="USD",
    cc="cfo@company.com"
)
```

This will automatically:
- Calculate percentage: 92%
- Assign severity: CRITICAL (orange)
- Format HTML email with color-coded alert
- Send with subject: `[CRITICAL] Budget Alert: Marketing Q1 2026 at 92%`

---

## Best Practices

### 1. Email Content
- **Use HTML tags**: Even for plain text, wrap in `<p>` tags
- **Keep it concise**: Shorter emails have better engagement
- **Test HTML**: Preview complex HTML before sending
- **Avoid spam triggers**: Don't use excessive caps, exclamation marks, or spam keywords

### 2. Recipient Management
- **Validate emails**: Ensure email addresses are valid before sending
- **Use BCC for bulk**: When sending to many recipients, use BCC to protect privacy
- **Respect unsubscribes**: Maintain an unsubscribe list and honor requests

### 3. Error Handling
- **Always check for errors**: Don't assume emails sent successfully
- **Log failures**: Keep track of failed sends for troubleshooting
- **Retry logic**: For critical emails, implement retry with exponential backoff
- **Alert on failure**: Notify admins when important emails fail

### 4. Security
- **Protect API keys**: Never hardcode `RESEND_API_KEY` in code
- **Verify sender domains**: Only send from verified domains
- **Validate input**: Sanitize any user input in email content
- **Rate limiting**: Don't send too many emails rapidly to avoid throttling

### 5. Budget Alerts
- **Set appropriate thresholds**: Configure alerts at 75%, 90%, and 100%
- **Multiple recipients**: Send to multiple stakeholders for critical budgets
- **Regular monitoring**: Run checks daily or weekly
- **Include context**: Use descriptive budget names

---

## Examples

### Example 1: User Welcome Email

```python
result = send_email(
    to="newuser@example.com",
    subject="Welcome to Our Platform!",
    html="""
    <div style="font-family: Arial, sans-serif; max-width: 600px;">
        <h1>Welcome!</h1>
        <p>Thank you for joining our platform. We're excited to have you!</p>
        <p>To get started, please verify your email address by clicking the link below:</p>
        <a href="https://example.com/verify?token=abc123"
           style="background-color: #4CAF50; color: white; padding: 10px 20px;
                  text-decoration: none; border-radius: 5px; display: inline-block;">
            Verify Email
        </a>
    </div>
    """
)

if "error" in result:
    print(f"Failed to send welcome email: {result['error']}")
else:
    print(f"Welcome email sent: {result['id']}")
```

### Example 2: Multiple Budget Alerts

```python
budgets = [
    {"name": "Marketing", "spend": 85000, "limit": 100000},
    {"name": "Engineering", "spend": 120000, "limit": 120000},
    {"name": "Operations", "spend": 45000, "limit": 80000},
]

for budget in budgets:
    percentage = (budget["spend"] / budget["limit"]) * 100

    # Only send alert if threshold exceeded
    if percentage >= 75:
        result = send_budget_alert_email(
            to="finance@company.com",
            budget_name=budget["name"],
            current_spend=budget["spend"],
            budget_limit=budget["limit"],
            currency="USD"
        )

        if "error" not in result:
            print(f"Alert sent for {budget['name']}: {percentage:.0f}%")
```

### Example 3: Error Recovery with Retry

```python
import time

def send_email_with_retry(to, subject, html, max_retries=3):
    """Send email with exponential backoff retry."""
    for attempt in range(max_retries):
        result = send_email(to=to, subject=subject, html=html)

        if "error" not in result:
            return result  # Success

        if attempt < max_retries - 1:
            wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
            print(f"Retry {attempt + 1}/{max_retries} after {wait_time}s...")
            time.sleep(wait_time)

    return result  # Final failure

# Usage
result = send_email_with_retry(
    to="user@example.com",
    subject="Important Notification",
    html="<p>This is a critical message.</p>"
)
```

### Example 4: Team Notification

```python
send_email(
    to="team-lead@example.com",
    subject="Deployment Complete",
    html="""
    <div style="font-family: monospace;">
        <h2>✅ Deployment Successful</h2>
        <p><strong>Environment:</strong> Production</p>
        <p><strong>Version:</strong> v2.5.0</p>
        <p><strong>Deployed at:</strong> 2026-02-07 14:30 UTC</p>
        <p><strong>Duration:</strong> 3 minutes</p>
        <hr>
        <p>All health checks passed. System is operational.</p>
    </div>
    """,
    cc=["devops@example.com", "engineering@example.com"]
)
```

---

## Troubleshooting

### Problem: "Sender email is required"
**Solution:** Set the `EMAIL_FROM` environment variable or pass `from_email` parameter:
```bash
export EMAIL_FROM="noreply@yourdomain.com"
```

### Problem: "Resend credentials not configured"
**Solution:** Set the `RESEND_API_KEY` environment variable:
```bash
export RESEND_API_KEY="re_your_api_key_here"
```
Get your API key at: https://resend.com/api-keys

### Problem: "Resend API error: Domain not verified"
**Solution:** Verify your domain in Resend dashboard:
1. Go to https://resend.com/domains
2. Add your domain
3. Add DNS records (SPF, DKIM)
4. Wait for verification
5. Use an email address from that domain as sender

### Problem: Email not received
**Check:**
1. Spam/junk folder
2. Email address is valid
3. Sender domain is verified
4. Check Resend dashboard for delivery logs
5. Ensure `result["success"]` is `True`

### Problem: HTML rendering issues
**Solution:**
- Test email in Resend preview
- Use inline CSS styles instead of external stylesheets
- Avoid complex layouts (use tables for structure)
- Keep HTML simple and email-client compatible

---

## Integration with Other Skills

- **travel-briefing**: Send travel itinerary confirmations
- **weather-intelligence**: Email weather alerts and forecasts
- **web-research**: Email research reports and summaries

---

## Technical Details

### Protocol
- Uses **HTTPS REST API** (not SMTP) for reliable, stateless communication
- Resend handles SMTP delivery internally
- No connection pooling or retry logic needed on client side

### Recipient Normalization
- Single strings are automatically converted to lists
- Empty strings are filtered out
- Both `"user@example.com"` and `["user@example.com"]` work correctly

### HTML Content
- Full HTML support with inline CSS
- No script tags (removed by email clients)
- Images should use absolute URLs
- Consider email client compatibility (Outlook, Gmail, etc.)

### Rate Limits
- Resend free tier: 100 emails/day
- Resend paid plans: Higher limits based on plan
- Implement exponential backoff for retries
- Monitor Resend dashboard for usage

---

## Ethical Guidelines

1. **Consent**: Only send emails to users who opted in
2. **Unsubscribe**: Always provide an unsubscribe mechanism
3. **Privacy**: Don't share recipient emails via CC (use BCC)
4. **Content**: Don't send spam, phishing, or malicious content
5. **Frequency**: Respect user preferences on email frequency
6. **Compliance**: Follow CAN-SPAM, GDPR, and other regulations

---

End of email-sender skill.
