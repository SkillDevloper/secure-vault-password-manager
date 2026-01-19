"""
Cryptographic utilities for the Password Manager.
Handles encryption, decryption, and key derivation.
"""

import os
import base64
import logging
import hashlib
import secrets
import json
from typing import Optional, Dict, List, Any
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend
from cryptography.exceptions import InvalidSignature, InvalidKey

from config import PBKDF2_ITERATIONS, SALT_LENGTH, KEY_LENGTH

logger = logging.getLogger(__name__)


class CryptoManager:
    """Manages cryptographic operations for the password manager."""
    
    def __init__(self, db_manager):
        """
        Initialize crypto manager.
        
        Args:
            db_manager: DatabaseManager instance
        """
        self.db = db_manager
        self._fernet = None
        self._master_key = None
    
    def generate_salt(self) -> bytes:
        """
        Generate a cryptographically secure random salt.
        
        Returns:
            Random salt bytes
        """
        return secrets.token_bytes(SALT_LENGTH)
    
    def derive_key_from_password(self, password: str, salt: bytes) -> bytes:
        """
        Derive encryption key from password using PBKDF2.
        
        Args:
            password: Master password
            salt: Salt bytes
            
        Returns:
            Derived key bytes
        """
        try:
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=KEY_LENGTH,
                salt=salt,
                iterations=PBKDF2_ITERATIONS,
                backend=default_backend()
            )
            password_bytes = password.encode('utf-8')
            key = kdf.derive(password_bytes)
            return base64.urlsafe_b64encode(key)
        except Exception as e:
            logger.error(f"Error deriving key: {e}")
            raise
    
    def verify_password(self, password: str, salt: bytes, stored_key_hash: str) -> bool:
        """
        Verify if password is correct by deriving key and comparing hash.
        
        Args:
            password: Password to verify
            salt: Salt used for key derivation
            stored_key_hash: Hash of the correct key
            
        Returns:
            True if password is correct, False otherwise
        """
        try:
            derived_key = self.derive_key_from_password(password, salt)
            derived_key_hash = hashlib.sha256(derived_key).hexdigest()
            return derived_key_hash == stored_key_hash
        except Exception as e:
            logger.error(f"Error verifying password: {e}")
            return False
    
    def initialize_master_password(self, password: str) -> bool:
        """
        Initialize master password (first-time setup).
        
        Args:
            password: Master password
            
        Returns:
            True if successful, False otherwise
        """
        if not password:
            return False
            
        try:
            # Generate and save salt
            salt = self.generate_salt()
            
            # Derive key and calculate its hash for verification
            key = self.derive_key_from_password(password, salt)
            key_hash = hashlib.sha256(key).hexdigest()
            
            # Save salt and key hash to database
            if not self.db.save_master_salt(salt, key_hash):
                return False
            
            self._master_key = key
            self._fernet = Fernet(key)
            
            logger.info("Master password initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Error initializing master password: {e}")
            return False
    
    def authenticate(self, password: str) -> bool:
        """
        Authenticate user with master password.
        
        Args:
            password: Master password
            
        Returns:
            True if authentication successful, False otherwise
        """
        try:
            # Get stored salt
            salt = self.db.get_master_salt()
            if not salt:
                logger.error("No master salt found in database")
                return False
            
            # Derive key from provided password
            key = self.derive_key_from_password(password, salt)
            key_hash = hashlib.sha256(key).hexdigest()
            
            # Get stored key hash
            stored_key_hash = self.db.get_master_key_hash()
            
            # If key_hash is stored, it MUST match (primary verification)
            if stored_key_hash and stored_key_hash.strip():
                if key_hash != stored_key_hash:
                    logger.error("Authentication failed: Key hash mismatch")
                    return False
                logger.info("Authentication successful - key hash verified")
                self._master_key = key
                self._fernet = Fernet(key)
                return True
            else:
                # Fallback to encryption test for backward compatibility
                logger.warning("No stored key hash found, using encryption test only")
                self._master_key = key
                self._fernet = Fernet(key)
                
                # Test encryption/decryption
                test_data = b"test"
                encrypted = self._fernet.encrypt(test_data)
                decrypted = self._fernet.decrypt(encrypted)
                
                if decrypted != test_data:
                    logger.error("Authentication failed: Encryption test failed")
                    return False
                
                logger.info("Authentication successful - encryption test passed")
                return True
            
        except (InvalidKey, InvalidSignature) as e:
            logger.error(f"Authentication failed - Invalid key: {e}")
            return False
        except Exception as e:
            logger.error(f"Error during authentication: {e}")
            return False
    
    def encrypt_password(self, password: str) -> str:
        """
        Encrypt a password.
        
        Args:
            password: Plaintext password
            
        Returns:
            Encrypted password as base64 string
        """
        if not self._fernet:
            raise RuntimeError("Not authenticated. Call authenticate() first.")
        
        try:
            password_bytes = password.encode('utf-8')
            encrypted_bytes = self._fernet.encrypt(password_bytes)
            return encrypted_bytes.decode('ascii')
        except Exception as e:
            logger.error(f"Error encrypting password: {e}")
            raise
    
    def decrypt_password(self, encrypted_password: str) -> str:
        """
        Decrypt a password.
        
        Args:
            encrypted_password: Encrypted password as base64 string
            
        Returns:
            Decrypted password
        """
        if not self._fernet:
            raise RuntimeError("Not authenticated. Call authenticate() first.")
        
        try:
            encrypted_bytes = encrypted_password.encode('ascii')
            decrypted_bytes = self._fernet.decrypt(encrypted_bytes)
            return decrypted_bytes.decode('utf-8')
        except (InvalidSignature, InvalidKey) as e:
            logger.error(f"Decryption failed - possible tampering: {e}")
            raise
        except Exception as e:
            logger.error(f"Error decrypting password: {e}")
            raise
    
    def is_authenticated(self) -> bool:
        """
        Check if user is authenticated.
        
        Returns:
            True if authenticated, False otherwise
        """
        return self._fernet is not None
    
    def change_master_password(self, old_password: str, new_password: str) -> bool:
        """
        Change master password and re-encrypt all stored passwords.
        
        Args:
            old_password: Current master password
            new_password: New master password
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Authenticate with old password
            if not self.authenticate(old_password):
                return False
            
            # Get all entries
            entries = self.db.get_all_entries()
            if not entries:
                # No entries to re-encrypt, just change salt
                return self.initialize_master_password(new_password)
            
            # Decrypt all passwords with old key
            decrypted_entries = []
            for entry in entries:
                try:
                    decrypted_password = self.decrypt_password(entry['password'])
                    decrypted_entries.append({
                        'id': entry['id'],
                        'service': entry['service'],
                        'username': entry['username'],
                        'password': decrypted_password
                    })
                except Exception as e:
                    logger.error(f"Error decrypting entry {entry['id']}: {e}")
                    return False
            
            # Generate new salt and key
            new_salt = self.generate_salt()
            new_key = self.derive_key_from_password(new_password, new_salt)
            new_key_hash = hashlib.sha256(new_key).hexdigest()
            
            # Save new salt with key_hash
            if not self.db.save_master_salt(new_salt, new_key_hash):
                return False
            
            # Update Fernet instance with new key
            self._fernet = Fernet(new_key)
            self._master_key = new_key
            
            # Re-encrypt all passwords with new key
            for entry in decrypted_entries:
                new_encrypted_password = self.encrypt_password(entry['password'])
                if not self.db.update_entry(
                    entry['id'],
                    entry['service'],
                    entry['username'],
                    new_encrypted_password
                ):
                    return False
            
            return True
        except Exception as e:
            logger.error(f"Error changing master password: {e}")
            return False
    
    # New methods for Export/Import functionality
    def export_data_with_password(self, data: Dict[str, Any], export_password: str) -> Dict[str, Any]:
        """
        Export data encrypted with a separate export password.
        
        Args:
            data: Data to export
            export_password: Password for export encryption
            
        Returns:
            Dictionary containing encrypted data and metadata
        """
        try:
            # Generate a new salt for this export
            export_salt = self.generate_salt()
            
            # Derive key from export password
            export_key = self.derive_key_from_password(export_password, export_salt)
            export_fernet = Fernet(export_key)
            
            # Convert data to JSON and encrypt
            data_json = json.dumps(data, indent=2).encode('utf-8')
            encrypted_data = export_fernet.encrypt(data_json)
            
            # Return export package
            return {
                'version': '1.0',
                'export_date': self.get_current_timestamp(),
                'salt': base64.b64encode(export_salt).decode('ascii'),
                'iterations': PBKDF2_ITERATIONS,
                'encrypted_data': base64.b64encode(encrypted_data).decode('ascii'),
                'data_hash': hashlib.sha256(data_json).hexdigest()
            }
        except Exception as e:
            logger.error(f"Error exporting data: {e}")
            raise
    
    def import_data_with_password(self, export_package: Dict[str, Any], import_password: str) -> Dict[str, Any]:
        """
        Import data that was encrypted with export password.
        
        Args:
            export_package: Exported data package
            import_password: Password used during export
            
        Returns:
            Decrypted data
        """
        try:
            # Extract components from export package
            version = export_package.get('version', '1.0')
            if version != '1.0':
                raise ValueError(f"Unsupported export version: {version}")
            
            export_salt = base64.b64decode(export_package['salt'])
            iterations = export_package['iterations']
            encrypted_data = base64.b64decode(export_package['encrypted_data'])
            expected_hash = export_package.get('data_hash')
            
            # Derive key from import password
            if iterations != PBKDF2_ITERATIONS:
                logger.warning(f"Export uses different iterations ({iterations}) than current ({PBKDF2_ITERATIONS})")
            
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=KEY_LENGTH,
                salt=export_salt,
                iterations=iterations,
                backend=default_backend()
            )
            import_key = base64.urlsafe_b64encode(kdf.derive(import_password.encode('utf-8')))
            import_fernet = Fernet(import_key)
            
            # Decrypt data
            decrypted_data = import_fernet.decrypt(encrypted_data)
            
            # Verify data integrity
            if expected_hash:
                actual_hash = hashlib.sha256(decrypted_data).hexdigest()
                if actual_hash != expected_hash:
                    raise ValueError("Data integrity check failed - file may be corrupted or password incorrect")
            
            # Parse JSON
            data = json.loads(decrypted_data.decode('utf-8'))
            return data
            
        except (InvalidKey, InvalidSignature) as e:
            logger.error(f"Import failed - incorrect password or corrupted file: {e}")
            raise ValueError("Incorrect password or corrupted export file")
        except Exception as e:
            logger.error(f"Error importing data: {e}")
            raise
    
    def get_current_timestamp(self) -> str:
        """
        Get current timestamp in ISO format.
        
        Returns:
            Current timestamp string
        """
        from datetime import datetime
        return datetime.now().isoformat()