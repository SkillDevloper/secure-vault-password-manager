"""
GUI application for the Password Manager using Tkinter.
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog
import tkinter.simpledialog as simpledialog
import pyperclip
import json
import os
import sys
import logging
from datetime import datetime
from typing import Optional, List
import base64  # For embedded images

from db import DatabaseManager
from crypto_utils import CryptoManager
from password_generator import PasswordGenerator
from config import APP_NAME, GUI_WINDOW_SIZE, COLORS

logger = logging.getLogger(__name__)


def resource_path(relative_path):
    """
    Get the absolute path to a resource, accounting for PyInstaller.
    
    Args:
        relative_path: Path relative to the application root
        
    Returns:
        Absolute path to the resource
    """
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


class PasswordManagerGUI:
    """Main GUI application for the password manager."""
    
    def __init__(self, root):
        """
        Initialize the GUI application.
        
        Args:
            root: Tkinter root window
        """
        self.root = root
        self.root.title(APP_NAME)
        self.root.geometry(GUI_WINDOW_SIZE)
        self.root.resizable(False, False)
        
        
        # Set application icon
        try:
            # Try to use authentication.png as window icon
            if os.path.exists(resource_path('Images/authentication.png')):
                img = tk.PhotoImage(file=resource_path('Images/authentication.png'))
                self.root.iconphoto(False, img)
                logger.info("Window icon set from authentication.png")
            elif os.path.exists(resource_path('icon.ico')):
                self.root.iconbitmap(resource_path('icon.ico'))
        except Exception as e:
            logger.warning(f"Could not set window icon: {e}")
        
        # Initialize managers
        self.db = DatabaseManager()
        self.crypto = CryptoManager(self.db)
        self.password_gen = PasswordGenerator()
        
        # Authentication flag
        self.authenticated = False
        
        # Load images for buttons (optional)
        self.button_images = {}
        self.load_button_images()
        
        # Setup GUI
        self.setup_ui()
        
        # Check if master password is set
        self.check_first_run()
    
    def load_button_images(self):
        """Load images for buttons from Images folder."""
        try:
            # Map button keys to image files
            image_mappings = {
                'authenticate': 'Images/authentication.png',
                'add': 'Images/add.png',
                'update': 'Images/updated.png',
                'delete': 'Images/delete.png',
                'copy': 'Images/copy.png',
                'generate': 'Images/generate.png',
                'refresh': 'Images/refresh.png',
                'export': 'Images/export.png',
                'import': 'Images/import.png',
                'exit': 'Images/exit.png',
                'show': 'Images/show.png',
                'hidden': 'Images/hidden.png',
                'change_password': 'Images/Change-password.png'
            }
            
            for key, image_path in image_mappings.items():
                resource_file = resource_path(image_path)
                if os.path.exists(resource_file):
                    try:
                        img = tk.PhotoImage(file=resource_file)
                        # Resize image if needed (scale to fit button)
                        self.button_images[key] = img
                        logger.info(f"Loaded image: {image_path}")
                    except Exception as e:
                        logger.warning(f"Could not load image {image_path}: {e}")
                else:
                    logger.warning(f"Image file not found: {image_path}")
                    
        except Exception as e:
            logger.warning(f"Could not load button images: {e}")
            self.button_images = {}
    
    def setup_ui(self):
        """Setup the user interface."""
        # Configure styles
        self.setup_styles()
        
        # Create main container
        self.main_frame = ttk.Frame(self.root, padding="10")
        self.main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        self.main_frame.columnconfigure(1, weight=1)
        self.main_frame.rowconfigure(1, weight=1)
        
        # Title label
        title_label = ttk.Label(
            self.main_frame, 
            text=APP_NAME, 
            font=("Arial", 16, "bold")
        )
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 10))
        
        # Status label
        self.status_label = ttk.Label(
            self.main_frame,
            text="Not Authenticated",
            foreground="red"
        )
        self.status_label.grid(row=0, column=2, pady=(0, 10), sticky=tk.E)
        
        # Search frame
        search_frame = ttk.Frame(self.main_frame)
        search_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        
        ttk.Label(search_frame, text="Search:").pack(side=tk.LEFT, padx=(0, 5))
        self.search_var = tk.StringVar()
        self.search_var.trace('w', self.on_search)
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var, width=30)
        search_entry.pack(side=tk.LEFT)
        
        # Treeview for password entries
        self.setup_treeview()
        
        # Details frame
        self.setup_details_frame()
        
        # Button frame (single line at bottom)
        self.setup_button_frame()
    
    def setup_styles(self):
        """Configure ttk styles."""
        style = ttk.Style()
        
        # Configure Treeview style
        style.configure("Treeview", 
                       rowheight=25,
                       font=("Arial", 10))
        style.configure("Treeview.Heading", 
                       font=("Arial", 10, "bold"))
        
        # Configure button styles
        style.configure("Primary.TButton",
                       font=("Arial", 10, "bold"),
                       padding=6)
        style.configure("Success.TButton",
                       font=("Arial", 10),
                       padding=6)
        style.configure("Danger.TButton",
                       font=("Arial", 10),
                       padding=6)
        style.configure("Info.TButton",
                       font=("Arial", 10),
                       padding=6)
    
    def setup_treeview(self):
        """Setup the treeview widget for displaying entries."""
        # Create frame for treeview and scrollbars
        tree_frame = ttk.Frame(self.main_frame)
        tree_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        tree_frame.columnconfigure(0, weight=1)
        tree_frame.rowconfigure(0, weight=1)
        
        # Create treeview with sequential ID display
        columns = ('ID', 'Service', 'Username', 'Email', 'Created')
        self.tree = ttk.Treeview(tree_frame, columns=columns, show='headings', selectmode='browse')
        
        # Define headings
        self.tree.heading('ID', text='ID')
        self.tree.heading('Service', text='Service')
        self.tree.heading('Username', text='Username')
        self.tree.heading('Email', text='Email')
        self.tree.heading('Created', text='Created')
        
        # Define columns
        self.tree.column('ID', width=50, anchor=tk.CENTER)
        self.tree.column('Service', width=150, anchor=tk.W)
        self.tree.column('Username', width=120, anchor=tk.W)
        self.tree.column('Email', width=150, anchor=tk.W)
        self.tree.column('Created', width=120, anchor=tk.W)
        
        # Add scrollbars
        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        
        # Grid treeview and scrollbars
        self.tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        vsb.grid(row=0, column=1, sticky=(tk.N, tk.S))
        hsb.grid(row=1, column=0, sticky=(tk.W, tk.E))
        
        # Bind selection event
        self.tree.bind('<<TreeviewSelect>>', self.on_entry_select)
    
    def setup_details_frame(self):
        """Setup the details frame for viewing/editing entries."""
        details_frame = ttk.LabelFrame(self.main_frame, text="Entry Details", padding="10")
        details_frame.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Service
        ttk.Label(details_frame, text="Service:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.service_var = tk.StringVar()
        service_entry = ttk.Entry(details_frame, textvariable=self.service_var, width=40)
        service_entry.grid(row=0, column=1, columnspan=2, sticky=(tk.W, tk.E), pady=2, padx=(5, 0))
        
        # Username
        ttk.Label(details_frame, text="Username:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.username_var = tk.StringVar()
        username_entry = ttk.Entry(details_frame, textvariable=self.username_var, width=40)
        username_entry.grid(row=1, column=1, columnspan=2, sticky=(tk.W, tk.E), pady=2, padx=(5, 0))
        
        # Email
        ttk.Label(details_frame, text="Email:").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.email_var = tk.StringVar()
        email_entry = ttk.Entry(details_frame, textvariable=self.email_var, width=40)
        email_entry.grid(row=2, column=1, columnspan=2, sticky=(tk.W, tk.E), pady=2, padx=(5, 0))
        
        # Password
        ttk.Label(details_frame, text="Password:").grid(row=3, column=0, sticky=tk.W, pady=2)
        password_frame = ttk.Frame(details_frame)
        password_frame.grid(row=3, column=1, columnspan=2, sticky=(tk.W, tk.E), pady=2, padx=(5, 0))
        
        self.password_var = tk.StringVar()
        self.password_entry = ttk.Entry(password_frame, textvariable=self.password_var, 
                                       width=30, show="*")
        self.password_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Show/hide password button with image
        self.password_visible = False
        if 'show' in self.button_images:
            self.show_password_btn = ttk.Button(password_frame, 
                                               image=self.button_images['show'],
                                               text="Show",
                                               compound=tk.LEFT,
                                               command=self.toggle_password_visibility)
        else:
            self.show_password_btn = ttk.Button(password_frame, text="Show", 
                                               width=8, command=self.toggle_password_visibility)
        self.show_password_btn.pack(side=tk.RIGHT, padx=(5, 0))
        
        # Notes (using scrolled text for multi-line)
        ttk.Label(details_frame, text="Notes:").grid(row=4, column=0, sticky=tk.NW, pady=2)
        notes_frame = ttk.Frame(details_frame)
        notes_frame.grid(row=4, column=1, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), 
                        pady=2, padx=(5, 0))
        
        # Create a scrolled text widget for notes
        self.notes_text = scrolledtext.ScrolledText(notes_frame, height=4, width=40,
                                                   wrap=tk.WORD, font=("Arial", 10))
        self.notes_text.pack(fill=tk.BOTH, expand=True)
        
        # Strength indicator
        self.strength_label = ttk.Label(details_frame, text="", font=("Arial", 9))
        self.strength_label.grid(row=5, column=1, columnspan=2, sticky=tk.W, pady=(5, 0))
        
        # Configure grid weights
        details_frame.columnconfigure(1, weight=1)
        details_frame.rowconfigure(4, weight=1)
    
    def setup_button_frame(self):
        """Setup the button frame (single line at bottom)."""
        button_frame = ttk.Frame(self.main_frame)
        button_frame.grid(row=4, column=0, columnspan=3, sticky=(tk.W, tk.E))
        
        # Create buttons with images or text
        buttons = [
            ("Authenticate", self.authenticate, "Primary.TButton", 12, 'authenticate'),
            ("Add Entry", self.add_entry, "Success.TButton", 10, 'add'),
            ("Update Entry", self.update_entry, "Success.TButton", 12, 'update'),
            ("Delete Entry", self.delete_entry, "Danger.TButton", 10, 'delete'),
            ("Copy Password", self.copy_password, "Success.TButton", 12, 'copy'),
            ("Generate Password", self.show_generator, "Primary.TButton", 15, 'generate'),
            ("Refresh", self.refresh_entries, "Primary.TButton", 10, 'refresh'),
            ("Export", self.export_passwords, "Info.TButton", 10, 'export'),
            ("Import", self.import_passwords, "Info.TButton", 10, 'import'),
            ("Change Password", self.change_master_password, "Danger.TButton", 15, 'change_password'),
            ("Exit", self.root.quit, "Danger.TButton", 10, 'exit')
        ]
        
        # Add buttons in a single line
        for i, (text, command, style, width, img_key) in enumerate(buttons):
            # Try to use image if available
            if img_key and img_key in self.button_images:
                btn = ttk.Button(button_frame, image=self.button_images[img_key], 
                               text=text, command=command, style=style, 
                               compound=tk.TOP)
            else:
                btn = ttk.Button(button_frame, text=text, command=command, 
                               style=style, width=width)
            
            btn.grid(row=0, column=i, padx=2, pady=5)
        
        # Configure grid to keep buttons centered
        for i in range(len(buttons)):
            button_frame.columnconfigure(i, weight=1)
    
    def create_tooltip(self, widget, text):
        """Create a tooltip for a widget."""
        def enter(event):
            x, y, _, _ = widget.bbox("insert")
            x += widget.winfo_rootx() + 25
            y += widget.winfo_rooty() + 25
            
            # Create a toplevel window
            self.tooltip = tk.Toplevel(widget)
            self.tooltip.wm_overrideredirect(True)
            self.tooltip.wm_geometry(f"+{x}+{y}")
            
            label = tk.Label(self.tooltip, text=text, background="lightyellow",
                           relief="solid", borderwidth=1, font=("Arial", 10))
            label.pack()
        
        def leave(event):
            if hasattr(self, 'tooltip'):
                self.tooltip.destroy()
        
        widget.bind("<Enter>", enter)
        widget.bind("<Leave>", leave)
    
    def check_first_run(self):
        """Check if this is the first run (no master password set)."""
        salt = self.db.get_master_salt()
        if salt is None:
            self.show_first_run_dialog()
    
    def show_first_run_dialog(self):
        """Show dialog for first-time setup."""
        messagebox.showinfo("First Run", 
                          "Welcome! It looks like this is your first time.\n"
                          "You need to set a master password to secure your vault.")
        
        while True:
            password = simpledialog.askstring("Set Master Password", 
                                            "Enter a strong master password:",
                                            show='*', parent=self.root)
            if not password:
                messagebox.showerror("Error", "Master password is required.")
                self.root.quit()
                return
            
            confirm = simpledialog.askstring("Confirm Master Password", 
                                           "Confirm your master password:",
                                           show='*', parent=self.root)
            
            if password != confirm:
                messagebox.showerror("Error", "Passwords don't match. Try again.")
                continue
            
            if len(password) < 8:
                messagebox.showwarning("Weak Password", 
                                     "Master password should be at least 8 characters.")
                continue
            
            # Initialize master password
            if self.crypto.initialize_master_password(password):
                self.authenticated = True
                self.status_label.config(text="Authenticated", foreground="green")
                messagebox.showinfo("Success", "Master password set successfully!")
                break
            else:
                messagebox.showerror("Error", "Failed to set master password.")
                self.root.quit()
                return
    
    def authenticate(self):
        """Authenticate with master password."""
        if self.authenticated:
            messagebox.showinfo("Info", "Already authenticated.")
            return
        
        password = simpledialog.askstring("Authentication", 
                                        "Enter master password:",
                                        show='*', parent=self.root)
        
        if not password:
            return
        
        if self.crypto.authenticate(password):
            self.authenticated = True
            self.status_label.config(text="Authenticated", foreground="green")
            self.refresh_entries()
            messagebox.showinfo("Success", "Authentication successful!")
        else:
            messagebox.showerror("Error", "Authentication failed!")
    
    def add_entry(self):
        """Add a new password entry."""
        if not self.authenticated:
            messagebox.showerror("Error", "Please authenticate first.")
            return
        
        # Get values from entry fields
        service = self.service_var.get().strip()
        username = self.username_var.get().strip()
        email = self.email_var.get().strip()
        password = self.password_var.get()
        notes = self.notes_text.get("1.0", tk.END).strip()
        
        # Validate
        if not username:
            messagebox.showerror("Error", "Username is required.")
            return
        
        if not password:
            # Generate password if empty
            password = self.password_gen.generate_password()
            self.password_var.set(password)
            messagebox.showinfo("Info", f"Generated password: {password}")
        
        # Check if entry already exists
        if self.db.entry_exists(service if service else None, username):
            if not messagebox.askyesno("Confirm", 
                                      "Entry already exists. Overwrite?"):
                return
        
        # Encrypt and save
        try:
            encrypted_password = self.crypto.encrypt_password(password)
            if self.db.add_entry(service if service else None, username, 
                               encrypted_password, email if email else None,
                               notes if notes else None):
                messagebox.showinfo("Success", "Entry added successfully!")
                self.clear_entry_fields()
                self.refresh_entries()
            else:
                messagebox.showerror("Error", "Failed to add entry.")
        except Exception as e:
            logger.error(f"Error adding entry: {e}")
            messagebox.showerror("Error", f"Failed to add entry: {str(e)}")
    
    def update_entry(self):
        """Update selected entry."""
        if not self.authenticated:
            messagebox.showerror("Error", "Please authenticate first.")
            return
        
        selected = self.tree.selection()
        if not selected:
            messagebox.showerror("Error", "No entry selected.")
            return
        
        item = self.tree.item(selected[0])
        entry_id = item['values'][0]
        
        # Get current values
        service = self.service_var.get().strip()
        username = self.username_var.get().strip()
        email = self.email_var.get().strip()
        password = self.password_var.get()
        notes = self.notes_text.get("1.0", tk.END).strip()
        
        # Validate
        if not username:
            messagebox.showerror("Error", "Username is required.")
            return
        
        if not password:
            messagebox.showerror("Error", "Password is required.")
            return
        
        # Update entry
        try:
            encrypted_password = self.crypto.encrypt_password(password)
            if self.db.update_entry(entry_id, service if service else None, 
                                   username, encrypted_password, 
                                   email if email else None,
                                   notes if notes else None):
                messagebox.showinfo("Success", "Entry updated successfully!")
                self.refresh_entries()
            else:
                messagebox.showerror("Error", "Failed to update entry.")
        except Exception as e:
            logger.error(f"Error updating entry: {e}")
            messagebox.showerror("Error", f"Failed to update entry: {str(e)}")
    
    def delete_entry(self):
        """Delete selected entry."""
        if not self.authenticated:
            messagebox.showerror("Error", "Please authenticate first.")
            return
        
        selected = self.tree.selection()
        if not selected:
            messagebox.showerror("Error", "No entry selected.")
            return
        
        item = self.tree.item(selected[0])
        entry_id = item['values'][0]
        service = item['values'][1]
        username = item['values'][2]
        
        # Confirm deletion
        confirm_msg = f"Delete entry for {username}"
        if service:
            confirm_msg += f" ({service})"
        confirm_msg += "?"
        
        if messagebox.askyesno("Confirm Deletion", confirm_msg):
            if self.db.delete_entry(entry_id):
                messagebox.showinfo("Success", "Entry deleted successfully!")
                self.clear_entry_fields()
                self.refresh_entries()
            else:
                messagebox.showerror("Error", "Failed to delete entry.")
    
    def copy_password(self):
        """Copy password to clipboard."""
        if not self.authenticated:
            messagebox.showerror("Error", "Please authenticate first.")
            return
        
        password = self.password_var.get()
        if not password:
            messagebox.showerror("Error", "No password to copy.")
            return
        
        try:
            pyperclip.copy(password)
            messagebox.showinfo("Success", "Password copied to clipboard!")
        except Exception as e:
            logger.error(f"Error copying to clipboard: {e}")
            messagebox.showerror("Error", f"Failed to copy: {str(e)}")
    
    def show_generator(self):
        """Show password generator dialog."""
        dialog = PasswordGeneratorDialog(self.root, self.password_gen, self.button_images)
        if dialog.generated_password:
            self.password_var.set(dialog.generated_password)
            self.update_strength_indicator()
    
    def refresh_entries(self):
        """Refresh the entries list with sequential IDs."""
        if not self.authenticated:
            # Clear tree if not authenticated
            for item in self.tree.get_children():
                self.tree.delete(item)
            return
        
        # Clear current items
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # Get all entries
        entries = self.db.get_all_entries()
        
        # Display with sequential numbering
        display_order = {}
        current_id = 1
        
        # First, build a mapping of actual IDs to display IDs
        for entry in entries:
            display_order[entry['id']] = current_id
            current_id += 1
        
        # Add entries to tree with display IDs
        for entry in entries:
            # Format date
            try:
                created_date = datetime.fromisoformat(entry['created_at'])
                formatted_date = created_date.strftime("%Y-%m-%d")
            except:
                formatted_date = entry['created_at']
            
            # Use display ID instead of actual ID
            display_id = display_order[entry['id']]
            
            self.tree.insert('', 'end', values=(
                display_id,  # Display sequential ID
                entry['service'] or '',
                entry['username'],
                entry['email'] or '',
                formatted_date
            ), tags=(entry['id'],))  # Store actual ID as tag
        
        # Store the mapping for later use
        self.id_mapping = {v: k for k, v in display_order.items()}
    
    def on_entry_select(self, event):
        """Handle entry selection in treeview."""
        if not self.authenticated:
            return
        
        selected = self.tree.selection()
        if not selected:
            return
        
        item = self.tree.item(selected[0])
        display_id = item['values'][0]
        
        # Get actual ID from mapping
        actual_id = self.id_mapping.get(display_id)
        if not actual_id:
            return
        
        # Get entry from database using actual ID
        entry = self.db.get_entry(actual_id)
        if entry:
            # Decrypt password
            try:
                decrypted_password = self.crypto.decrypt_password(entry['password'])
                self.service_var.set(entry['service'] or '')
                self.username_var.set(entry['username'])
                self.email_var.set(entry['email'] or '')
                self.password_var.set(decrypted_password)
                
                # Clear and set notes
                self.notes_text.delete("1.0", tk.END)
                if entry['notes']:
                    self.notes_text.insert("1.0", entry['notes'])
                
                self.update_strength_indicator()
            except Exception as e:
                logger.error(f"Error decrypting password: {e}")
                messagebox.showerror("Error", "Failed to decrypt password.")
                self.clear_entry_fields()
    
    def on_search(self, *args):
        """Handle search functionality."""
        if not self.authenticated:
            return
        
        search_term = self.search_var.get().strip()
        
        # Clear current items
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        if not search_term:
            # Show all entries if search is empty
            self.refresh_entries()
            return
        
        # Search entries by service, username, or email
        all_entries = self.db.get_all_entries()
        filtered_entries = []
        
        for entry in all_entries:
            if (search_term.lower() in (entry['service'] or '').lower() or
                search_term.lower() in entry['username'].lower() or
                search_term.lower() in (entry['email'] or '').lower()):
                filtered_entries.append(entry)
        
        # Display filtered entries with sequential IDs
        display_order = {}
        current_id = 1
        
        for entry in filtered_entries:
            display_order[entry['id']] = current_id
            current_id += 1
        
        for entry in filtered_entries:
            try:
                created_date = datetime.fromisoformat(entry['created_at'])
                formatted_date = created_date.strftime("%Y-%m-%d")
            except:
                formatted_date = entry['created_at']
            
            display_id = display_order[entry['id']]
            
            self.tree.insert('', 'end', values=(
                display_id,
                entry['service'] or '',
                entry['username'],
                entry['email'] or '',
                formatted_date
            ), tags=(entry['id'],))
        
        # Store mapping for filtered results
        self.id_mapping = {v: k for k, v in display_order.items()}
    
    def clear_entry_fields(self):
        """Clear all entry fields."""
        self.service_var.set('')
        self.username_var.set('')
        self.email_var.set('')
        self.password_var.set('')
        self.notes_text.delete("1.0", tk.END)
        self.strength_label.config(text='')
    
    def toggle_password_visibility(self):
        """Toggle password visibility."""
        if self.password_entry.cget('show') == '*':
            self.password_entry.config(show='')
            self.password_visible = True
            # Update button with hide image
            if 'hidden' in self.button_images:
                self.show_password_btn.config(image=self.button_images['hidden'], text='Hide')
            else:
                self.show_password_btn.config(text='Hide')
        else:
            self.password_entry.config(show='*')
            self.password_visible = False
            # Update button with show image
            if 'show' in self.button_images:
                self.show_password_btn.config(image=self.button_images['show'], text='Show')
            else:
                self.show_password_btn.config(text='Show')
    
    def update_strength_indicator(self):
        """Update password strength indicator."""
        password = self.password_var.get()
        if password:
            evaluation = self.password_gen.evaluate_strength(password)
            color_map = {
                "Very Weak": "red",
                "Weak": "orange",
                "Moderate": "yellow",
                "Strong": "lightgreen",
                "Very Strong": "green"
            }
            color = color_map.get(evaluation['strength'], 'black')
            self.strength_label.config(
                text=f"Strength: {evaluation['strength']} ({evaluation['entropy']:.1f} bits)",
                foreground=color
            )
        else:
            self.strength_label.config(text='')
    
    def change_master_password(self):
        """Change master password."""
        if not self.authenticated:
            messagebox.showerror("Error", "Please authenticate first.")
            return
        
        old_password = simpledialog.askstring("Change Master Password", 
                                            "Enter current master password:",
                                            show='*', parent=self.root)
        if not old_password:
            return
        
        # Verify current password
        if not self.crypto.authenticate(old_password):
            messagebox.showerror("Error", "Current password is incorrect.")
            return
        
        new_password = simpledialog.askstring("Change Master Password", 
                                            "Enter new master password:",
                                            show='*', parent=self.root)
        if not new_password:
            return
        
        if len(new_password) < 8:
            messagebox.showerror("Error", "New password must be at least 8 characters.")
            return
        
        confirm = simpledialog.askstring("Change Master Password", 
                                       "Confirm new master password:",
                                       show='*', parent=self.root)
        
        if new_password != confirm:
            messagebox.showerror("Error", "Passwords don't match.")
            return
        
        # Change master password
        if self.crypto.change_master_password(old_password, new_password):
            messagebox.showinfo("Success", "Master password changed successfully!")
        else:
            messagebox.showerror("Error", "Failed to change master password.")
    
    def export_passwords(self):
        """Export passwords to an encrypted file."""
        if not self.authenticated:
            messagebox.showerror("Error", "Please authenticate first.")
            return
        
        # Get all entries
        entries = self.db.get_all_entries()
        if not entries:
            messagebox.showinfo("Info", "No entries to export.")
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
                    'email': entry['email'],
                    'notes': entry['notes'],
                    'created_at': entry['created_at']
                })
            except Exception as e:
                logger.error(f"Error decrypting entry for export: {e}")
                messagebox.showerror("Error", f"Failed to decrypt entry {entry['id']}. Export cancelled.")
                return
        
        # Ask for export password
        export_password = simpledialog.askstring("Export Passwords", 
                                               "Enter password to encrypt export file:\n"
                                               "(This can be different from your master password)",
                                               show='*', parent=self.root)
        if not export_password:
            return
        
        if len(export_password) < 6:
            messagebox.showerror("Error", "Export password must be at least 6 characters.")
            return
        
        confirm_password = simpledialog.askstring("Confirm Export Password", 
                                                "Confirm export password:",
                                                show='*', parent=self.root)
        if export_password != confirm_password:
            messagebox.showerror("Error", "Passwords don't match.")
            return
        
        # Ask for save location
        file_path = filedialog.asksaveasfilename(
            defaultextension=".enc",
            filetypes=[("Encrypted files", "*.enc"), ("All files", "*.*")],
            title="Save export file",
            initialfile="password_export.enc"
        )
        
        if not file_path:
            return
        
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
            
            messagebox.showinfo("Success", 
                              f"Successfully exported {len(export_data)} entries to:\n{file_path}\n\n"
                              "Remember your export password to import this file later!")
            
        except Exception as e:
            logger.error(f"Error exporting passwords: {e}")
            messagebox.showerror("Error", f"Export failed: {str(e)}")
    
    def import_passwords(self):
        """Import passwords from an encrypted file."""
        if not self.authenticated:
            messagebox.showerror("Error", "Please authenticate first.")
            return
        
        # Ask for file location
        file_path = filedialog.askopenfilename(
            defaultextension=".enc",
            filetypes=[("Encrypted files", "*.enc"), ("JSON files", "*.json"), ("All files", "*.*")],
            title="Select export file to import"
        )
        
        if not file_path or not os.path.exists(file_path):
            return
        
        # Ask for import password
        import_password = simpledialog.askstring("Import Passwords", 
                                               "Enter password used to encrypt this file:",
                                               show='*', parent=self.root)
        if not import_password:
            return
        
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
                messagebox.showinfo("Info", "No entries found in import file.")
                return
            
            # Show import preview
            preview_text = f"Found {len(entries)} entries in export file:\n\n"
            for i, entry in enumerate(entries[:5], 1):
                preview_text += f"{i}. {entry.get('service', '(no service)')} - {entry['username']}\n"
            
            if len(entries) > 5:
                preview_text += f"... and {len(entries) - 5} more entries\n"
            
            preview_text += "\nHow do you want to handle duplicates?"
            
            # Ask for import mode
            import_mode = messagebox.askyesnocancel("Import Options", 
                                                   preview_text + "\n\n"
                                                   "Yes: Import all, skip duplicates\n"
                                                   "No: Import all, overwrite duplicates\n"
                                                   "Cancel: Abort import")
            
            if import_mode is None:  # Cancelled
                return
            
            skip_duplicates = import_mode  # True = skip, False = overwrite
            
            # Import entries
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
                                self.db.update_entry(db_entry['id'], service, username, 
                                                   encrypted_password, email, notes)
                                imported_count += 1
                                break
                    else:
                        # Add new entry
                        if self.db.add_entry(service, username, encrypted_password, 
                                           email, notes):
                            imported_count += 1
                        else:
                            failed_count += 1
                            
                except Exception as e:
                    logger.error(f"Error importing entry {username}: {e}")
                    failed_count += 1
            
            # Show results
            result_message = f"Import completed!\n\n"
            result_message += f"✓ Imported: {imported_count} entries\n"
            if skipped_count > 0:
                result_message += f"⏭️ Skipped: {skipped_count} duplicates\n"
            if failed_count > 0:
                result_message += f"✗ Failed: {failed_count} entries\n"
            
            messagebox.showinfo("Import Results", result_message)
            
            # Refresh entries list
            self.refresh_entries()
            
        except ValueError as e:
            messagebox.showerror("Import Error", 
                               f"Failed to import: {str(e)}\n\n"
                               "Possible causes:\n"
                               "- Incorrect password\n"
                               "- Corrupted export file\n"
                               "- Invalid file format")
        except Exception as e:
            logger.error(f"Error importing passwords: {e}")
            messagebox.showerror("Error", f"Import failed: {str(e)}")


class PasswordGeneratorDialog:
    """Dialog for generating passwords."""
    
    def __init__(self, parent, password_gen, button_images=None):
        """
        Initialize password generator dialog.
        
        Args:
            parent: Parent window
            password_gen: PasswordGenerator instance
            button_images: Dictionary of loaded button images
        """
        self.parent = parent
        self.password_gen = password_gen
        self.button_images = button_images or {}
        self.generated_password = None
        
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Password Generator")
        self.dialog.geometry("400x300")
        self.dialog.resizable(False, False)
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Set dialog icon
        try:
            if 'generate' in self.button_images:
                self.dialog.iconphoto(False, self.button_images['generate'])
        except Exception as e:
            logger.warning(f"Could not set dialog icon: {e}")
        
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the dialog UI."""
        # Variables
        self.length_var = tk.IntVar(value=20)
        self.lower_var = tk.BooleanVar(value=True)
        self.upper_var = tk.BooleanVar(value=True)
        self.digits_var = tk.BooleanVar(value=True)
        self.symbols_var = tk.BooleanVar(value=True)
        self.password_var = tk.StringVar()
        
        # Length
        ttk.Label(self.dialog, text="Length:").grid(row=0, column=0, padx=10, pady=10, sticky=tk.W)
        length_scale = ttk.Scale(self.dialog, from_=8, to=50, variable=self.length_var, 
                               orient=tk.HORIZONTAL)
        length_scale.grid(row=0, column=1, padx=10, pady=10, sticky=(tk.W, tk.E))
        length_label = ttk.Label(self.dialog, textvariable=self.length_var)
        length_label.grid(row=0, column=2, padx=10, pady=10)
        
        # Character types
        ttk.Checkbutton(self.dialog, text="Lowercase (a-z)", 
                       variable=self.lower_var).grid(row=1, column=0, columnspan=3, 
                                                    padx=10, pady=5, sticky=tk.W)
        ttk.Checkbutton(self.dialog, text="Uppercase (A-Z)", 
                       variable=self.upper_var).grid(row=2, column=0, columnspan=3, 
                                                    padx=10, pady=5, sticky=tk.W)
        ttk.Checkbutton(self.dialog, text="Digits (0-9)", 
                       variable=self.digits_var).grid(row=3, column=0, columnspan=3, 
                                                     padx=10, pady=5, sticky=tk.W)
        ttk.Checkbutton(self.dialog, text="Symbols (!@#$)", 
                       variable=self.symbols_var).grid(row=4, column=0, columnspan=3, 
                                                      padx=10, pady=5, sticky=tk.W)
        
        # Generated password
        ttk.Label(self.dialog, text="Generated Password:").grid(row=5, column=0, 
                                                               padx=10, pady=10, sticky=tk.W)
        password_entry = ttk.Entry(self.dialog, textvariable=self.password_var, 
                                  width=30, font=("Courier", 10))
        password_entry.grid(row=5, column=1, columnspan=2, padx=10, pady=10, sticky=(tk.W, tk.E))
        
        # Buttons
        button_frame = ttk.Frame(self.dialog)
        button_frame.grid(row=6, column=0, columnspan=3, pady=10)
        
        # Generate button
        generate_btn = ttk.Button(button_frame, text="Generate", command=self.generate)
        generate_btn.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(button_frame, text="Copy", 
                  command=self.copy).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Use", 
                  command=self.use).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Close", 
                  command=self.dialog.destroy).pack(side=tk.LEFT, padx=5)
        
        # Generate initial password
        self.generate()
        
        # Configure grid
        self.dialog.columnconfigure(1, weight=1)
    
    def generate(self):
        """Generate a new password."""
        try:
            password = self.password_gen.generate_password(
                length=self.length_var.get(),
                include_lowercase=self.lower_var.get(),
                include_uppercase=self.upper_var.get(),
                include_digits=self.digits_var.get(),
                include_symbols=self.symbols_var.get()
            )
            self.password_var.set(password)
        except ValueError as e:
            messagebox.showerror("Error", str(e), parent=self.dialog)
    
    def copy(self):
        """Copy generated password to clipboard."""
        password = self.password_var.get()
        if password:
            try:
                pyperclip.copy(password)
                messagebox.showinfo("Success", "Password copied to clipboard!", 
                                  parent=self.dialog)
            except Exception as e:
                logger.error(f"Error copying password: {e}")
                messagebox.showerror("Error", f"Failed to copy: {str(e)}", 
                                   parent=self.dialog)
    
    def use(self):
        """Use the generated password."""
        self.generated_password = self.password_var.get()
        self.dialog.destroy()


def main():
    """Main function to run the GUI application."""
    import sys
    
    # Configure logging
    logging.basicConfig(
        level=logging.WARNING,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create and run application
    root = tk.Tk()
    app = PasswordManagerGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()