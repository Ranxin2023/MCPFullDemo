"""
Delete the 4 working custom skills, then re-upload them
This will reorder skills so the old "Weather" ends up last
"""

from pathlib import Path
from anthropic import Anthropic
from anthropic.lib import files_from_dir
from dotenv import load_dotenv
import os
import sys
import time

# Fix Windows encoding
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Load environment
env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(env_path)

api_key = os.getenv("ANTHROPIC_API_KEY")
client = Anthropic(api_key=api_key)

print("=" * 60)
print("REORDER SKILLS STRATEGY")
print("=" * 60)

# Step 1: List current skills
print("\n📋 Step 1: Current skills")
skills = client.beta.skills.list(betas=["skills-2025-10-02"])

print(f"Total: {len(skills.data)} skills")
for i, s in enumerate(skills.data, 1):
    icon = "🏢" if s.source == "anthropic" else "⚙️"
    print(f"  {i}. {icon} {s.display_title} ({s.id})")

# Skills to delete (the 4 good ones)
skills_to_delete = [
    "Web Scrapy",
    "Weather Intelligence",
    "Web Research",
    "Travel Briefing"
]

# Step 2: Delete the 4 working skills
print(f"\n🗑️  Step 2: Deleting working skills to reorder...")
deleted_ids = []

for skill in skills.data:
    if skill.display_title in skills_to_delete:
        print(f"  Deleting {skill.display_title}...", end=" ")
        try:
            client.beta.skills.delete(
                skill_id=skill.id,
                betas=["skills-2025-10-02"]
            )
            deleted_ids.append(skill.id)
            print("✅")
            time.sleep(0.5)  # Rate limiting
        except Exception as e:
            print(f"❌ {e}")

print(f"\n✅ Deleted {len(deleted_ids)} skills")

# Step 3: Verify intermediate state
print(f"\n📋 Step 3: Intermediate state (should be 5 skills)")
skills_mid = client.beta.skills.list(betas=["skills-2025-10-02"])
print(f"Total: {len(skills_mid.data)} skills")
for i, s in enumerate(skills_mid.data, 1):
    icon = "🏢" if s.source == "anthropic" else "⚙️"
    print(f"  {i}. {icon} {s.display_title}")

# Step 4: Re-upload the 4 skills from .claude/skills
print(f"\n📤 Step 4: Re-uploading skills...")

skills_dir = Path(".claude/skills")
uploaded_count = 0

if skills_dir.exists():
    for skill_folder in sorted(skills_dir.iterdir()):
        if skill_folder.is_dir() and (skill_folder / "SKILL.md").exists():
            display_title = skill_folder.name.replace('-', ' ').title()

            print(f"  Uploading {display_title}...", end=" ")
            try:
                skill = client.beta.skills.create(
                    display_title=display_title,
                    files=files_from_dir(str(skill_folder)),
                    betas=["skills-2025-10-02"]
                )
                print(f"✅ ({skill.id})")
                uploaded_count += 1
                time.sleep(0.5)  # Rate limiting
            except Exception as e:
                error_str = str(e)
                if "reuse an existing display_title" in error_str:
                    print(f"⏭️  (already exists)")
                else:
                    print(f"❌ {e}")

print(f"\n✅ Uploaded {uploaded_count} skills")

# Step 5: Final verification
print(f"\n{'='*60}")
print("FINAL RESULT")
print(f"{'='*60}")

final_skills = client.beta.skills.list(betas=["skills-2025-10-02"])

print(f"\n📋 Skills in order (first 8 will be used):\n")
for i, skill in enumerate(final_skills.data, 1):
    icon = "🏢" if skill.source == "anthropic" else "⚙️"
    used = "✅" if i <= 8 else "❌"

    # Highlight the old Weather skill
    if skill.display_title == "Weather":
        marker = " ← OLD (should be at position 9)"
    else:
        marker = ""

    print(f"  {i}. {used} {icon} {skill.display_title}{marker}")

print(f"\n{'='*60}")

# Check if it worked
custom_skills = [s for s in final_skills.data if s.source == "custom"]
weather_position = None

for i, skill in enumerate(final_skills.data, 1):
    if skill.display_title == "Weather":
        weather_position = i
        break

if weather_position == 9:
    print("🎉 SUCCESS! The old 'Weather' skill is now at position 9 (excluded)")
elif weather_position and weather_position > 8:
    print(f"✅ SUCCESS! The old 'Weather' skill is at position {weather_position} (excluded)")
elif weather_position and weather_position <= 8:
    print(f"⚠️  The 'Weather' skill is still at position {weather_position} (active)")
    print("   But all your 4 desired skills should still be in the first 8")
else:
    print("✅ The 'Weather' skill may have been deleted!")

if len(final_skills.data) <= 8:
    print(f"\n✅ Perfect! You now have {len(final_skills.data)} skills (within limit)")
else:
    print(f"\n📊 You have {len(final_skills.data)} skills. First 8 will be used.")
