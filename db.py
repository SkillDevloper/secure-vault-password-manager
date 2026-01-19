"""
Database operations for the Password Manager.
Handles SQLite database connection, initialization, and operations.
"""

import sqlite3
import logging
from datetime import datetime
from typing import Optional, List, Tuple, Dict, Any
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages SQLite database operations for the password manager."""
    
    def __init__(self, db_path: str = "vault.db"):
        """
        Initialize database manager.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self._init_database()
    
    @contextmanager
    def _get_connection(self):
        """Context manager for database connections."""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            yield conn
            conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Database error: {e}")
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                conn.close()
    
    def _init_database(self):
        """Initialize database with required tables."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Check if vault table exists and has created_at column
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='vault'
            """)
            
            if cursor.fetchone():
                # Check if created_at column exists
                cursor.execute("PRAGMA table_info(vault)")
                columns = [col[1] for col in cursor.fetchall()]
                
                # Add created_at column for backward compatibility
                if 'created_at' not in columns:
                    cursor.execute("ALTER TABLE vault ADD COLUMN created_at TEXT")
                    
                    # Set default value for existing records
                    cursor.execute("UPDATE vault SET created_at = ? WHERE created_at IS NULL", 
                                 (datetime.now().isoformat(),))
                
                # Add email column if not exists
                if 'email' not in columns:
                    cursor.execute("ALTER TABLE vault ADD COLUMN email TEXT")
                
                # Add notes column if not exists
                if 'notes' not in columns:
                    cursor.execute("ALTER TABLE vault ADD COLUMN notes TEXT")
            else:
                # Create vault table if it doesn't exist
                cursor.execute("""
                    CREATE TABLE vault (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        service TEXT,
                        username TEXT NOT NULL,
                        password TEXT NOT NULL,
                        email TEXT,
                        notes TEXT,
                        created_at TEXT NOT NULL
                    )
                """)
            
            # Create master_salt table if it doesn't exist
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS master_salt (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    salt BLOB NOT NULL,
                    key_hash TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)
            
            # Check if master_salt table exists and has key_hash column
            cursor.execute("PRAGMA table_info(master_salt)")
            master_salt_columns = [col[1] for col in cursor.fetchall()]
            
            # Add key_hash column if not exists (migration for existing databases)
            if 'key_hash' not in master_salt_columns:
                logger.info("Migrating master_salt table: adding key_hash column")
                cursor.execute("ALTER TABLE master_salt ADD COLUMN key_hash TEXT DEFAULT ''")
            
            # Add created_at column if not exists
            if 'created_at' not in master_salt_columns:
                cursor.execute("ALTER TABLE master_salt ADD COLUMN created_at TEXT DEFAULT ?",
                             (datetime.now().isoformat(),))
            
            # Create index for faster lookups
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_username 
                ON vault(username)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_service 
                ON vault(service)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_email 
                ON vault(email)
            """)
    
    def get_master_salt(self) -> Optional[bytes]:
        """
        Retrieve the master salt from database.
        
        Returns:
            Salt bytes if found, None otherwise
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT salt FROM master_salt WHERE id = 1")
                result = cursor.fetchone()
                return result['salt'] if result else None
        except sqlite3.Error as e:
            logger.error(f"Error getting master salt: {e}")
            return None
    
    def get_master_key_hash(self) -> Optional[str]:
        """
        Retrieve the master key hash from database.
        
        Returns:
            Key hash if found, None otherwise
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT key_hash FROM master_salt WHERE id = 1")
                result = cursor.fetchone()
                return result['key_hash'] if result else None
        except sqlite3.Error as e:
            logger.error(f"Error getting master key hash: {e}")
            return None
    
    def save_master_salt(self, salt: bytes, key_hash: str = None) -> bool:
        """
        Save master salt to database.
        
        Args:
            salt: Salt bytes to save
            key_hash: Hash of the derived key (for verification)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                # If key_hash is not provided, use empty string for backward compatibility
                cursor.execute("""
                    INSERT OR REPLACE INTO master_salt (id, salt, key_hash, created_at) 
                    VALUES (1, ?, ?, ?)
                """, (salt, key_hash or '', datetime.now().isoformat()))
                return True
        except sqlite3.Error as e:
            logger.error(f"Error saving master salt: {e}")
            return False
    
    def add_entry(self, service: Optional[str], username: str, 
                  encrypted_password: str, email: Optional[str] = None,
                  notes: Optional[str] = None) -> bool:
        """
        Add a new password entry to the database.
        
        Args:
            service: Service name (optional)
            username: Username (required)
            encrypted_password: Encrypted password
            email: Email address (optional)
            notes: Additional notes (optional)
            
        Returns:
            True if successful, False otherwise
        """
        if not username or not encrypted_password:
            return False
            
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO vault (service, username, password, email, notes, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (service, username, encrypted_password, email, notes,
                      datetime.now().isoformat()))
                return True
        except sqlite3.Error as e:
            logger.error(f"Error adding entry: {e}")
            return False
    
    def get_entry(self, entry_id: int) -> Optional[Dict[str, Any]]:
        """
        Get a specific entry by ID.
        
        Args:
            entry_id: Entry ID
            
        Returns:
            Entry dictionary or None if not found
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, service, username, password, email, notes, created_at
                    FROM vault WHERE id = ?
                """, (entry_id,))
                result = cursor.fetchone()
                return dict(result) if result else None
        except sqlite3.Error as e:
            logger.error(f"Error getting entry: {e}")
            return None
    
    def get_all_entries(self) -> List[Dict[str, Any]]:
        """
        Get all password entries, sorted by creation date.
        
        Returns:
            List of entry dictionaries
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, service, username, password, email, notes, created_at
                    FROM vault 
                    ORDER BY created_at DESC
                """)
                return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error(f"Error getting all entries: {e}")
            return []
    
    def get_entries_by_service(self, service: str) -> List[Dict[str, Any]]:
        """
        Get entries by service name.
        
        Args:
            service: Service name
            
        Returns:
            List of entry dictionaries
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, service, username, password, email, notes, created_at
                    FROM vault 
                    WHERE service LIKE ?
                    ORDER BY created_at DESC
                """, (f"%{service}%",))
                return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error(f"Error getting entries by service: {e}")
            return []
    
    def delete_entry(self, entry_id: int) -> bool:
        """
        Delete an entry by ID.
        
        Args:
            entry_id: Entry ID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM vault WHERE id = ?", (entry_id,))
                return cursor.rowcount > 0
        except sqlite3.Error as e:
            logger.error(f"Error deleting entry: {e}")
            return False
    
    def entry_exists(self, service: str, username: str) -> bool:
        """
        Check if an entry already exists.
        
        Args:
            service: Service name
            username: Username
            
        Returns:
            True if entry exists, False otherwise
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT COUNT(*) as count 
                    FROM vault 
                    WHERE service = ? AND username = ?
                """, (service, username))
                result = cursor.fetchone()
                return result['count'] > 0 if result else False
        except sqlite3.Error as e:
            logger.error(f"Error checking entry existence: {e}")
            return False
    
    def update_entry(self, entry_id: int, service: Optional[str], 
                     username: str, encrypted_password: str, 
                     email: Optional[str] = None, notes: Optional[str] = None) -> bool:
        """
        Update an existing entry.
        
        Args:
            entry_id: Entry ID
            service: New service name
            username: New username
            encrypted_password: New encrypted password
            email: New email address
            notes: New notes
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE vault 
                    SET service = ?, username = ?, password = ?, email = ?, notes = ?
                    WHERE id = ?
                """, (service, username, encrypted_password, email, notes, entry_id))
                return cursor.rowcount > 0
        except sqlite3.Error as e:
            logger.error(f"Error updating entry: {e}")
            return False
    
    # New methods for sequential ID management
    def get_entries_with_sequential_ids(self) -> List[Dict[str, Any]]:
        """
        Get all entries with sequential display IDs.
        This maintains 1, 2, 3, 4... sequence even after deletions.
        
        Returns:
            List of entries with sequential display IDs
        """
        try:
            entries = self.get_all_entries()
            
            # Add sequential display ID
            for i, entry in enumerate(entries, 1):
                entry['display_id'] = i
            
            return entries
        except Exception as e:
            logger.error(f"Error getting sequential entries: {e}")
            return []
    
    def get_next_display_id(self) -> int:
        """
        Get next sequential display ID.
        
        Returns:
            Next available display ID
        """
        try:
            entries = self.get_all_entries()
            return len(entries) + 1
        except Exception as e:
            logger.error(f"Error getting next display ID: {e}")
            return 1
    
    def get_actual_id_from_display_id(self, display_id: int) -> Optional[int]:
        """
        Get actual database ID from display ID.
        
        Args:
            display_id: Sequential display ID (1, 2, 3...)
            
        Returns:
            Actual database ID or None if not found
        """
        try:
            entries = self.get_all_entries()
            if 1 <= display_id <= len(entries):
                # Display IDs are 1-indexed, entries are sorted by created_at DESC
                # So we need to get the entry at position (display_id - 1)
                return entries[display_id - 1]['id']
            return None
        except Exception as e:
            logger.error(f"Error getting actual ID from display ID: {e}")
            return None
    
    def search_entries(self, search_term: str) -> List[Dict[str, Any]]:
        """
        Search entries by service, username, or email.
        
        Args:
            search_term: Search term
            
        Returns:
            List of matching entries with sequential display IDs
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, service, username, password, email, notes, created_at
                    FROM vault 
                    WHERE service LIKE ? OR username LIKE ? OR email LIKE ?
                    ORDER BY created_at DESC
                """, (f"%{search_term}%", f"%{search_term}%", f"%{search_term}%"))
                
                entries = [dict(row) for row in cursor.fetchall()]
                
                # Add sequential display IDs
                for i, entry in enumerate(entries, 1):
                    entry['display_id'] = i
                
                return entries
        except sqlite3.Error as e:
            logger.error(f"Error searching entries: {e}")
            return []
    
    def get_entry_by_display_id(self, display_id: int) -> Optional[Dict[str, Any]]:
        """
        Get entry by display ID.
        
        Args:
            display_id: Sequential display ID
            
        Returns:
            Entry dictionary or None if not found
        """
        try:
            actual_id = self.get_actual_id_from_display_id(display_id)
            if actual_id:
                return self.get_entry(actual_id)
            return None
        except Exception as e:
            logger.error(f"Error getting entry by display ID: {e}")
            return None
    
    def delete_entry_by_display_id(self, display_id: int) -> bool:
        """
        Delete entry by display ID.
        
        Args:
            display_id: Sequential display ID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            actual_id = self.get_actual_id_from_display_id(display_id)
            if actual_id:
                return self.delete_entry(actual_id)
            return False
        except Exception as e:
            logger.error(f"Error deleting entry by display ID: {e}")
            return False
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get database statistics.
        
        Returns:
            Dictionary with statistics
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Total entries
                cursor.execute("SELECT COUNT(*) as count FROM vault")
                total_entries = cursor.fetchone()['count']
                
                # Entries with email
                cursor.execute("SELECT COUNT(*) as count FROM vault WHERE email IS NOT NULL AND email != ''")
                entries_with_email = cursor.fetchone()['count']
                
                # Entries with notes
                cursor.execute("SELECT COUNT(*) as count FROM vault WHERE notes IS NOT NULL AND notes != ''")
                entries_with_notes = cursor.fetchone()['count']
                
                # Most recent entry
                cursor.execute("SELECT MAX(created_at) as latest FROM vault")
                latest_entry = cursor.fetchone()['latest']
                
                return {
                    'total_entries': total_entries,
                    'entries_with_email': entries_with_email,
                    'entries_with_notes': entries_with_notes,
                    'latest_entry': latest_entry
                }
        except sqlite3.Error as e:
            logger.error(f"Error getting statistics: {e}")
            return {
                'total_entries': 0,
                'entries_with_email': 0,
                'entries_with_notes': 0,
                'latest_entry': None
            }