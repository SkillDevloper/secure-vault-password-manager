"""
Main application file - Password Manager with PyQt5 GUI.
"""

import sys
import os
import logging
from datetime import datetime
import json

from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
import pyperclip

# PDF Generation
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.units import inch

from db import DatabaseManager
from crypto_utils import CryptoManager
from password_generator import PasswordGenerator
from config import (
    APP_NAME,
    APP_VERSION,
    COLORS,
    PDF_EXPORT_TITLE,
    PDF_AUTHOR,
    PDF_COMPANY,
    PDF_FOOTER_TEXT,
)

logger = logging.getLogger(__name__)


class PasswordManagerGUI(QMainWindow):
    """Main GUI application for the password manager using PyQt5."""

    def __init__(self):
        """Initialize the GUI application."""
        super().__init__()
        self.authenticated = False
        self.current_entry_id = None
        self.id_mapping = {}
        self.button_images = {}
        self.dark_mode = False

        # Initialize managers
        self.db = DatabaseManager()
        self.crypto = CryptoManager(self.db)
        self.password_gen = PasswordGenerator()

        # Load button images
        self.load_button_images()

        # Setup UI
        self.init_ui()

        # Check if master password is set
        self.check_first_run()

    def load_button_images(self):
        """Load images for buttons from Images folder."""
        try:
            image_folder = "Images"
            if os.path.exists(image_folder):
                # Map image names to button purposes
                image_mapping = {
                    "authentication.png": "authenticate",
                    "add.png": "add",
                    "updated.png": "update",
                    "delete.png": "delete",
                    "copy.png": "copy",
                    "generate.png": "generate",
                    "refresh.png": "refresh",
                    "export.png": "export_encrypted",
                    "import.png": "import",
                    "exit.png": "exit",
                    "show.png": "show",
                    "hidden.png": "hide",
                    "Change-password.png": "change_password",
                    "search.png": "search",
                    "about.png": "about",
                    "dark.png": "dark_mode",
                }

                for image_file, key in image_mapping.items():
                    image_path = os.path.join(image_folder, image_file)
                    if os.path.exists(image_path):
                        self.button_images[key] = QIcon(image_path)
                        logger.info(f"Loaded image: {image_path}")
                    else:
                        logger.warning(f"Image not found: {image_path}")

            # Set window icon
            icon_path = (
                os.path.join(image_folder, "reset-password.ico")
                if image_folder
                else "reset-password.ico"
            )
            if os.path.exists(icon_path):
                self.setWindowIcon(QIcon(icon_path))

        except Exception as e:
            logger.error(f"Error loading images: {e}")
            self.button_images = {}

    def init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION}")
        self.setGeometry(100, 100, 1350, 750)
        self.setMinimumSize(1200, 700)

        # Apply light mode style by default
        self.apply_light_theme()

        # Create central widget
        central_widget = QWidget()
        central_widget.setObjectName("centralWidget")
        self.setCentralWidget(central_widget)

        # Main layout
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        # Status bar at top - Header removed as requested
        status_bar = self.create_status_bar()
        main_layout.addWidget(status_bar)

        # Main content area
        content_widget = self.create_content_area()
        main_layout.addWidget(content_widget, 1)

        # Button panel
        button_panel = self.create_button_panel()
        main_layout.addWidget(button_panel)

        # Connect signals
        self.entries_table.itemSelectionChanged.connect(self.on_entry_select)

    def apply_light_theme(self):
        """Apply light theme stylesheet."""
        self.setStyleSheet(
            """
            QMainWindow {
                background-color: #f0f2f5;
            }
            
            QWidget#centralWidget {
                background-color: white;
                border-radius: 15px;
                border: 2px solid #e0e0e0;
            }
            
            QPushButton {
                padding: 12px 20px;
                border-radius: 10px;
                font-weight: 600;
                font-size: 13px;
                border: 2px solid transparent;
                margin: 3px;
                min-height: 20px;
            }
            
            QPushButton:hover {
                border: 2px solid rgba(52, 152, 219, 0.5);
            }
            
            QPushButton:pressed {
                border: 2px solid rgba(52, 152, 219, 0.8);
            }
            
            .primary-button {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #5DADE2, stop: 1 #2E86C1);
                color: white;
                font-weight: bold;
                border: 2px solid transparent;
            }
            
            .primary-button:hover {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #2E86C1, stop: 1 #1B4965);
                border: 2px solid rgba(255, 255, 255, 0.3);
            }
            
            .success-button {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #58D68D, stop: 1 #2ECC71);
                color: white;
                font-weight: bold;
                border: 2px solid transparent;
            }
            
            .success-button:hover {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #2ECC71, stop: 1 #27AE60);
                border: 2px solid rgba(255, 255, 255, 0.3);
            }
            
            .warning-button {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #F8B739, stop: 1 #F39C12);
                color: white;
                font-weight: bold;
                border: 2px solid transparent;
            }
            
            .warning-button:hover {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #F39C12, stop: 1 #D68910);
                border: 2px solid rgba(255, 255, 255, 0.3);
            }
            
            .danger-button {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #EC7063, stop: 1 #E74C3C);
                color: white;
                font-weight: bold;
                border: 2px solid transparent;
            }
            
            .danger-button:hover {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #E74C3C, stop: 1 #C0392B);
                border: 2px solid rgba(255, 255, 255, 0.3);
            }
            
            .info-button {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #52B6D6, stop: 1 #2BA8B5);
                color: white;
                font-weight: bold;
                border: 2px solid transparent;
            }
            
            .info-button:hover {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #2BA8B5, stop: 1 #16A085);
                border: 2px solid rgba(255, 255, 255, 0.3);
            }
            
            .dark-mode-button {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #34495E, stop: 1 #1A252F);
                color: white;
                font-weight: bold;
                border: 2px solid transparent;
            }
            
            .dark-mode-button:hover {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #1A252F, stop: 1 #0F1620);
                border: 2px solid rgba(255, 255, 255, 0.3);
            }
            
            .about-button {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #B974D6, stop: 1 #9B59B6);
                color: white;
                font-weight: bold;
                border: 2px solid transparent;
            }
            
            .about-button:hover {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #9B59B6, stop: 1 #8E44AD);
                border: 2px solid rgba(255, 255, 255, 0.3);
            }
            
            QLineEdit, QTextEdit {
                padding: 8px;
                border: 2px solid #ddd;
                border-radius: 6px;
                font-size: 14px;
                background-color: white;
                color: #333;
            }
            
            QLineEdit:focus, QTextEdit:focus {
                border-color: #3498db;
            }
            
            QTableWidget {
                background-color: white;
                border: 2px solid #ddd;
                border-radius: 8px;
                alternate-background-color: #f8f9fa;
                selection-background-color: #3498db;
                selection-color: white;
                font-size: 12px;
            }
            
            QTableWidget::item {
                padding: 8px;
            }
            
            QHeaderView::section {
                background-color: #2c3e50;
                color: white;
                padding: 10px;
                font-weight: bold;
                border: none;
            }
            
            QLabel {
                font-size: 14px;
                color: #333;
            }
            
            QLabel#titleLabel {
                font-size: 24px;
                font-weight: bold;
                color: #2c3e50;
            }
            
            QLabel#statusLabel {
                font-size: 12px;
                font-weight: bold;
                padding: 5px 10px;
                border-radius: 10px;
            }
            
            QLabel#strengthLabel {
                font-size: 12px;
                font-weight: bold;
                padding: 5px;
                border-radius: 5px;
                text-align: center;
            }
            
            QLabel#statsLabel {
                font-size: 12px;
                color: #7f8c8d;
            }
            
            QGroupBox {
                border: 2px solid #ddd;
                border-radius: 8px;
                margin-top: 10px;
                font-weight: bold;
                color: #2c3e50;
            }
            
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
            
            QMessageBox {
                background-color: white;
            }
            
            QMessageBox QLabel {
                color: #333333;
                font-size: 14px;
            }
            
            QMessageBox QPushButton {
                background-color: #3498db;
                color: white;
                padding: 8px 20px;
                border-radius: 6px;
                font-weight: bold;
                min-width: 80px;
            }
            
            QMessageBox QPushButton:hover {
                background-color: #2980b9;
            }
            
            QMessageBox QPushButton:pressed {
                background-color: #21618c;
            }
            
            QInputDialog {
                background-color: white;
            }
            
            QInputDialog QLabel {
                color: #333333;
                font-size: 14px;
            }
            
            QInputDialog QLineEdit {
                background-color: white;
                color: #333333;
                border: 2px solid #ddd;
                border-radius: 6px;
                padding: 8px;
            }
            
            QInputDialog QPushButton {
                background-color: #3498db;
                color: white;
                padding: 8px 20px;
                border-radius: 6px;
                font-weight: bold;
                min-width: 80px;
            }
            
            QInputDialog QPushButton:hover {
                background-color: #2980b9;
            }
        """
        )

    def apply_dark_theme(self):
        """Apply dark theme stylesheet."""
        self.setStyleSheet(
            """
            QMainWindow {
                background-color: #121212;
            }
            
            QWidget#centralWidget {
                background-color: #1e1e1e;
                border-radius: 15px;
                border: 2px solid #333;
            }
            
            QPushButton {
                padding: 12px 20px;
                border-radius: 10px;
                font-weight: 600;
                font-size: 13px;
                border: 2px solid transparent;
                margin: 3px;
                min-height: 20px;
                color: #ffffff;
                background-color: #2d2d2d;
            }
            
            QPushButton:hover {
                border: 2px solid rgba(52, 152, 219, 0.5);
                background-color: #383838;
            }
            
            QPushButton:pressed {
                border: 2px solid rgba(52, 152, 219, 0.8);
                background-color: #2d2d2d;
            }
            
            .primary-button {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #5DADE2, stop: 1 #2E86C1);
                color: white;
                font-weight: bold;
                border: 2px solid transparent;
            }
            
            .primary-button:hover {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #2E86C1, stop: 1 #1B4965);
                border: 2px solid rgba(255, 255, 255, 0.3);
            }
            
            .success-button {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #58D68D, stop: 1 #2ECC71);
                color: white;
                font-weight: bold;
                border: 2px solid transparent;
            }
            
            .success-button:hover {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #2ECC71, stop: 1 #27AE60);
                border: 2px solid rgba(255, 255, 255, 0.3);
            }
            
            .warning-button {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #F8B739, stop: 1 #F39C12);
                color: white;
                font-weight: bold;
                border: 2px solid transparent;
            }
            
            .warning-button:hover {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #F39C12, stop: 1 #D68910);
                border: 2px solid rgba(255, 255, 255, 0.3);
            }
            
            .danger-button {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #EC7063, stop: 1 #E74C3C);
                color: white;
                font-weight: bold;
                border: 2px solid transparent;
            }
            
            .danger-button:hover {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #E74C3C, stop: 1 #C0392B);
                border: 2px solid rgba(255, 255, 255, 0.3);
            }
            
            .info-button {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #52B6D6, stop: 1 #2BA8B5);
                color: white;
                font-weight: bold;
                border: 2px solid transparent;
            }
            
            .info-button:hover {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #2BA8B5, stop: 1 #16A085);
                border: 2px solid rgba(255, 255, 255, 0.3);
            }
            
            .dark-mode-button {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #FFD700, stop: 1 #FFA500);
                color: #1a1a1a;
                font-weight: bold;
                border: 2px solid transparent;
            }
            
            .dark-mode-button:hover {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #FFA500, stop: 1 #FF8C00);
                border: 2px solid rgba(0, 0, 0, 0.3);
            }
            
            .about-button {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #B974D6, stop: 1 #9B59B6);
                color: white;
                font-weight: bold;
                border: 2px solid transparent;
            }
            
            .about-button:hover {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #9B59B6, stop: 1 #8E44AD);
                border: 2px solid rgba(255, 255, 255, 0.3);
            }
            
            QLineEdit, QTextEdit {
                padding: 8px;
                border: 2px solid #444;
                border-radius: 6px;
                font-size: 14px;
                background-color: #2d2d2d;
                color: #ffffff;
            }
            
            QLineEdit:focus, QTextEdit:focus {
                border-color: #3498db;
            }
            
            QTableWidget {
                background-color: #2d2d2d;
                border: 2px solid #444;
                border-radius: 8px;
                alternate-background-color: #333;
                selection-background-color: #3498db;
                selection-color: white;
                font-size: 12px;
                color: #ffffff;
            }
            
            QTableWidget::item {
                padding: 8px;
                color: #ffffff;
            }
            
            QHeaderView::section {
                background-color: #3498db;
                color: white;
                padding: 10px;
                font-weight: bold;
                border: none;
            }
            
            QLabel {
                font-size: 14px;
                color: #ffffff;
            }
            
            QLabel#titleLabel {
                font-size: 24px;
                font-weight: bold;
                color: #ffffff;
            }
            
            QLabel#statusLabel {
                font-size: 12px;
                font-weight: bold;
                padding: 5px 10px;
                border-radius: 10px;
            }
            
            QLabel#strengthLabel {
                font-size: 12px;
                font-weight: bold;
                padding: 5px;
                border-radius: 5px;
                text-align: center;
                color: #ffffff;
            }
            
            QLabel#statsLabel {
                font-size: 12px;
                color: #b0bec5;
            }
            
            QGroupBox {
                border: 2px solid #444;
                border-radius: 8px;
                margin-top: 10px;
                font-weight: bold;
                color: #ffffff;
            }
            
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: #ffffff;
            }
            
            QMessageBox {
                background-color: #1e1e1e;
            }
            
            QMessageBox QLabel {
                color: #e0e0e0;
                font-size: 14px;
            }
            
            QMessageBox QPushButton {
                background-color: #3498db;
                color: white;
                padding: 8px 20px;
                border-radius: 6px;
                font-weight: bold;
                min-width: 80px;
            }
            
            QMessageBox QPushButton:hover {
                background-color: #2980b9;
            }
            
            QMessageBox QPushButton:pressed {
                background-color: #21618c;
            }
            
            QInputDialog {
                background-color: #1e1e1e;
            }
            
            QInputDialog QLabel {
                color: #e0e0e0;
                font-size: 14px;
            }
            
            QInputDialog QLineEdit {
                background-color: #2d2d2d;
                color: #ffffff;
                border: 2px solid #444;
                border-radius: 6px;
                padding: 8px;
            }
            
            QInputDialog QPushButton {
                background-color: #3498db;
                color: white;
                padding: 8px 20px;
                border-radius: 6px;
                font-weight: bold;
                min-width: 80px;
            }
            
            QInputDialog QPushButton:hover {
                background-color: #2980b9;
            }
        """
        )

    def toggle_dark_mode(self):
        """Toggle between light and dark mode."""
        self.dark_mode = not self.dark_mode

        if self.dark_mode:
            self.apply_dark_theme()
            self.dark_mode_btn.setText("Light Mode")
            self.dark_mode_btn.setProperty("class", "dark-mode-button")
            # Update Entry Details title color to white in dark mode
            if hasattr(self, 'entry_details_title'):
                self.entry_details_title.setStyleSheet(
                    """
                    font-size: 18px;
                    font-weight: bold;
                    color: #ffffff;
                    padding-bottom: 10px;
                    border-bottom: 2px solid #3498db;
                """
                )
            # Update status label colors for dark mode
            if hasattr(self, 'status_label'):
                if self.authenticated:
                    self.status_label.setStyleSheet("background-color: #27ae60; color: white;")
                else:
                    self.status_label.setStyleSheet("background-color: #e74c3c; color: white;")
            # Update stats label for dark mode
            if hasattr(self, 'stats_label'):
                self.stats_label.setStyleSheet("color: #b0bec5; font-size: 12px;")
        else:
            self.apply_light_theme()
            self.dark_mode_btn.setText("Dark Mode")
            self.dark_mode_btn.setProperty("class", "dark-mode-button")
            # Update Entry Details title color to dark in light mode
            if hasattr(self, 'entry_details_title'):
                self.entry_details_title.setStyleSheet(
                    """
                    font-size: 18px;
                    font-weight: bold;
                    color: #2c3e50;
                    padding-bottom: 10px;
                    border-bottom: 2px solid #3498db;
                """
                )
            # Update status label colors for light mode
            if hasattr(self, 'status_label'):
                if self.authenticated:
                    self.status_label.setStyleSheet("background-color: #27ae60; color: white;")
                else:
                    self.status_label.setStyleSheet("background-color: #e74c3c; color: white;")
            # Update stats label for light mode
            if hasattr(self, 'stats_label'):
                self.stats_label.setStyleSheet("color: #7f8c8d; font-size: 12px;")

        # Force style update
        self.dark_mode_btn.style().polish(self.dark_mode_btn)
        
        # Update all buttons to reflect new theme
        self.update_button_styles()

    def create_header(self):
        """Create the header with logo and title."""
        header = QWidget()
        header.setFixedHeight(80)
        layout = QHBoxLayout(header)
        layout.setContentsMargins(0, 0, 0, 0)

        # Logo (using authentication image)
        logo_label = QLabel()
        if "authenticate" in self.button_images:
            logo_label.setPixmap(self.button_images["authenticate"].pixmap(50, 50))
        else:
            logo_label.setText("🔐")
            logo_label.setStyleSheet("font-size: 40px;")
        layout.addWidget(logo_label)

        # Title
        title_label = QLabel(APP_NAME)
        title_label.setObjectName("titleLabel")
        layout.addWidget(title_label, 1)

        # Version
        version_label = QLabel(f"v{APP_VERSION}")
        version_label.setStyleSheet("color: #7f8c8d; font-size: 12px;")
        layout.addWidget(version_label)

        return header

    def create_status_bar(self):
        """Create the status bar."""
        status_bar = QWidget()
        status_bar.setFixedHeight(40)
        layout = QHBoxLayout(status_bar)

        # Status indicator
        status_container = QWidget()
        status_container.setFixedHeight(30)
        status_layout = QHBoxLayout(status_container)
        status_layout.setContentsMargins(10, 0, 10, 0)

        self.status_label = QLabel(" Not Authenticated")
        self.status_label.setObjectName("statusLabel")
        if self.dark_mode:
            self.status_label.setStyleSheet("background-color: #e74c3c; color: white;")
        else:
            self.status_label.setStyleSheet("background-color: #e74c3c; color: white;")
        status_layout.addWidget(self.status_label)

        layout.addWidget(status_container)

        # Statistics
        stats_label = QLabel()
        stats_label.setObjectName("statsLabel")
        if self.dark_mode:
            stats_label.setStyleSheet("color: #b0bec5; font-size: 12px;")
        else:
            stats_label.setStyleSheet("color: #7f8c8d; font-size: 12px;")
        layout.addWidget(stats_label, 1)
        self.stats_label = stats_label

        # Update statistics
        self.update_statistics()

        return status_bar

    def create_content_area(self):
        """Create the main content area."""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setSpacing(20)

        # Left panel - Table
        left_panel = self.create_table_panel()
        layout.addWidget(left_panel, 2)

        # Right panel - Details
        right_panel = self.create_details_panel()
        layout.addWidget(right_panel, 1)

        return widget

    def create_table_panel(self):
        """Create the table panel."""
        panel = QWidget()
        panel.setObjectName("tablePanel")
        layout = QVBoxLayout(panel)

        # Search bar
        search_container = QWidget()
        search_layout = QHBoxLayout(search_container)
        search_layout.setContentsMargins(0, 0, 0, 0)

        search_icon = QLabel()
        if "search" in self.button_images:
            search_icon.setPixmap(self.button_images["search"].pixmap(16, 16))
            search_icon.setStyleSheet("padding-right: 5px;")
        else:
            search_icon.setText("🔍")
            search_icon.setStyleSheet("font-size: 16px; padding-right: 5px;")
        search_layout.addWidget(search_icon)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search by service, username, or email...")
        self.search_input.textChanged.connect(self.on_search)
        search_layout.addWidget(self.search_input, 1)

        layout.addWidget(search_container)

        # Table
        self.entries_table = QTableWidget()
        self.entries_table.setColumnCount(5)
        self.entries_table.setHorizontalHeaderLabels(
            ["ID", "Service", "Username", "Email", "Created"]
        )
        self.entries_table.setAlternatingRowColors(True)
        self.entries_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.entries_table.setSelectionMode(QTableWidget.SingleSelection)
        self.entries_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.entries_table.horizontalHeader().setStretchLastSection(True)
        self.entries_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.Interactive
        )

        # Set column widths
        self.entries_table.setColumnWidth(0, 50)
        self.entries_table.setColumnWidth(1, 200)
        self.entries_table.setColumnWidth(2, 180)
        self.entries_table.setColumnWidth(3, 200)

        layout.addWidget(self.entries_table, 1)

        return panel

    def create_details_panel(self):
        """Create the details panel."""
        panel = QWidget()
        panel.setObjectName("detailsPanel")
        layout = QVBoxLayout(panel)

        # Panel title
        self.entry_details_title = QLabel("Entry Details")
        title_color = "#ffffff" if self.dark_mode else "#2c3e50"
        self.entry_details_title.setStyleSheet(
            f"""
            font-size: 18px;
            font-weight: bold;
            color: {title_color};
            padding-bottom: 10px;
            border-bottom: 2px solid #3498db;
        """
        )
        layout.addWidget(self.entry_details_title)

        # Form layout - CHANGED: Labels aligned to left
        form_layout = QFormLayout()
        form_layout.setLabelAlignment(
            Qt.AlignLeft
        )  # Changed from AlignRight to AlignLeft
        form_layout.setSpacing(15)
        form_layout.setContentsMargins(10, 20, 10, 10)

        # Service
        self.service_input = QLineEdit()
        self.service_input.setPlaceholderText("e.g., Google, Facebook")
        form_layout.addRow("Service:", self.service_input)

        # Username
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Username or email")
        form_layout.addRow("Username:", self.username_input)

        # Email
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("Optional email")
        form_layout.addRow("Email:", self.email_input)

        # Password
        password_container = QWidget()
        password_layout = QHBoxLayout(password_container)
        password_layout.setContentsMargins(0, 0, 0, 0)

        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.textChanged.connect(self.update_strength_indicator)
        password_layout.addWidget(self.password_input, 1)

        # Show/Hide button
        self.show_password_btn = QPushButton()
        if "show" in self.button_images:
            self.show_password_btn.setIcon(self.button_images["show"])
            self.show_password_btn.setToolTip("Show Password")
        else:
            self.show_password_btn.setText("👁")
            self.show_password_btn.setToolTip("Show Password")
        self.show_password_btn.setCheckable(True)
        self.show_password_btn.setFixedWidth(40)
        self.show_password_btn.toggled.connect(self.toggle_password_visibility)
        password_layout.addWidget(self.show_password_btn)

        # Copy button
        copy_btn = QPushButton()
        if "copy" in self.button_images:
            copy_btn.setIcon(self.button_images["copy"])
            copy_btn.setToolTip("Copy Password")
        else:
            copy_btn.setText("📋")
            copy_btn.setToolTip("Copy Password")
        copy_btn.setFixedWidth(40)
        copy_btn.clicked.connect(self.copy_password)
        password_layout.addWidget(copy_btn)

        form_layout.addRow("Password:", password_container)

        # Strength indicator
        strength_container = QWidget()
        strength_layout = QHBoxLayout(strength_container)
        strength_layout.setContentsMargins(0, 0, 0, 0)

        self.strength_label = QLabel()
        self.strength_label.setObjectName("strengthLabel")
        self.strength_label.setAlignment(Qt.AlignCenter)
        self.strength_label.setMinimumHeight(25)
        strength_layout.addWidget(self.strength_label)

        form_layout.addRow("Strength:", strength_container)

        # Notes
        notes_label = QLabel("Notes:")
        notes_label.setStyleSheet("font-weight: bold;")
        self.notes_input = QTextEdit()
        self.notes_input.setMaximumHeight(120)
        self.notes_input.setPlaceholderText("Add optional notes...")
        form_layout.addRow(notes_label, self.notes_input)

        layout.addLayout(form_layout)
        layout.addStretch(1)

        return panel

    def create_button_panel(self):
        """Create the button panel."""
        panel = QWidget()
        panel.setFixedHeight(160)
        layout = QVBoxLayout(panel)
        layout.setSpacing(8)
        layout.setContentsMargins(5, 5, 5, 5)

        # Create two rows of buttons
        row1 = QHBoxLayout()
        row2 = QHBoxLayout()

        # Button definitions with images
        buttons_row1 = [
            ("Authenticate", self.authenticate, "primary-button", "authenticate"),
            ("Add Entry", self.add_entry, "success-button", "add"),
            ("Update Entry", self.update_entry, "warning-button", "update"),
            ("Delete Entry", self.delete_entry, "danger-button", "delete"),
            ("Generate", self.show_generator, "primary-button", "generate"),
        ]

        buttons_row2 = [
            ("Refresh", self.refresh_entries, "info-button", "refresh"),
            ("Export", self.export_passwords, "info-button", "export_encrypted"),
            ("PDF Export", self.export_to_pdf, "warning-button", "export_encrypted"),
            ("Import", self.import_passwords, "info-button", "import"),
            (
                "Change Password",
                self.change_master_password,
                "danger-button",
                "change_password",
            ),
            ("Dark Mode", self.toggle_dark_mode, "dark-mode-button", "dark_mode"),
            ("About", self.show_about, "about-button", "about"),
            ("Exit", self.close, "danger-button", "exit"),
        ]

        # Add buttons to rows
        for text, slot, style, image_key in buttons_row1:
            btn = self.create_button(text, slot, style, image_key)
            row1.addWidget(btn)

        for text, slot, style, image_key in buttons_row2:
            btn = self.create_button(text, slot, style, image_key)
            if text == "Dark Mode":
                self.dark_mode_btn = btn
            row2.addWidget(btn)

        layout.addLayout(row1)
        layout.addLayout(row2)

        return panel

    def create_button(self, text, slot, style, image_key=None):
        """Create a styled button with optional icon."""
        btn = QPushButton(text)
        btn.setProperty("class", style)

        if image_key and image_key in self.button_images:
            btn.setIcon(self.button_images[image_key])
            btn.setIconSize(QSize(22, 22))

        btn.clicked.connect(slot)

        # Add tooltip
        btn.setToolTip(text)
        
        # Store reference for later updates
        if not hasattr(self, '_button_widgets'):
            self._button_widgets = []
        self._button_widgets.append(btn)

        return btn
    
    def update_button_styles(self):
        """Update all button styles when theme changes."""
        # Buttons are styled via the main stylesheet, so we just need to refresh
        if hasattr(self, '_button_widgets'):
            for btn in self._button_widgets:
                btn.style().unpolish(btn)
                btn.style().polish(btn)
                btn.update()

    def update_statistics(self):
        """Update statistics display."""
        try:
            stats = self.db.get_statistics()
            stats_text = f" Total: {stats['total_entries']} | With Email: {stats['entries_with_email']} | With Notes: {stats['entries_with_notes']}"
            self.stats_label.setText(stats_text)
        except Exception as e:
            logger.error(f"Error updating statistics: {e}")
            self.stats_label.setText(" Statistics: N/A")

    def show_about(self):
        """Show about dialog with application information."""
        about_dialog = QDialog(self)
        about_dialog.setWindowTitle("About Secure Vault")
        about_dialog.setMinimumWidth(500)
        about_dialog.setMinimumHeight(400)

        layout = QVBoxLayout(about_dialog)

        # Header with logo
        header_layout = QHBoxLayout()

        # Logo
        logo_label = QLabel()
        if "authenticate" in self.button_images:
            logo_label.setPixmap(self.button_images["authenticate"].pixmap(64, 64))
        else:
            logo_label.setText("🔐")
            logo_label.setStyleSheet("font-size: 48px;")
        header_layout.addWidget(logo_label)

        # Title
        title_label = QLabel(APP_NAME)
        title_label.setStyleSheet(
            """
            font-size: 24px;
            font-weight: bold;
            color: #2c3e50;
        """
        )
        header_layout.addWidget(title_label, 1)

        layout.addLayout(header_layout)

        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        separator.setStyleSheet("background-color: #3498db; height: 2px;")
        layout.addWidget(separator)

        # Application info - Color based on theme
        text_color = "#333333" if not self.dark_mode else "#e0e0e0"
        heading_color = "#2c3e50" if not self.dark_mode else "#3498db"
        link_color = "#3498db" if not self.dark_mode else "#64b5f6"
        footer_color = "#7f8c8d" if not self.dark_mode else "#b0bec5"
        
        info_text = f"""
        <div style="text-align: center; padding: 10px;">
            <h3 style="color: {heading_color};">Secure Vault Password Manager</h3>
            <p style="color: {text_color};"><b>Version:</b> {APP_VERSION}</p>
            <p style="color: {text_color};"><b>Developer:</b> Daniyal Shahid</p>
            <p style="color: {text_color};"><b>Email:</b> daniyalpro.dev@gmail.com.com</p>
            <p style="color: {text_color};"><b>GitHub:</b> <a href="https://github.com/skilldevloper" style="color: {link_color};">github.com/skilldevloper</a></p>
        </div>
        
        <div style="margin-top: 20px;">
            <h4 style="color: {heading_color};">About This Software:</h4>
            <p style="color: {text_color};">Secure Vault is a robust, secure, and user-friendly password manager designed to keep your credentials safe.</p>
            
            <h4 style="color: {heading_color};">Key Features:</h4>
            <ul style="color: {text_color};">
                <li>Military-grade AES-256 encryption</li>
                <li>Master password protection</li>
                <li>Built-in password generator</li>
                <li>Password strength analyzer</li>
                <li>Export to encrypted files</li>
                <li>Export to PDF reports</li>
                <li>Dark/Light mode</li>
                <li>Quick search functionality</li>
                <li>One-click password copying</li>
            </ul>
            
            <h4 style="color: {heading_color};">Security Features:</h4>
            <ul style="color: {text_color};">
                <li>PBKDF2 key derivation</li>
                <li>Salted password hashing</li>
                <li>Encrypted database</li>
                <li>No internet connection required</li>
                <li>Local storage only</li>
            </ul>
        </div>
        
        <div style="margin-top: 20px; text-align: center; color: {footer_color};">
            <p>© 2026 Daniyal Shahid. All rights reserved.</p>
            <p>This software is provided "as is" without any warranty.</p>
        </div>
        """

        info_label = QLabel(info_text)
        info_label.setTextFormat(Qt.RichText)
        info_label.setTextInteractionFlags(Qt.TextBrowserInteraction)
        info_label.setOpenExternalLinks(True)
        info_label.setWordWrap(True)
        # Set background color based on theme
        if self.dark_mode:
            info_label.setStyleSheet("background-color: #1e1e1e; padding: 10px;")
        else:
            info_label.setStyleSheet("background-color: white; padding: 10px;")

        scroll_area = QScrollArea()
        scroll_area.setWidget(info_label)
        scroll_area.setWidgetResizable(True)
        layout.addWidget(scroll_area, 1)

        # Close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(about_dialog.accept)
        close_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #3498db;
                color: white;
                padding: 10px 20px;
                border-radius: 6px;
                font-weight: normal;
                font-size: 14px;
            }
            
            QPushButton:hover {
                background-color: #2980b9;
            }
        """
        )

        button_layout = QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(close_btn)
        button_layout.addStretch()
        layout.addLayout(button_layout)

        about_dialog.exec_()

    # ===== CORE FUNCTIONALITY METHODS =====

    def check_first_run(self):
        """Check if this is the first run (no master password set)."""
        salt = self.db.get_master_salt()
        if salt is None:
            self.show_first_run_dialog()

    def show_first_run_dialog(self):
        """Show dialog for first-time setup."""
        msg = QMessageBox(self)
        msg.setWindowTitle("First Run")
        msg.setText("Welcome to Secure Vault!")
        msg.setInformativeText(
            "It looks like this is your first time.\nYou need to set a master password to secure your vault."
        )
        msg.setIcon(QMessageBox.Information)
        msg.setMinimumWidth(420)
        msg.setStyleSheet(
            """
    QLabel {
        min-width: 360px;
        font-size: 13px;
            }
        """
        )
        msg.exec_()

        while True:
            password, ok = QInputDialog.getText(
                self,
                "Set Master Password",
                "Enter a strong master password:",
                QLineEdit.Password,
            )

            if not ok or not password:
                QMessageBox.critical(self, "Error", "Master password is required.")
                self.close()
                return

            confirm, ok = QInputDialog.getText(
                self,
                "Confirm Master Password",
                "Confirm your master password:",
                QLineEdit.Password,
            )

            if not ok:
                continue

            if password != confirm:
                QMessageBox.critical(self, "Error", "Passwords don't match. Try again.")
                continue

            if len(password) < 8:
                QMessageBox.warning(
                    self,
                    "Weak Password",
                    "Master password should be at least 8 characters.",
                )
                continue

            # Initialize master password
            if self.crypto.initialize_master_password(password):
                self.authenticated = True
                self.status_label.setText("Authenticated")
                self.status_label.setStyleSheet(
                    "background-color: #27ae60; color: white;"
                )
                self.statusBar().showMessage("Authenticated")
                self.refresh_entries()
                QMessageBox.information(
                    self, "Success", "Master password set successfully!"
                )
                break
            else:
                QMessageBox.critical(self, "Error", "Failed to set master password.")
                self.close()
                return

    def authenticate(self):
        """Authenticate with master password."""
        if self.authenticated:
            QMessageBox.information(self, "Info", "Already authenticated.")
            return

        password, ok = QInputDialog.getText(
            self, "Authentication", "Enter master password:", QLineEdit.Password
        )

        if not ok or not password:
            return

        if self.crypto.authenticate(password):
            self.authenticated = True
            self.status_label.setText("Authenticated")
            self.status_label.setStyleSheet("background-color: #27ae60; color: white;")
            self.statusBar().showMessage("Authenticated")
            self.refresh_entries()
            QMessageBox.information(self, "Success", "Authentication successful!")
        else:
            QMessageBox.critical(self, "Error", "Authentication failed!")

    def add_entry(self):
        """Add a new password entry."""
        if not self.authenticated:
            QMessageBox.critical(self, "Error", "Please authenticate first.")
            return

        # Get values from input fields
        service = self.service_input.text().strip()
        username = self.username_input.text().strip()
        email = self.email_input.text().strip()
        password = self.password_input.text()
        notes = self.notes_input.toPlainText().strip()

        # Validate
        if not username:
            QMessageBox.critical(self, "Error", "Username is required.")
            return

        if not password:
            # Generate password if empty
            password = self.password_gen.generate_password()
            self.password_input.setText(password)
            self.update_strength_indicator()

        # Check if entry already exists
        if self.db.entry_exists(service if service else None, username):
            reply = QMessageBox.question(
                self,
                "Confirm",
                "Entry already exists. Overwrite?",
                QMessageBox.Yes | QMessageBox.No,
            )
            if reply == QMessageBox.No:
                return

        # Encrypt and save
        try:
            encrypted_password = self.crypto.encrypt_password(password)
            if self.db.add_entry(
                service if service else None,
                username,
                encrypted_password,
                email if email else None,
                notes if notes else None,
            ):
                QMessageBox.information(self, "Success", "Entry added successfully!")
                self.clear_entry_fields()
                self.refresh_entries()
                self.update_statistics()
            else:
                QMessageBox.critical(self, "Error", "Failed to add entry.")
        except Exception as e:
            logger.error(f"Error adding entry: {e}")
            QMessageBox.critical(self, "Error", f"Failed to add entry: {str(e)}")

    def update_entry(self):
        """Update selected entry."""
        if not self.authenticated:
            QMessageBox.critical(self, "Error", "Please authenticate first.")
            return

        selected_rows = self.entries_table.selectedItems()
        if not selected_rows:
            QMessageBox.critical(self, "Error", "No entry selected.")
            return

        # Get display ID from first column of selected row
        row = selected_rows[0].row()
        display_id = int(self.entries_table.item(row, 0).text())

        # Get actual ID from mapping
        actual_id = self.id_mapping.get(display_id)
        if not actual_id:
            QMessageBox.critical(self, "Error", "Invalid entry selected.")
            return

        # Get current values
        service = self.service_input.text().strip()
        username = self.username_input.text().strip()
        email = self.email_input.text().strip()
        password = self.password_input.text()
        notes = self.notes_input.toPlainText().strip()

        # Validate
        if not username:
            QMessageBox.critical(self, "Error", "Username is required.")
            return

        if not password:
            QMessageBox.critical(self, "Error", "Password is required.")
            return

        # Update entry
        try:
            encrypted_password = self.crypto.encrypt_password(password)
            if self.db.update_entry(
                actual_id,
                service if service else None,
                username,
                encrypted_password,
                email if email else None,
                notes if notes else None,
            ):
                QMessageBox.information(self, "Success", "Entry updated successfully!")
                self.refresh_entries()
                self.update_statistics()
            else:
                QMessageBox.critical(self, "Error", "Failed to update entry.")
        except Exception as e:
            logger.error(f"Error updating entry: {e}")
            QMessageBox.critical(self, "Error", f"Failed to update entry: {str(e)}")

    def delete_entry(self):
        """Delete selected entry."""
        if not self.authenticated:
            QMessageBox.critical(self, "Error", "Please authenticate first.")
            return

        selected_rows = self.entries_table.selectedItems()
        if not selected_rows:
            QMessageBox.critical(self, "Error", "No entry selected.")
            return

        # Get entry info for confirmation
        row = selected_rows[0].row()
        service = self.entries_table.item(row, 1).text()
        username = self.entries_table.item(row, 2).text()
        display_id = int(self.entries_table.item(row, 0).text())

        # Get actual ID from mapping
        actual_id = self.id_mapping.get(display_id)
        if not actual_id:
            QMessageBox.critical(self, "Error", "Invalid entry selected.")
            return

        # Confirm deletion
        confirm_msg = f"Delete entry for {username}"
        if service:
            confirm_msg += f" ({service})"
        confirm_msg += "?"

        reply = QMessageBox.question(
            self, "Confirm Deletion", confirm_msg, QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            if self.db.delete_entry(actual_id):
                QMessageBox.information(self, "Success", "Entry deleted successfully!")
                self.clear_entry_fields()
                self.refresh_entries()
                self.update_statistics()
            else:
                QMessageBox.critical(self, "Error", "Failed to delete entry.")

    def copy_password(self):
        """Copy password to clipboard."""
        if not self.authenticated:
            QMessageBox.critical(self, "Error", "Please authenticate first.")
            return

        password = self.password_input.text()
        if not password:
            QMessageBox.critical(self, "Error", "No password to copy.")
            return

        try:
            pyperclip.copy(password)
            QMessageBox.information(self, "Success", "Password copied to clipboard!")
        except Exception as e:
            logger.error(f"Error copying to clipboard: {e}")
            QMessageBox.critical(self, "Error", f"Failed to copy: {str(e)}")

    def show_generator(self):
        """Show password generator dialog."""
        dialog = PasswordGeneratorDialog(self, self.password_gen, self.button_images)
        # Update dialog dark mode state
        dialog.dark_mode = self.dark_mode
        if self.dark_mode:
            dialog.apply_dark_theme()
        else:
            dialog.apply_light_theme()
        if dialog.exec_() == QDialog.Accepted and dialog.generated_password:
            self.password_input.setText(dialog.generated_password)
            self.update_strength_indicator()

    def refresh_entries(self):
        """Refresh the entries list with sequential IDs."""
        if not self.authenticated:
            self.entries_table.setRowCount(0)
            return

        # Clear current items
        self.entries_table.setRowCount(0)
        self.id_mapping.clear()

        # Get all entries
        entries = self.db.get_all_entries()

        # Set row count
        self.entries_table.setRowCount(len(entries))

        # Display with sequential numbering
        for i, entry in enumerate(entries):
            # Store mapping (display ID -> actual ID)
            display_id = i + 1
            self.id_mapping[display_id] = entry["id"]

            # Format date in readable format
            try:
                created_date = datetime.fromisoformat(entry["created_at"])
                formatted_date = created_date.strftime("%d %B %Y, %I:%M %p")
            except:
                formatted_date = entry["created_at"]

            # Add items to table with styling
            self.entries_table.setItem(i, 0, QTableWidgetItem(str(display_id)))
            self.entries_table.setItem(
                i, 1, QTableWidgetItem(entry["service"] or "N/A")
            )
            self.entries_table.setItem(i, 2, QTableWidgetItem(entry["username"]))
            self.entries_table.setItem(i, 3, QTableWidgetItem(entry["email"] or "N/A"))
            self.entries_table.setItem(i, 4, QTableWidgetItem(formatted_date))

            # Color code based on service availability
            if not entry["service"]:
                self.entries_table.item(i, 1).setForeground(QColor("#7f8c8d"))

    def on_entry_select(self):
        """Handle entry selection in table."""
        if not self.authenticated:
            return

        selected_rows = self.entries_table.selectedItems()
        if not selected_rows:
            return

        # Get display ID from first column of selected row
        row = selected_rows[0].row()
        display_id = int(self.entries_table.item(row, 0).text())

        # Get actual ID from mapping
        actual_id = self.id_mapping.get(display_id)
        if not actual_id:
            return

        # Get entry from database
        entry = self.db.get_entry(actual_id)
        if entry:
            # Decrypt password
            try:
                decrypted_password = self.crypto.decrypt_password(entry["password"])
                self.service_input.setText(entry["service"] or "")
                self.username_input.setText(entry["username"])
                self.email_input.setText(entry["email"] or "")
                self.password_input.setText(decrypted_password)
                self.notes_input.setPlainText(entry["notes"] or "")
                self.update_strength_indicator()
            except Exception as e:
                logger.error(f"Error decrypting password: {e}")
                QMessageBox.critical(self, "Error", "Failed to decrypt password.")
                self.clear_entry_fields()

    def on_search(self):
        """Handle search functionality."""
        if not self.authenticated:
            return

        search_term = self.search_input.text().strip().lower()

        if not search_term:
            # Show all entries if search is empty
            self.refresh_entries()
            return

        # Get all entries
        all_entries = self.db.get_all_entries()
        filtered_entries = []

        for entry in all_entries:
            if (
                search_term in (entry["service"] or "").lower()
                or search_term in entry["username"].lower()
                or search_term in (entry["email"] or "").lower()
            ):
                filtered_entries.append(entry)

        # Display filtered entries
        self.entries_table.setRowCount(len(filtered_entries))
        self.id_mapping.clear()

        for i, entry in enumerate(filtered_entries):
            display_id = i + 1
            self.id_mapping[display_id] = entry["id"]

            # Format date in readable format
            try:
                created_date = datetime.fromisoformat(entry["created_at"])
                formatted_date = created_date.strftime("%d %B %Y, %I:%M %p")
            except:
                formatted_date = entry["created_at"]

            self.entries_table.setItem(i, 0, QTableWidgetItem(str(display_id)))
            self.entries_table.setItem(
                i, 1, QTableWidgetItem(entry["service"] or "N/A")
            )
            self.entries_table.setItem(i, 2, QTableWidgetItem(entry["username"]))
            self.entries_table.setItem(i, 3, QTableWidgetItem(entry["email"] or "N/A"))
            self.entries_table.setItem(i, 4, QTableWidgetItem(formatted_date))

    def clear_entry_fields(self):
        """Clear all entry fields."""
        self.service_input.clear()
        self.username_input.clear()
        self.email_input.clear()
        self.password_input.clear()
        self.notes_input.clear()
        self.strength_label.clear()
        self.strength_label.setStyleSheet("")

    def toggle_password_visibility(self, checked):
        """Toggle password visibility."""
        if checked:
            self.password_input.setEchoMode(QLineEdit.Normal)
            if "hide" in self.button_images:
                self.show_password_btn.setIcon(self.button_images["hide"])
                self.show_password_btn.setToolTip("Hide Password")
            else:
                self.show_password_btn.setText("")
                self.show_password_btn.setToolTip("Hide Password")
        else:
            self.password_input.setEchoMode(QLineEdit.Password)
            if "show" in self.button_images:
                self.show_password_btn.setIcon(self.button_images["show"])
                self.show_password_btn.setToolTip("Show Password")
            else:
                self.show_password_btn.setText("")
                self.show_password_btn.setToolTip("Show Password")

    def update_strength_indicator(self):
        """Update password strength indicator."""
        password = self.password_input.text()
        if password:
            evaluation = self.password_gen.evaluate_strength(password)

            color_map = {
                "Very Weak": ("#e74c3c", ""),
                "Weak": ("#e67e22", ""),
                "Moderate": ("#f1c40f", ""),
                "Strong": ("#2ecc71", ""),
                "Very Strong": ("#27ae60", ""),
            }

            color, icon = color_map.get(evaluation["strength"], ("#333", ""))
            strength_text = (
                f"{icon} {evaluation['strength']} ({evaluation['entropy']:.1f} bits)"
            )

            self.strength_label.setText(strength_text)
            self.strength_label.setStyleSheet(
                f"""
                background-color: {color}15;
                color: {color};
                border: 1px solid {color}30;
                font-weight: bold;
            """
            )
        else:
            self.strength_label.clear()
            self.strength_label.setStyleSheet("")

    def change_master_password(self):
        """Change master password."""
        if not self.authenticated:
            QMessageBox.critical(self, "Error", "Please authenticate first.")
            return

        old_password, ok = QInputDialog.getText(
            self,
            "Change Master Password",
            "Enter current master password:",
            QLineEdit.Password,
        )

        if not ok or not old_password:
            return

        # Verify current password
        if not self.crypto.authenticate(old_password):
            QMessageBox.critical(self, "Error", "Current password is incorrect.")
            return

        new_password, ok = QInputDialog.getText(
            self,
            "Change Master Password",
            "Enter new master password:",
            QLineEdit.Password,
        )

        if not ok or not new_password:
            return

        if len(new_password) < 8:
            QMessageBox.critical(
                self, "Error", "New password must be at least 8 characters."
            )
            return

        confirm, ok = QInputDialog.getText(
            self,
            "Change Master Password",
            "Confirm new master password:",
            QLineEdit.Password,
        )

        if not ok or new_password != confirm:
            QMessageBox.critical(self, "Error", "Passwords don't match.")
            return

        # Change master password
        if self.crypto.change_master_password(old_password, new_password):
            QMessageBox.information(
                self, "Success", "Master password changed successfully!"
            )
        else:
            QMessageBox.critical(self, "Error", "Failed to change master password.")

    def export_passwords(self):
        """Export passwords to an encrypted file."""
        if not self.authenticated:
            QMessageBox.critical(self, "Error", "Please authenticate first.")
            return

        # Get all entries
        entries = self.db.get_all_entries()
        if not entries:
            QMessageBox.information(self, "Info", "No entries to export.")
            return

        # Decrypt all passwords for export
        export_data = []
        for entry in entries:
            try:
                decrypted_password = self.crypto.decrypt_password(entry["password"])
                export_data.append(
                    {
                        "service": entry["service"],
                        "username": entry["username"],
                        "password": decrypted_password,
                        "email": entry["email"],
                        "notes": entry["notes"],
                        "created_at": entry["created_at"],
                    }
                )
            except Exception as e:
                logger.error(f"Error decrypting entry for export: {e}")
                QMessageBox.critical(
                    self,
                    "Error",
                    f"Failed to decrypt entry {entry['id']}. Export cancelled.",
                )
                return

        # Ask for export password
        export_password, ok = QInputDialog.getText(
            self,
            "Export Passwords",
            "Enter password to encrypt export file:\n(This can be different from your master password)",
            QLineEdit.Password,
        )

        if not ok or not export_password:
            return

        if len(export_password) < 6:
            QMessageBox.critical(
                self, "Error", "Export password must be at least 6 characters."
            )
            return

        confirm_password, ok = QInputDialog.getText(
            self,
            "Confirm Export Password",
            "Confirm export password:",
            QLineEdit.Password,
        )

        if not ok or export_password != confirm_password:
            QMessageBox.critical(self, "Error", "Passwords don't match.")
            return

        # Ask for save location
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save export file",
            "password_export.enc",
            "Encrypted files (*.enc);;All files (*.*)",
        )

        if not file_path:
            return

        try:
            # Create export package
            export_package = {
                "metadata": {
                    "export_date": datetime.now().isoformat(),
                    "total_entries": len(export_data),
                    "app_version": "1.0",
                },
                "entries": export_data,
            }

            # Encrypt export data
            encrypted_package = self.crypto.export_data_with_password(
                export_package, export_password
            )

            # Save to file
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(encrypted_package, f, indent=2)

            QMessageBox.information(
                self,
                "Success",
                f"Successfully exported {len(export_data)} entries to:\n{file_path}\n\n"
                "Remember your export password to import this file later!",
            )

        except Exception as e:
            logger.error(f"Error exporting passwords: {e}")
            QMessageBox.critical(self, "Error", f"Export failed: {str(e)}")

    def export_to_pdf(self):
        """Export all entries to a well-decorated PDF file."""
        if not self.authenticated:
            QMessageBox.critical(self, "Error", "Please authenticate first.")
            return

        # Get all entries
        entries = self.db.get_all_entries()
        if not entries:
            QMessageBox.information(
                self, "Info", "No entries to export. Please add entries first!"
            )
            return

        # Ask for save location
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export to PDF",
            "password_manager_report.pdf",
            "PDF files (*.pdf);;All files (*.*)",
        )

        if not file_path:
            return

        try:
            # Create PDF
            self.create_pdf_report(file_path, entries)

            # Show success message
            msg = QMessageBox(self)
            msg.setWindowTitle("PDF Export Successful")
            msg.setText(f"Successfully exported {len(entries)} entries to PDF!")
            msg.setInformativeText(f"File saved to:\n{file_path}")
            msg.setIcon(QMessageBox.Information)
            msg.exec_()

        except Exception as e:
            logger.error(f"Error exporting to PDF: {e}")
            QMessageBox.critical(self, "Error", f"Failed to export PDF: {str(e)}")

    def create_pdf_report(self, file_path, entries):
        """Create a beautifully formatted PDF report."""
        from reportlab.lib.styles import getSampleStyleSheet

        # Create document
        doc = SimpleDocTemplate(
            file_path,
            pagesize=A4,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=72,
        )

        # Create styles
        styles = getSampleStyleSheet()

        # Custom styles
        title_style = ParagraphStyle(
            "CustomTitle",
            parent=styles["Title"],
            fontSize=24,
            textColor=colors.HexColor("#2c3e50"),
            spaceAfter=30,
            alignment=1,  # Center
        )

        header_style = ParagraphStyle(
            "CustomHeader",
            parent=styles["Heading2"],
            fontSize=14,
            textColor=colors.HexColor("#2c3e50"),
            spaceAfter=12,
        )

        normal_style = ParagraphStyle(
            "CustomNormal",
            parent=styles["Normal"],
            fontSize=10,
            textColor=colors.HexColor("#333333"),
        )

        # Create story (content)
        story = []

        # Title
        story.append(Paragraph(PDF_EXPORT_TITLE, title_style))
        story.append(Spacer(1, 20))

        # Report information
        report_date = datetime.now().strftime("%d %B %Y, %I:%M %p")
        
        # Create Paragraph objects for text wrapping
        info_data = [
            [Paragraph("<b>Report Date:</b>", normal_style), Paragraph(report_date, normal_style)],
            [Paragraph("<b>Total Entries:</b>", normal_style), Paragraph(str(len(entries)), normal_style)],
            [Paragraph("<b>Generated By:</b>", normal_style), Paragraph(PDF_AUTHOR, normal_style)],
            [Paragraph("<b>Application:</b>", normal_style), Paragraph(f"{APP_NAME}", normal_style)],
        ]

        info_table = Table(info_data, colWidths=[2.2 * inch, 3.8 * inch])
        info_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f8f9fa")),
                    ("BACKGROUND", (1, 0), (1, -1), colors.white),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("FONTSIZE", (0, 0), (-1, -1), 10),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                    ("TOPPADDING", (0, 0), (-1, -1), 8),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                    ("GRID", (0, 0), (-1, -1), 1, colors.HexColor("#dee2e6")),
                ]
            )
        )

        story.append(info_table)
        story.append(Spacer(1, 30))

        # Entries table
        story.append(Paragraph("Password Entries", header_style))
        story.append(Spacer(1, 10))

        # Prepare table data with Paragraph objects for text wrapping
        header_style_bold = ParagraphStyle(
            "TableHeader",
            parent=normal_style,
            fontSize=11,
            textColor=colors.white,
            fontName="Helvetica-Bold",
            alignment=1,  # Center
        )
        
        cell_style = ParagraphStyle(
            "TableCell",
            parent=normal_style,
            fontSize=9,
            textColor=colors.HexColor("#333333"),
            alignment=0,  # Left
        )
        
        cell_style_center = ParagraphStyle(
            "TableCellCenter",
            parent=normal_style,
            fontSize=9,
            textColor=colors.HexColor("#333333"),
            alignment=1,  # Center
        )
        
        table_data = [
            [
                Paragraph("<b>ID</b>", header_style_bold),
                Paragraph("<b>Service</b>", header_style_bold),
                Paragraph("<b>Username</b>", header_style_bold),
                Paragraph("<b>Email</b>", header_style_bold),
                Paragraph("<b>Password</b>", header_style_bold),
                Paragraph("<b>Created</b>", header_style_bold),
            ]
        ]

        for i, entry in enumerate(entries):
            # Format date in readable format
            try:
                created_date = datetime.fromisoformat(entry["created_at"])
                formatted_date = created_date.strftime("%d %B %Y")
            except:
                formatted_date = entry["created_at"]
            
            # Decrypt password
            try:
                decrypted_password = self.crypto.decrypt_password(entry["password"])
            except Exception as e:
                logger.error(f"Error decrypting password for entry {entry['id']}: {e}")
                decrypted_password = "***DECRYPTION_ERROR***"

            table_data.append(
                [
                    Paragraph(str(i + 1), cell_style_center),
                    Paragraph(entry["service"] or "N/A", cell_style),
                    Paragraph(entry["username"], cell_style),
                    Paragraph(entry["email"] or "N/A", cell_style),
                    Paragraph(decrypted_password, cell_style),
                    Paragraph(formatted_date, cell_style),
                ]
            )

        # Create table with adjusted column widths
        table = Table(
            table_data,
            colWidths=[0.4 * inch, 1.0 * inch, 1.0 * inch, 1.2 * inch, 1.3 * inch, 0.9 * inch],
        )

        # Build table style dynamically to avoid index errors
        table_style = [
            # Header style
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c3e50")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ALIGN", (0, 0), (-1, 0), "CENTER"),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
            ("TOPPADDING", (0, 0), (-1, 0), 8),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            # Text style for all data rows
            ("ALIGN", (0, 1), (-1, -1), "LEFT"),
            ("ALIGN", (0, 1), (0, -1), "CENTER"),
            ("BOTTOMPADDING", (0, 1), (-1, -1), 8),
            ("TOPPADDING", (0, 1), (-1, -1), 8),
            # Grid
            ("GRID", (0, 0), (-1, -1), 1, colors.HexColor("#dee2e6")),
            ("BOX", (0, 0), (-1, -1), 2, colors.HexColor("#2c3e50")),
        ]

        # Add alternating row colors for existing rows only
        num_rows = len(table_data)
        for i in range(1, num_rows):
            if i % 2 == 0:  # Even rows (2, 4, 6, etc.)
                if i < num_rows:
                    table_style.append(
                        ("BACKGROUND", (0, i), (-1, i), colors.HexColor("#f8f9fa"))
                    )

        table.setStyle(TableStyle(table_style))

        story.append(table)
        story.append(Spacer(1, 30))

        # Statistics
        story.append(Paragraph("Statistics", header_style))
        story.append(Spacer(1, 10))

        stats = self.db.get_statistics()
        
        # Format latest entry date
        latest_entry_formatted = "N/A"
        if stats["latest_entry"]:
            try:
                latest_date = datetime.fromisoformat(stats["latest_entry"])
                latest_entry_formatted = latest_date.strftime("%d %B %Y, %I:%M %p")
            except:
                latest_entry_formatted = stats["latest_entry"]
        
        # Create Paragraph objects for text wrapping
        stats_data = [
            [Paragraph("<b>Total Entries:</b>", normal_style), Paragraph(str(stats["total_entries"]), normal_style)],
            [Paragraph("<b>Entries with Email:</b>", normal_style), Paragraph(str(stats["entries_with_email"]), normal_style)],
            [Paragraph("<b>Entries with Notes:</b>", normal_style), Paragraph(str(stats["entries_with_notes"]), normal_style)],
            [Paragraph("<b>Latest Entry:</b>", normal_style), Paragraph(latest_entry_formatted, normal_style)],
        ]

        stats_table = Table(stats_data, colWidths=[2.2 * inch, 3.8 * inch])
        stats_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#3498db15")),
                    ("BACKGROUND", (1, 0), (1, -1), colors.white),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("FONTSIZE", (0, 0), (-1, -1), 10),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                    ("TOPPADDING", (0, 0), (-1, -1), 8),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                    ("GRID", (0, 0), (-1, -1), 1, colors.HexColor("#dee2e6")),
                ]
            )
        )

        story.append(stats_table)
        story.append(Spacer(1, 40))

        # Footer note
        footer_text = f"""
        <para alignment="center">
        <font size="8" color="#7f8c8d">
        {PDF_FOOTER_TEXT}<br/>
        This document contains sensitive information. Please keep it secure.<br/>
        Generated on {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
        </font>
        </para>
        """

        story.append(Paragraph(footer_text, normal_style))

        # Build PDF
        doc.build(story)

    def import_passwords(self):
        """Import passwords from an encrypted file."""
        if not self.authenticated:
            QMessageBox.critical(self, "Error", "Please authenticate first.")
            return

        # Ask for file location
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select export file to import",
            "",
            "Encrypted files (*.enc);;JSON files (*.json);;All files (*.*)",
        )

        if not file_path or not os.path.exists(file_path):
            return

        # Ask for import password
        import_password, ok = QInputDialog.getText(
            self,
            "Import Passwords",
            "Enter password used to encrypt this file:",
            QLineEdit.Password,
        )

        if not ok or not import_password:
            return

        try:
            # Load encrypted package
            with open(file_path, "r", encoding="utf-8") as f:
                encrypted_package = json.load(f)

            # Decrypt data
            decrypted_data = self.crypto.import_data_with_password(
                encrypted_package, import_password
            )

            # Validate data structure
            if "entries" not in decrypted_data:
                raise ValueError("Invalid export file format")

            entries = decrypted_data["entries"]

            if not entries:
                QMessageBox.information(
                    self, "Info", "No entries found in import file."
                )
                return

            # Show import preview
            preview_dialog = QDialog(self)
            preview_dialog.setWindowTitle("Import Preview")
            preview_dialog.setMinimumWidth(500)

            layout = QVBoxLayout(preview_dialog)

            # Preview text
            preview_text = QLabel(f"Found {len(entries)} entries in import file:")
            layout.addWidget(preview_text)

            # Preview list
            preview_list = QListWidget()
            for i, entry in enumerate(entries[:10], 1):
                service = entry.get("service", "(no service)")
                preview_list.addItem(f"{i}. {service} - {entry['username']}")

            if len(entries) > 10:
                preview_list.addItem(f"... and {len(entries) - 10} more entries")

            layout.addWidget(preview_list)

            # Import options
            options_group = QGroupBox("Import Options")
            options_layout = QVBoxLayout()

            skip_radio = QRadioButton("Skip duplicates")
            overwrite_radio = QRadioButton("Overwrite duplicates")
            skip_radio.setChecked(True)

            options_layout.addWidget(skip_radio)
            options_layout.addWidget(overwrite_radio)
            options_group.setLayout(options_layout)
            layout.addWidget(options_group)

            # Buttons
            button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
            button_box.accepted.connect(preview_dialog.accept)
            button_box.rejected.connect(preview_dialog.reject)
            layout.addWidget(button_box)

            if preview_dialog.exec_() != QDialog.Accepted:
                return

            skip_duplicates = skip_radio.isChecked()

            # Import entries
            imported_count = 0
            skipped_count = 0
            failed_count = 0

            progress = QProgressDialog(
                "Importing entries...", "Cancel", 0, len(entries), self
            )
            progress.setWindowTitle("Import Progress")
            progress.setWindowModality(Qt.WindowModal)
            progress.setMinimumDuration(0)

            for i, entry in enumerate(entries):
                if progress.wasCanceled():
                    break

                progress.setValue(i)
                progress.setLabelText(f"Importing entry {i+1} of {len(entries)}...")
                QApplication.processEvents()

                service = entry.get("service")
                username = entry["username"]
                password = entry["password"]
                email = entry.get("email")
                notes = entry.get("notes")

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
                            if (
                                db_entry["service"] == service
                                and db_entry["username"] == username
                            ):
                                self.db.update_entry(
                                    db_entry["id"],
                                    service,
                                    username,
                                    encrypted_password,
                                    email,
                                    notes,
                                )
                                imported_count += 1
                                break
                    else:
                        # Add new entry
                        if self.db.add_entry(
                            service, username, encrypted_password, email, notes
                        ):
                            imported_count += 1
                        else:
                            failed_count += 1

                except Exception as e:
                    logger.error(f"Error importing entry {username}: {e}")
                    failed_count += 1

            progress.close()

            # Show results
            result_message = f"""
            <h3>Import Results</h3>
            <p><b>Imported:</b> {imported_count} entries</p>
            <p><b>Skipped:</b> {skipped_count} duplicates</p>
            <p><b>Failed:</b> {failed_count} entries</p>
            """

            result_dialog = QMessageBox(self)
            result_dialog.setWindowTitle("Import Complete")
            result_dialog.setTextFormat(Qt.RichText)
            result_dialog.setText(result_message)
            result_dialog.setIcon(QMessageBox.Information)
            result_dialog.exec_()

            # Refresh entries list
            self.refresh_entries()
            self.update_statistics()

        except ValueError as e:
            QMessageBox.critical(
                self,
                "Import Error",
                f"Failed to import: {str(e)}\n\n"
                "Possible causes:\n"
                "- Incorrect password\n"
                "- Corrupted export file\n"
                "- Invalid file format",
            )
        except Exception as e:
            logger.error(f"Error importing passwords: {e}")
            QMessageBox.critical(self, "Error", f"Import failed: {str(e)}")


class PasswordGeneratorDialog(QDialog):
    """Dialog for generating passwords."""

    def __init__(self, parent, password_gen, button_images=None):
        """Initialize password generator dialog."""
        super().__init__(parent)
        self.password_gen = password_gen
        self.button_images = button_images or {}
        self.generated_password = None
        self.dark_mode = parent.dark_mode if hasattr(parent, 'dark_mode') else False

        self.init_ui()
        self.generate_password()

    def apply_dark_theme(self):
        """Apply dark theme to dialog."""
        self.dark_mode = True
        self.setStyleSheet(self.get_dark_stylesheet())
    
    def apply_light_theme(self):
        """Apply light theme to dialog."""
        self.dark_mode = False
        self.setStyleSheet(self.get_light_stylesheet())
    
    def get_dark_stylesheet(self):
        """Get dark theme stylesheet."""
        return """
            QDialog {
                background-color: #1e1e1e;
                border-radius: 10px;
            }
            
            QLabel {
                color: #e0e0e0;
            }
            
            QCheckBox {
                color: #e0e0e0;
            }
            
            QGroupBox {
                font-weight: bold;
                border: 2px solid #444;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
                color: #e0e0e0;
            }
            
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: #e0e0e0;
            }
            
            QSlider::groove:horizontal {
                height: 6px;
                background: #444;
                border-radius: 3px;
            }
            
            QSlider::handle:horizontal {
                background: #5DADE2;
                width: 20px;
                height: 20px;
                margin: -7px 0;
                border-radius: 10px;
            }
            
            QPushButton {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #5DADE2, stop: 1 #2E86C1);
                color: white;
                padding: 10px 20px;
                border-radius: 6px;
                font-weight: bold;
                border: none;
            }
            
            QPushButton:hover {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #2E86C1, stop: 1 #1B4965);
            }
            """
    
    def get_light_stylesheet(self):
        """Get light theme stylesheet."""
        return """
            QDialog {
                background-color: white;
                border-radius: 10px;
            }
            
            QLabel {
                color: #333333;
            }
            
            QCheckBox {
                color: #333333;
            }
            
            QGroupBox {
                font-weight: bold;
                border: 2px solid #dee2e6;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
                color: #333333;
            }
            
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: #333333;
            }
            
            QSlider::groove:horizontal {
                height: 6px;
                background: #dee2e6;
                border-radius: 3px;
            }
            
            QSlider::handle:horizontal {
                background: #3498db;
                width: 20px;
                height: 20px;
                margin: -7px 0;
                border-radius: 10px;
            }
            
            QPushButton {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #5DADE2, stop: 1 #2E86C1);
                color: white;
                padding: 10px 20px;
                border-radius: 6px;
                font-weight: bold;
                border: none;
            }
            
            QPushButton:hover {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #2E86C1, stop: 1 #1B4965);
            }
            """
    
    def init_ui(self):
        """Initialize the dialog UI."""
        self.setWindowTitle("Password Generator")
        self.setMinimumWidth(450)
        
        # Set stylesheet based on theme
        if self.dark_mode:
            self.setStyleSheet(self.get_dark_stylesheet())
        else:
            self.setStyleSheet(self.get_light_stylesheet())

        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        # Length control
        length_group = QGroupBox("Password Length")
        length_layout = QHBoxLayout(length_group)

        self.length_slider = QSlider(Qt.Horizontal)
        self.length_slider.setRange(8, 50)
        self.length_slider.setValue(20)
        self.length_slider.valueChanged.connect(self.generate_password)
        length_layout.addWidget(self.length_slider, 1)

        self.length_label = QLabel("20")
        self.length_label.setMinimumWidth(30)
        self.length_label.setAlignment(Qt.AlignCenter)
        
        # Set length label style based on theme
        if self.dark_mode:
            length_label_style = """
            font-weight: bold;
            font-size: 14px;
            color: #2ECC71;
        """
        else:
            length_label_style = """
            font-weight: bold;
            font-size: 14px;
            color: #2c3e50;
        """
        
        self.length_label.setStyleSheet(length_label_style)
        length_layout.addWidget(self.length_label)

        layout.addWidget(length_group)

        # Character types
        types_group = QGroupBox("Character Types")
        types_layout = QVBoxLayout(types_group)

        self.lower_check = QCheckBox("Lowercase (a-z)")
        self.lower_check.setChecked(True)
        self.lower_check.stateChanged.connect(self.generate_password)
        types_layout.addWidget(self.lower_check)

        self.upper_check = QCheckBox("Uppercase (A-Z)")
        self.upper_check.setChecked(True)
        self.upper_check.stateChanged.connect(self.generate_password)
        types_layout.addWidget(self.upper_check)

        self.digits_check = QCheckBox("Digits (0-9)")
        self.digits_check.setChecked(True)
        self.digits_check.stateChanged.connect(self.generate_password)
        types_layout.addWidget(self.digits_check)

        self.symbols_check = QCheckBox("Symbols (!@#$%^&*)")
        self.symbols_check.setChecked(True)
        self.symbols_check.stateChanged.connect(self.generate_password)
        types_layout.addWidget(self.symbols_check)

        layout.addWidget(types_group)

        # Generated password
        password_group = QGroupBox("Generated Password")
        password_layout = QVBoxLayout(password_group)

        self.password_display = QLineEdit()
        self.password_display.setReadOnly(True)
        
        # Set password display style based on theme
        if self.dark_mode:
            password_style = """
            font-family: 'Courier New', monospace;
            font-size: 14px;
            font-weight: bold;
            padding: 10px;
            border: 2px solid #444;
            border-radius: 6px;
            background-color: #2d2d2d;
            color: #2ECC71;
        """
        else:
            password_style = """
            font-family: 'Courier New', monospace;
            font-size: 14px;
            font-weight: bold;
            padding: 10px;
            border: 2px solid #dee2e6;
            border-radius: 6px;
            background-color: #f8f9fa;
            color: #2c3e50;
        """
        
        self.password_display.setStyleSheet(password_style)
        password_layout.addWidget(self.password_display)

        # Entropy display
        self.entropy_label = QLabel()
        self.entropy_label.setAlignment(Qt.AlignCenter)
        
        # Set entropy label style based on theme
        if self.dark_mode:
            entropy_style = """
            font-size: 12px;
            color: #3498db;
            padding: 5px;
        """
        else:
            entropy_style = """
            font-size: 12px;
            color: #7f8c8d;
            padding: 5px;
        """
        
        self.entropy_label.setStyleSheet(entropy_style)
        password_layout.addWidget(self.entropy_label)

        layout.addWidget(password_group)

        # Buttons
        button_layout = QHBoxLayout()

        generate_btn = QPushButton("Generate New")
        generate_btn.clicked.connect(self.generate_password)
        generate_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #3498db;
                color: white;
                padding: 8px 15px;
                border-radius: 6px;
                font-weight: normal;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """
        )
        button_layout.addWidget(generate_btn)

        copy_btn = QPushButton("Copy")
        copy_btn.clicked.connect(self.copy_password)
        copy_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #27ae60;
                color: white;
                padding: 8px 15px;
                border-radius: 6px;
                font-weight: normal;
            }
            QPushButton:hover {
                background-color: #229954;
            }
        """
        )
        button_layout.addWidget(copy_btn)

        use_btn = QPushButton("Use This Password")
        use_btn.clicked.connect(self.use_password)
        use_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #f39c12;
                color: white;
                padding: 8px 15px;
                border-radius: 6px;
                font-weight: normal;
            }
            QPushButton:hover {
                background-color: #d68910;
            }
        """
        )
        button_layout.addWidget(use_btn)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        cancel_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #e74c3c;
                color: white;
                padding: 8px 15px;
                border-radius: 6px;
                font-weight: normal;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
        """
        )
        button_layout.addWidget(cancel_btn)

        layout.addLayout(button_layout)

    def generate_password(self):
        """Generate a new password."""
        self.length_label.setText(str(self.length_slider.value()))

        try:
            password = self.password_gen.generate_password(
                length=self.length_slider.value(),
                include_lowercase=self.lower_check.isChecked(),
                include_uppercase=self.upper_check.isChecked(),
                include_digits=self.digits_check.isChecked(),
                include_symbols=self.symbols_check.isChecked(),
            )
            self.password_display.setText(password)

            # Calculate and display entropy
            entropy = self.password_gen.calculate_entropy(password)
            strength = self.password_gen.evaluate_strength(password)

            color_map = {
                "Very Weak": "#e74c3c",
                "Weak": "#e67e22",
                "Moderate": "#f1c40f",
                "Strong": "#2ecc71",
                "Very Strong": "#27ae60",
            }

            color = color_map.get(strength["strength"], "#7f8c8d")
            self.entropy_label.setText(
                f"Strength: <b>{strength['strength']}</b> | "
                f"Entropy: <b>{entropy:.1f} bits</b>"
            )
            self.entropy_label.setStyleSheet(
                f"""
                font-size: 12px;
                color: {color};
                padding: 5px;
            """
            )

        except ValueError as e:
            QMessageBox.warning(self, "Error", str(e))

    def copy_password(self):
        """Copy generated password to clipboard."""
        password = self.password_display.text()
        if password:
            pyperclip.copy(password)
            QMessageBox.information(self, "Success", "Password copied to clipboard!")

    def use_password(self):
        """Use the generated password."""
        self.generated_password = self.password_display.text()
        self.accept()


def main():
    """Main function to run the GUI application."""
    # Configure logging
    logging.basicConfig(
        level=logging.WARNING,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Create and run application
    app = QApplication(sys.argv)

    # Set application style
    app.setStyle("Fusion")

    # Set application font
    font = QFont("Segoe UI", 10)
    app.setFont(font)

    # Create and show main window
    window = PasswordManagerGUI()
    window.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
