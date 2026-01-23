"""
CLI application for the Password Manager.
"""

import sys
import getpass
import json
import os
import logging
from datetime import datetime
from typing import Optional, List

from db import DatabaseManager
from crypto_utils import CryptoManager
from password_generator import PasswordGenerator
from config import APP_NAME, APP_VERSION

logger = logging.getLogger(__name__)


class PasswordManagerCLI:
    """Command-line interface for the password manager."""
    
    def __init__(self):
        """Initialize CLI application."""
        self.db = DatabaseManager()
        self.crypto = CryptoManager(self.db)
        self.password_gen = PasswordGenerator()
        self.authenticated = False
        
    def run(self):
        """Run the CLI application."""
        self.print_header()
        
        # Check if master password is set
        if not self.db.get_master_salt():
            self.first_run_setup()
        
        # Main loop
        while True:
            if not self.authenticated:
                self.authenticate()
                if not self.authenticated:
                    print("\nAuthentication failed. Exiting.")
                    sys.exit(1)
            
            self.show_menu()
            choice = input("\nEnter your choice (1-9): ").strip()
            
            if choice == '1':
                self.add_entry()
            elif choice == '2':
                self.get_entry()
            elif choice == '3':
                self.delete_entry()
            elif choice == '4':
                self.generate_password()
            elif choice == '5':
                self.list_entries()
            elif choice == '6':
                self.change_master_password()
            elif choice == '7':
                self.export_passwords()  # نیا Export فیچر
            elif choice == '8':
                self.import_passwords()  # نیا Import فیچر
            elif choice == '9':
                print("\nGoodbye!")
                sys.exit(0)
            else:
                print("\nInvalid choice. Please try again.")
    
    def print_header(self):
        """Print application header."""
        print("\n" + "=" * 60)
        print(f"{APP_NAME} - CLI Version {APP_VERSION}")
        print("=" * 60)
    
    def show_menu(self):
        """Display main menu."""
        print("\n" + "-" * 40)
        print("MAIN MENU")
        print("-" * 40)
        print("1. Add new password entry")
        print("2. Get password entry")
        print("3. Delete password entry")
        print("4. Generate secure password")
        print("5. List all entries")
        print("6. Change master password")
        print("7. Export passwords")      # نیا آپشن
        print("8. Import passwords")      # نیا آپشن
        print("9. Exit")
        print("-" * 40)
    
    def first_run_setup(self):
        """First-time setup for master password."""
        print("\n" + "=" * 60)
        print("FIRST TIME SETUP")
        print("=" * 60)
        print("You need to set a master password to secure your vault.")
        print("This password will be used to encrypt all your stored passwords.")
        print("Make sure it's strong and memorable!")
        print("=" * 60)
        
        while True:
            password = getpass.getpass("\nEnter a master password: ")
            
            if not password:
                print("Error: Master password cannot be empty.")
                continue
            
            if len(password) < 8:
                print("Warning: Password should be at least 8 characters.")
                continue
            
            confirm = getpass.getpass("Confirm master password: ")
            
            if password != confirm:
                print("Error: Passwords don't match. Try again.")
                continue
            
            # Initialize master password
            if self.crypto.initialize_master_password(password):
                print("\n✓ Master password set successfully!")
                self.authenticated = True
                break
            else:
                print("Error: Failed to set master password. Please try again.")
                sys.exit(1)
    
    def authenticate(self):
        """Authenticate with master password."""
        print("\n" + "=" * 40)
        print("AUTHENTICATION REQUIRED")
        print("=" * 40)
        
        for attempt in range(3):
            password = getpass.getpass("Enter master password: ")
            
            if self.crypto.authenticate(password):
                self.authenticated = True
                print("\n✓ Authentication successful!")
                return
            else:
                remaining = 2 - attempt
                if remaining > 0:
                    print(f"✗ Authentication failed. {remaining} attempts remaining.")
                else:
                    print("✗ Too many failed attempts.")
    
    def add_entry(self):
        """Add a new password entry."""
        print("\n" + "-" * 40)
        print("ADD NEW PASSWORD ENTRY")
        print("-" * 40)
        
        # Get service
        service = input("Service (optional, e.g., 'github.com'): ").strip()
        if service == '':
            service = None
        
        # Get username
        while True:
            username = input("Username (required): ").strip()
            if username:
                break
            print("Error: Username is required.")
        
        # Get email
        email = input("Email (optional): ").strip()
        if email == '':
            email = None
        
        # Get password
        password = getpass.getpass("Password (press Enter to generate): ")
        if not password:
            password = self.password_gen.generate_password()
            print(f"\nGenerated password: {password}")
            print("✓ Password copied to clipboard (if supported)")
            try:
                import pyperclip
                pyperclip.copy(password)
            except:
                pass
        
        # Get notes
        print("\nNotes (optional, press Enter twice to finish):")
        notes_lines = []
        while True:
            line = input()
            if line == '' and notes_lines:
                break
            if line == '' and not notes_lines:
                continue
            notes_lines.append(line)
        notes = '\n'.join(notes_lines) if notes_lines else None
        
        # Confirm
        print("\n" + "-" * 40)
        print(f"Service: {service or '(not specified)'}")
        print(f"Username: {username}")
        if email:
            print(f"Email: {email}")
        print(f"Password: {'*' * min(len(password), 20)}")
        if notes:
            notes_preview = notes[:50] + "..." if len(notes) > 50 else notes
            print(f"Notes: {notes_preview}")
        print("-" * 40)
        
        confirm = input("\nSave this entry? (y/N): ").strip().lower()
        if confirm != 'y':
            print("Entry not saved.")
            return
        
        # Encrypt and save
        try:
            encrypted_password = self.crypto.encrypt_password(password)
            if self.db.add_entry(service, username, encrypted_password, email, notes):
                print("✓ Entry saved successfully!")
            else:
                print("✗ Failed to save entry.")
        except Exception as e:
            logger.error(f"Error saving entry: {e}")
            print(f"✗ Error: {str(e)}")
    
    def get_entry(self):
        """Get and display a password entry."""
        print("\n" + "-" * 40)
        print("GET PASSWORD ENTRY")
        print("-" * 40)
        
        search_term = input("Search by service, username, or email: ").strip()
        
        if not search_term:
            print("Error: Search term is required.")
            return
        
        # Search for entries
        entries = self.db.get_entries_by_service(search_term)
        all_entries = self.db.get_all_entries()
        
        # Also search by username and email
        search_lower = search_term.lower()
        for entry in all_entries:
            # Check username
            if search_lower in entry['username'].lower():
                if entry['id'] not in [e['id'] for e in entries]:
                    entries.append(entry)
            # Check email
            elif entry.get('email') and search_lower in entry['email'].lower():
                if entry['id'] not in [e['id'] for e in entries]:
                    entries.append(entry)
        
        if not entries:
            print("No entries found.")
            return
        
        # Display results
        print(f"\nFound {len(entries)} matching entr{'y' if len(entries) == 1 else 'ies'}:\n")
        for i, entry in enumerate(entries, 1):
            try:
                created_date = datetime.fromisoformat(entry['created_at'])
                formatted_date = created_date.strftime("%d %B %Y, %I:%M %p")
            except:
                formatted_date = entry['created_at']
            
            print(f"{i}. ID: {entry['id']}")
            print(f"   Service: {entry['service'] or '(not specified)'}")
            print(f"   Username: {entry['username']}")
            if entry.get('email'):
                print(f"   Email: {entry['email']}")
            print(f"   Created: {formatted_date}")
            print()
        
        # Let user select an entry
        try:
            choice = input("Enter entry number to view password (0 to cancel): ").strip()
            if choice == '0':
                return
            
            index = int(choice) - 1
            if 0 <= index < len(entries):
                entry = entries[index]
                
                # Decrypt and display password
                try:
                    password = self.crypto.decrypt_password(entry['password'])
                    
                    print("\n" + "=" * 40)
                    print("PASSWORD DETAILS")
                    print("=" * 40)
                    print(f"Service: {entry['service'] or '(not specified)'}")
                    print(f"Username: {entry['username']}")
                    if entry.get('email'):
                        print(f"Email: {entry['email']}")
                    print(f"Password: {password}")
                    if entry.get('notes'):
                        print(f"\nNotes:")
                        print(entry['notes'])
                    print("=" * 40)
                    
                    # Offer to copy to clipboard
                    copy_choice = input("\nCopy password to clipboard? (y/N): ").strip().lower()
                    if copy_choice == 'y':
                        try:
                            import pyperclip
                            pyperclip.copy(password)
                            print("✓ Password copied to clipboard!")
                        except ImportError:
                            print("✗ pyperclip not installed. Cannot copy to clipboard.")
                except Exception as e:
                    logger.error(f"Error decrypting password: {e}")
                    print("✗ Failed to decrypt password.")
            else:
                print("Invalid selection.")
        except ValueError:
            print("Invalid input. Please enter a number.")
    
    def delete_entry(self):
        """Delete a password entry."""
        print("\n" + "-" * 40)
        print("DELETE PASSWORD ENTRY")
        print("-" * 40)
        
        entry_id = input("Enter entry ID to delete: ").strip()
        
        if not entry_id.isdigit():
            print("Error: ID must be a number.")
            return
        
        # Get entry details
        entry = self.db.get_entry(int(entry_id))
        if not entry:
            print("Error: Entry not found.")
            return
        
        # Display entry details
        print("\nEntry to delete:")
        print(f"ID: {entry['id']}")
        print(f"Service: {entry['service'] or '(not specified)'}")
        print(f"Username: {entry['username']}")
        if entry.get('email'):
            print(f"Email: {entry['email']}")
        
        # Confirm deletion
        confirm = input("\nAre you sure you want to delete this entry? (y/N): ").strip().lower()
        if confirm != 'y':
            print("Deletion cancelled.")
            return
        
        # Delete entry
        if self.db.delete_entry(int(entry_id)):
            print("✓ Entry deleted successfully!")
        else:
            print("✗ Failed to delete entry.")
    
    def generate_password(self):
        """Generate a secure password."""
        print("\n" + "-" * 40)
        print("GENERATE SECURE PASSWORD")
        print("-" * 40)
        
        try:
            length = input(f"Password length (default 20): ").strip()
            length = int(length) if length.isdigit() else 20
            
            if length < 8 or length > 100:
                print("Error: Length must be between 8 and 100.")
                return
            
            print("\nCharacter types to include:")
            print("1. Lowercase letters (a-z)")
            print("2. Uppercase letters (A-Z)")
            print("3. Digits (0-9)")
            print("4. Symbols (!@#$%^&*)")
            print("5. All of the above (recommended)")
            
            choice = input("\nEnter choice (1-5): ").strip()
            
            if choice == '1':
                password = self.password_gen.generate_password(
                    length=length,
                    include_lowercase=True,
                    include_uppercase=False,
                    include_digits=False,
                    include_symbols=False
                )
            elif choice == '2':
                password = self.password_gen.generate_password(
                    length=length,
                    include_lowercase=False,
                    include_uppercase=True,
                    include_digits=False,
                    include_symbols=False
                )
            elif choice == '3':
                password = self.password_gen.generate_password(
                    length=length,
                    include_lowercase=False,
                    include_uppercase=False,
                    include_digits=True,
                    include_symbols=False
                )
            elif choice == '4':
                password = self.password_gen.generate_password(
                    length=length,
                    include_lowercase=False,
                    include_uppercase=False,
                    include_digits=False,
                    include_symbols=True
                )
            elif choice == '5':
                password = self.password_gen.generate_password(length=length)
            else:
                print("Invalid choice. Using default settings.")
                password = self.password_gen.generate_password(length=length)
            
            # Evaluate strength
            evaluation = self.password_gen.evaluate_strength(password)
            
            print("\n" + "=" * 40)
            print("GENERATED PASSWORD")
            print("=" * 40)
            print(f"Password: {password}")
            print(f"Length: {len(password)} characters")
            print(f"Strength: {evaluation['strength']}")
            print(f"Entropy: {evaluation['entropy']:.1f} bits")
            print("=" * 40)
            
            # Offer to copy to clipboard
            copy_choice = input("\nCopy password to clipboard? (y/N): ").strip().lower()
            if copy_choice == 'y':
                try:
                    import pyperclip
                    pyperclip.copy(password)
                    print("✓ Password copied to clipboard!")
                except ImportError:
                    print("✗ pyperclip not installed. Cannot copy to clipboard.")
            
            # Offer to save
            save_choice = input("\nSave this password to vault? (y/N): ").strip().lower()
            if save_choice == 'y':
                service = input("Service (optional): ").strip()
                if service == '':
                    service = None
                
                username = input("Username (required): ").strip()
                if not username:
                    print("Username is required. Password not saved.")
                    return
                
                # Get email and notes
                email = input("Email (optional): ").strip()
                if email == '':
                    email = None
                
                notes = input("Notes (optional): ").strip()
                if notes == '':
                    notes = None
                
                # Encrypt and save
                encrypted_password = self.crypto.encrypt_password(password)
                if self.db.add_entry(service, username, encrypted_password, email, notes):
                    print("✓ Password saved to vault!")
                else:
                    print("✗ Failed to save password.")
        
        except ValueError as e:
            print(f"Error: {str(e)}")
        except Exception as e:
            logger.error(f"Error generating password: {e}")
            print(f"✗ Error: {str(e)}")
    
    def list_entries(self):
        """List all password entries."""
        print("\n" + "-" * 40)
        print("ALL PASSWORD ENTRIES")
        print("-" * 40)
        
        entries = self.db.get_all_entries()
        
        if not entries:
            print("No entries found.")
            return
        
        print(f"\nTotal entries: {len(entries)}\n")
        
        for entry in entries:
            try:
                created_date = datetime.fromisoformat(entry['created_at'])
                formatted_date = created_date.strftime("%d %B %Y, %I:%M %p")
            except:
                formatted_date = entry['created_at']
            
            print(f"ID: {entry['id']}")
            print(f"  Service: {entry['service'] or '(not specified)'}")
            print(f"  Username: {entry['username']}")
            if entry.get('email'):
                print(f"  Email: {entry['email']}")
            if entry.get('notes'):
                notes_preview = entry['notes'][:50] + "..." if len(entry['notes']) > 50 else entry['notes']
                print(f"  Notes: {notes_preview}")
            print(f"  Created: {formatted_date}")
            print()
    
    def change_master_password(self):
        """Change the master password."""
        print("\n" + "=" * 40)
        print("CHANGE MASTER PASSWORD")
        print("=" * 40)
        print("WARNING: This will re-encrypt all stored passwords.")
        print("=" * 40)
        
        current = getpass.getpass("\nEnter current master password: ")
        
        # Verify current password
        if not self.crypto.authenticate(current):
            print("✗ Current password is incorrect.")
            return
        
        new_password = getpass.getpass("Enter new master password: ")
        
        if len(new_password) < 8:
            print("✗ New password must be at least 8 characters.")
            return
        
        confirm = getpass.getpass("Confirm new master password: ")
        
        if new_password != confirm:
            print("✗ Passwords don't match.")
            return
        
        # Change master password
        print("\nRe-encrypting all passwords...")
        if self.crypto.change_master_password(current, new_password):
            print("✓ Master password changed successfully!")
            # Re-authenticate with new password
            self.crypto.authenticate(new_password)
        else:
            print("✗ Failed to change master password.")
    
    def export_passwords(self):
        """Export passwords to an encrypted file."""
        print("\n" + "=" * 40)
        print("EXPORT PASSWORDS")
        print("=" * 40)
        
        # Get all entries
        entries = self.db.get_all_entries()
        if not entries:
            print("No entries to export.")
            return
        
        # Decrypt all passwords for export
        export_data = []
        for entry in entries:
            try:
                decrypted_password = self.crypto.decrypt_password(entry['password'])
                export_data.append({
                    'service': entry['service'],
                    'username': entry['username'],
                    'password': decrypted_password,
                    'email': entry.get('email'),
                    'notes': entry.get('notes'),
                    'created_at': entry['created_at']
                })
            except Exception as e:
                logger.error(f"Error decrypting entry for export: {e}")
                print(f"✗ Failed to decrypt entry {entry['id']}. Export cancelled.")
                return
        
        # Ask for export password
        export_password = getpass.getpass("Enter password to encrypt export file: ")
        if len(export_password) < 6:
            print("✗ Export password must be at least 6 characters.")
            return
        
        confirm_password = getpass.getpass("Confirm export password: ")
        if export_password != confirm_password:
            print("✗ Passwords don't match.")
            return
        
        # Ask for file path
        file_path = input("\nEnter file path to save export (default: password_export.enc): ").strip()
        if not file_path:
            file_path = "password_export.enc"
        
        try:
            # Create export package
            export_package = {
                'metadata': {
                    'export_date': datetime.now().isoformat(),
                    'total_entries': len(export_data),
                    'app_version': '1.0'
                },
                'entries': export_data
            }
            
            # Encrypt export data
            encrypted_package = self.crypto.export_data_with_password(export_package, export_password)
            
            # Save to file
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(encrypted_package, f, indent=2)
            
            print(f"\n✓ Successfully exported {len(export_data)} entries to: {file_path}")
            print("Remember your export password to import this file later!")
            
        except Exception as e:
            logger.error(f"Error exporting passwords: {e}")
            print(f"✗ Export failed: {str(e)}")
    
    def import_passwords(self):
        """Import passwords from an encrypted file."""
        print("\n" + "=" * 40)
        print("IMPORT PASSWORDS")
        print("=" * 40)
        
        # Ask for file path
        file_path = input("Enter path to export file: ").strip()
        
        if not os.path.exists(file_path):
            print("✗ File not found.")
            return
        
        # Ask for import password
        import_password = getpass.getpass("Enter password used to encrypt this file: ")
        
        try:
            # Load encrypted package
            with open(file_path, 'r', encoding='utf-8') as f:
                encrypted_package = json.load(f)
            
            # Decrypt data
            decrypted_data = self.crypto.import_data_with_password(encrypted_package, import_password)
            
            # Validate data structure
            if 'entries' not in decrypted_data:
                raise ValueError("Invalid export file format")
            
            entries = decrypted_data['entries']
            
            if not entries:
                print("No entries found in import file.")
                return
            
            # Show import preview
            print(f"\nFound {len(entries)} entries in export file:")
            for i, entry in enumerate(entries[:5], 1):
                print(f"  {i}. {entry.get('service', '(no service)')} - {entry['username']}")
            
            if len(entries) > 5:
                print(f"  ... and {len(entries) - 5} more entries")
            
            # Ask for import mode
            print("\nImport options:")
            print("  1. Import all, skip duplicates")
            print("  2. Import all, overwrite duplicates")
            print("  3. Cancel import")
            
            mode_choice = input("\nSelect import mode (1-3): ").strip()
            
            if mode_choice == '3':
                print("Import cancelled.")
                return
            
            skip_duplicates = (mode_choice == '1')
            
            # Import entries
            print("\nImporting...")
            imported_count = 0
            skipped_count = 0
            failed_count = 0
            
            for entry in entries:
                service = entry.get('service')
                username = entry['username']
                password = entry['password']
                email = entry.get('email')
                notes = entry.get('notes')
                created_at = entry.get('created_at', datetime.now().isoformat())
                
                # Check if entry exists
                exists = self.db.entry_exists(service, username)
                
                if exists and skip_duplicates:
                    skipped_count += 1
                    continue
                
                # Encrypt password
                try:
                    encrypted_password = self.crypto.encrypt_password(password)
                    
                    if exists and not skip_duplicates:
                        # Find entry ID to update
                        all_entries = self.db.get_all_entries()
                        for db_entry in all_entries:
                            if db_entry['service'] == service and db_entry['username'] == username:
                                self.db.update_entry(db_entry['id'], service, username, encrypted_password, email, notes)
                                imported_count += 1
                                break
                    else:
                        # Add new entry
                        if self.db.add_entry(service, username, encrypted_password, email, notes):
                            imported_count += 1
                        else:
                            failed_count += 1
                            
                except Exception as e:
                    logger.error(f"Error importing entry {username}: {e}")
                    failed_count += 1
            
            # Show results
            print(f"\n✓ Import completed!")
            print(f"  Imported: {imported_count} entries")
            if skipped_count > 0:
                print(f"  Skipped: {skipped_count} duplicates")
            if failed_count > 0:
                print(f"  Failed: {failed_count} entries")
            
        except ValueError as e:
            print(f"\n✗ Failed to import: {str(e)}")
            print("Possible causes:")
            print("  - Incorrect password")
            print("  - Corrupted export file")
            print("  - Invalid file format")
        except Exception as e:
            logger.error(f"Error importing passwords: {e}")
            print(f"✗ Import failed: {str(e)}")


def main():
    """Main function to run the CLI application."""
    # Configure logging
    logging.basicConfig(
        level=logging.WARNING,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create and run CLI
    try:
        cli = PasswordManagerCLI()
        cli.run()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user. Exiting.")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        print(f"\n✗ Unexpected error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()