"""
Configuration constants for the Password Manager.
"""

import os

# Database configuration
DB_NAME = "vault.db"
DB_TABLE_NAME = "vault"
SALT_TABLE_NAME = "master_salt"

# Security configuration
PBKDF2_ITERATIONS = 600000  # High iteration count for key derivation
SALT_LENGTH = 32  # 32 bytes = 256 bits
KEY_LENGTH = 32  # 32 bytes for Fernet key

# Password generation configuration
DEFAULT_PASSWORD_LENGTH = 20
PASSWORD_CHARSET = {
    'lowercase': 'abcdefghijklmnopqrstuvwxyz',
    'uppercase': 'ABCDEFGHIJKLMNOPQRSTUVWXYZ',
    'digits': '0123456789',
    'symbols': '!@#$%^&*()_+-=[]{}|;:,.<>?'
}

# Application configuration
APP_NAME = "Secure Vault Password Manager By Daniyal Shahid"
APP_VERSION = "1.0.0"
GUI_WINDOW_SIZE = "1250x710" # Width x Height
MAX_PASSWORD_LENGTH = 100
MIN_PASSWORD_LENGTH = 8

# Validation patterns
SERVICE_PATTERN = r'^[a-zA-Z0-9\-\.\:\/\ ]*$'  # Allow basic URL characters and spaces
USERNAME_PATTERN = r'^[a-zA-Z0-9_@\.\-]*$'  # Basic username pattern

# Colors for GUI (optional)
COLORS = {
    'primary': '#2c3e50',
    'secondary': '#3498db',
    'success': '#27ae60',
    'danger': '#e74c3c',
    'warning': '#f39c12',
    'light': '#ecf0f1',
    'dark': '#2c3e50'
}