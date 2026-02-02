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

response = client.beta.messages.create(
    model="claude-sonnet-4-5-20250929",
    max_tokens=4096,
    betas=["code-execution-2025-08-25", "skills-2025-10-02"],
    container={
        "skills": [
            {
                "type": "anthropic",
                "skill_id": "pdf",
                "version": "latest"
            }
        ]
    },
    messages=[{
        "role": "user",
        "content": "Generate a PDF invoice template"
    }],
    tools=[{
        "type": "code_execution_20250825",
        "name": "code_execution"
    }]
)
print(f"response from model for pdf is\n {response}")
file_ids = []

for block in response.content:
    # check file id exist
    fid = getattr(block, "file_id", None)
    if fid:
        file_ids.append(fid)

print("file_ids:", file_ids)

if not file_ids:
    # print some text so you can see what happened
    texts = []
    for block in response.content:
        if getattr(block, "type", None) == "text":
            texts.append(block.text)
    print("No file_id returned. Text content:\n", "\n".join(texts))
    raise SystemExit(1)

# 3) download the first pdf
file_id = file_ids[0]
pdf_bytes = client.beta.files.download(file_id).read()

out_path = Path(__file__).resolve().parent / "invoice_template.pdf"
out_path.write_bytes(pdf_bytes)
print("✅ Saved:", out_path)

# response = client.beta.messages.create(
#     model="claude-sonnet-4-5-20250929",
#     max_tokens=1024,
#     betas=["skills-2025-10-02", "files-api-2025-04-14"],
#     container={
#         "skills": [
#             {"type": "anthropic", "skill_id": "docx", "version": "latest"}
#         ]
#     },
#     messages=[{
#         "role": "user",
#         "content": "Create a 1-page Word document with a title and 5 bullet points about renewable energy."
#     }],
# )

# print(f"response for generating word......\n {response}")