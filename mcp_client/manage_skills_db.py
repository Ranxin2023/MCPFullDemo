"""
Command-line utility for managing the skills database.

Usage:
    python manage_skills_db.py list              # List all skills
    python manage_skills_db.py stats             # Show database statistics
    python manage_skills_db.py add <name> <title> <path>  # Add a skill
    python manage_skills_db.py delete <name>     # Delete a skill
    python manage_skills_db.py sync              # Sync local skills from .claude/skills
"""

import sys
from pathlib import Path
from skills_db import SkillsDatabase
from client_streamlit import MCPClient, AsyncLoopThread


def list_skills(db: SkillsDatabase, filter_type: str = None):
    """List all skills or filter by type."""
    if filter_type:
        skills = db.get_all_skills(source=filter_type)
        print(f"\n{'='*60}")
        print(f"{filter_type.upper()} SKILLS")
        print(f"{'='*60}")
    else:
        skills = db.get_all_skills()
        print(f"\n{'='*60}")
        print("ALL SKILLS")
        print(f"{'='*60}")

    if not skills:
        print("No skills found.")
        return

    for skill in skills:
        status = "✅ Uploaded" if skill['is_uploaded'] else "📁 Local"
        print(f"\n{skill['display_title']} ({skill['name']}) - {status}")
        print(f"  Source: {skill['source']}")
        if skill['description']:
            print(f"  Description: {skill['description']}")
        if skill['local_path']:
            print(f"  Path: {skill['local_path']}")
        if skill['skill_id']:
            print(f"  Skill ID: {skill['skill_id']}")
        if skill['uploaded_at']:
            print(f"  Uploaded: {skill['uploaded_at']}")


def show_stats(db: SkillsDatabase):
    """Show database statistics."""
    stats = db.get_stats()

    print(f"\n{'='*60}")
    print("DATABASE STATISTICS")
    print(f"{'='*60}")
    print(f"Total Skills:      {stats['total']}")
    print(f"Uploaded:          {stats['uploaded']}")
    print(f"Local Only:        {stats['total'] - stats['uploaded']}")
    print(f"\nBy Source:")
    print(f"  Anthropic:       {stats['anthropic']}")
    print(f"  Custom:          {stats['custom']}")
    print(f"  Local:           {stats['local']}")


def add_skill(db: SkillsDatabase, name: str, display_title: str, path: str, description: str = ""):
    """Add a skill to the database."""
    try:
        skill_id = db.add_skill(
            name=name,
            display_title=display_title,
            description=description,
            local_path=path,
            source='local'
        )
        print(f"✅ Successfully added skill: {display_title} (ID: {skill_id})")
    except Exception as e:
        print(f"❌ Failed to add skill: {e}")


def delete_skill(db: SkillsDatabase, name: str):
    """Delete a skill from the database."""
    try:
        if db.delete_skill(name):
            print(f"✅ Successfully deleted skill: {name}")
        else:
            print(f"❌ Skill not found: {name}")
    except Exception as e:
        print(f"❌ Failed to delete skill: {e}")


def sync_local_skills(db: SkillsDatabase, base_path: str = "./.claude/skills"):
    """Sync local skills from filesystem."""
    try:
        # Create a temporary client to use find_local_skills
        loop_thread = AsyncLoopThread()
        loop_thread.start()
        client = MCPClient(loop_thread)

        print(f"Scanning {base_path}...")
        local_skills = client.find_local_skills(base_path)

        if not local_skills:
            print("No local skills found.")
            return

        print(f"Found {len(local_skills)} local skills. Syncing to database...")
        stats = db.sync_local_skills(local_skills)

        print(f"\n✅ Sync complete:")
        print(f"  Added:   {stats['added']}")
        print(f"  Updated: {stats['updated']}")
        print(f"  Skipped: {stats['skipped']}")

        loop_thread.stop()

    except Exception as e:
        print(f"❌ Failed to sync skills: {e}")


def main():
    """Main CLI entry point."""
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    command = sys.argv[1].lower()
    db = SkillsDatabase()

    if command == "list":
        filter_type = sys.argv[2] if len(sys.argv) > 2 else None
        list_skills(db, filter_type)

    elif command == "stats":
        show_stats(db)

    elif command == "add":
        if len(sys.argv) < 5:
            print("Usage: manage_skills_db.py add <name> <title> <path> [description]")
            sys.exit(1)
        name = sys.argv[2]
        title = sys.argv[3]
        path = sys.argv[4]
        desc = sys.argv[5] if len(sys.argv) > 5 else ""
        add_skill(db, name, title, path, desc)

    elif command == "delete":
        if len(sys.argv) < 3:
            print("Usage: manage_skills_db.py delete <name>")
            sys.exit(1)
        name = sys.argv[2]
        delete_skill(db, name)

    elif command == "sync":
        base_path = sys.argv[2] if len(sys.argv) > 2 else "./.claude/skills"
        sync_local_skills(db, base_path)

    else:
        print(f"Unknown command: {command}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
