"""
SQLite database for managing MCP agent skills.

This module provides a persistent storage layer for tracking:
- Local skills available for upload
- Uploaded skills and their Anthropic IDs
- Skill metadata and status
"""

import sqlite3
from datetime import datetime
from typing import Optional, List, Dict
from contextlib import contextmanager


class SkillsDatabase:
    """Database manager for agent skills."""

    def __init__(self, db_path: str = "./skills.db"):
        """
        Initialize the skills database.

        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = db_path
        self._init_database()

    @contextmanager
    def _get_connection(self):
        """Context manager for database connections."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Return rows as dictionaries
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_database(self):
        """Create the skills table if it doesn't exist."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS skills (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    display_title TEXT NOT NULL,
                    description TEXT,
                    local_path TEXT,
                    skill_id TEXT,
                    source TEXT DEFAULT 'local',
                    version TEXT DEFAULT 'latest',
                    is_uploaded BOOLEAN DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    uploaded_at TIMESTAMP
                )
            """)

            # Create index on skill_id for faster lookups
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_skill_id
                ON skills(skill_id)
            """)

            # Create index on source for filtering
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_source
                ON skills(source)
            """)

    def add_skill(
        self,
        name: str,
        display_title: str,
        description: str = "",
        local_path: str = "",
        skill_id: Optional[str] = None,
        source: str = "local"
    ) -> int:
        """
        Add a new skill to the database.

        Args:
            name: Skill name (e.g., 'travel-briefing')
            display_title: Display title (e.g., 'Travel Briefing')
            description: Skill description
            local_path: Path to local skill folder
            skill_id: Anthropic skill ID (if already uploaded)
            source: 'local', 'anthropic', or 'custom'

        Returns:
            Database ID of the inserted skill
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            is_uploaded = 1 if skill_id else 0
            uploaded_at = datetime.now().isoformat() if skill_id else None

            cursor.execute("""
                INSERT INTO skills (
                    name, display_title, description, local_path,
                    skill_id, source, is_uploaded, uploaded_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                name, display_title, description, local_path,
                skill_id, source, is_uploaded, uploaded_at
            ))

            return cursor.lastrowid

    def update_skill(
        self,
        name: str,
        **kwargs
    ) -> bool:
        """
        Update an existing skill.

        Args:
            name: Skill name to update
            **kwargs: Fields to update (display_title, description, skill_id, etc.)

        Returns:
            True if skill was updated, False if not found
        """
        allowed_fields = {
            'display_title', 'description', 'local_path',
            'skill_id', 'source', 'version', 'is_uploaded'
        }

        updates = {k: v for k, v in kwargs.items() if k in allowed_fields}

        if not updates:
            return False

        # Add updated_at timestamp
        updates['updated_at'] = datetime.now().isoformat()

        # If skill_id is being set, mark as uploaded
        if 'skill_id' in updates and updates['skill_id']:
            updates['is_uploaded'] = 1
            updates['uploaded_at'] = datetime.now().isoformat()

        with self._get_connection() as conn:
            cursor = conn.cursor()

            set_clause = ', '.join(f"{k} = ?" for k in updates.keys())
            values = list(updates.values()) + [name]

            cursor.execute(f"""
                UPDATE skills
                SET {set_clause}
                WHERE name = ?
            """, values)

            return cursor.rowcount > 0

    def get_skill(self, name: str) -> Optional[Dict]:
        """
        Get a skill by name.

        Args:
            name: Skill name

        Returns:
            Dict with skill data or None if not found
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM skills WHERE name = ?", (name,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_skill_by_id(self, skill_id: str) -> Optional[Dict]:
        """
        Get a skill by Anthropic skill ID.

        Args:
            skill_id: Anthropic skill ID

        Returns:
            Dict with skill data or None if not found
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM skills WHERE skill_id = ?", (skill_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_all_skills(self, source: Optional[str] = None) -> List[Dict]:
        """
        Get all skills, optionally filtered by source.

        Args:
            source: Filter by source ('local', 'anthropic', 'custom')

        Returns:
            List of skill dictionaries
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            if source:
                cursor.execute(
                    "SELECT * FROM skills WHERE source = ? ORDER BY created_at DESC",
                    (source,)
                )
            else:
                cursor.execute("SELECT * FROM skills ORDER BY created_at DESC")

            return [dict(row) for row in cursor.fetchall()]

    def get_uploaded_skills(self) -> List[Dict]:
        """
        Get all skills that have been uploaded to Anthropic.

        Returns:
            List of uploaded skill dictionaries
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM skills
                WHERE is_uploaded = 1
                ORDER BY uploaded_at DESC
            """)
            return [dict(row) for row in cursor.fetchall()]

    def get_local_skills(self) -> List[Dict]:
        """
        Get all local skills that haven't been uploaded yet.

        Returns:
            List of local skill dictionaries
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM skills
                WHERE source = 'local' AND is_uploaded = 0
                ORDER BY created_at DESC
            """)
            return [dict(row) for row in cursor.fetchall()]

    def delete_skill(self, name: str) -> bool:
        """
        Delete a skill by name.

        Args:
            name: Skill name to delete

        Returns:
            True if skill was deleted, False if not found
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM skills WHERE name = ?", (name,))
            return cursor.rowcount > 0

    def delete_skill_by_id(self, skill_id: str) -> bool:
        """
        Delete a skill by Anthropic skill ID.

        Args:
            skill_id: Anthropic skill ID

        Returns:
            True if skill was deleted, False if not found
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM skills WHERE skill_id = ?", (skill_id,))
            return cursor.rowcount > 0

    def mark_as_uploaded(self, name: str, skill_id: str) -> bool:
        """
        Mark a skill as uploaded with its Anthropic skill ID.

        Args:
            name: Skill name
            skill_id: Anthropic skill ID

        Returns:
            True if updated successfully
        """
        return self.update_skill(
            name=name,
            skill_id=skill_id,
            is_uploaded=1
        )

    def sync_local_skills(self, local_skills: List[Dict]) -> Dict[str, int]:
        """
        Sync local skills from filesystem into database.

        Args:
            local_skills: List of skill dicts from find_local_skills()

        Returns:
            Dict with counts: {'added': int, 'updated': int, 'skipped': int}
        """
        stats = {'added': 0, 'updated': 0, 'skipped': 0}

        for skill in local_skills:
            existing = self.get_skill(skill['name'])

            if existing:
                # Update if path or description changed
                if (existing['local_path'] != skill['path'] or
                    existing['description'] != skill.get('description', '')):
                    self.update_skill(
                        name=skill['name'],
                        local_path=skill['path'],
                        description=skill.get('description', ''),
                        display_title=skill['display_title']
                    )
                    stats['updated'] += 1
                else:
                    stats['skipped'] += 1
            else:
                # Add new skill
                self.add_skill(
                    name=skill['name'],
                    display_title=skill['display_title'],
                    description=skill.get('description', ''),
                    local_path=skill['path'],
                    source='local'
                )
                stats['added'] += 1

        return stats

    def sync_uploaded_skills(self, uploaded_skills: List[Dict]) -> Dict[str, int]:
        """
        Sync uploaded skills from Anthropic API into database.

        Args:
            uploaded_skills: List of skill dicts from list_all_skills()

        Returns:
            Dict with counts: {'added': int, 'updated': int, 'skipped': int}
        """
        stats = {'added': 0, 'updated': 0, 'skipped': 0}

        for skill in uploaded_skills:
            existing = self.get_skill_by_id(skill['id'])

            if existing:
                # Update if needed
                if existing['source'] != skill['source']:
                    self.update_skill(
                        name=existing['name'],
                        source=skill['source']
                    )
                    stats['updated'] += 1
                else:
                    stats['skipped'] += 1
            else:
                # Add new skill from Anthropic
                # Use skill_id as name if we don't have a local match
                display_title = skill['display_title']
                name = display_title.lower().replace(' ', '-')

                try:
                    self.add_skill(
                        name=name,
                        display_title=display_title,
                        skill_id=skill['id'],
                        source=skill['source']
                    )
                    stats['added'] += 1
                except sqlite3.IntegrityError:
                    # Name conflict, skip
                    stats['skipped'] += 1

        return stats

    def get_stats(self) -> Dict[str, int]:
        """
        Get statistics about skills in the database.

        Returns:
            Dict with counts for different categories
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            stats = {}

            # Total skills
            cursor.execute("SELECT COUNT(*) FROM skills")
            stats['total'] = cursor.fetchone()[0]

            # Uploaded skills
            cursor.execute("SELECT COUNT(*) FROM skills WHERE is_uploaded = 1")
            stats['uploaded'] = cursor.fetchone()[0]

            # Local skills
            cursor.execute("SELECT COUNT(*) FROM skills WHERE source = 'local'")
            stats['local'] = cursor.fetchone()[0]

            # Anthropic skills
            cursor.execute("SELECT COUNT(*) FROM skills WHERE source = 'anthropic'")
            stats['anthropic'] = cursor.fetchone()[0]

            # Custom skills
            cursor.execute("SELECT COUNT(*) FROM skills WHERE source = 'custom'")
            stats['custom'] = cursor.fetchone()[0]

            return stats
