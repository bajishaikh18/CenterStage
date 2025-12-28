"""
Center Stage Camera - Entry Point

A professional AI-powered camera application with automatic face tracking
and Center Stage functionality.
"""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from src.ui.main_window import MainWindow
from src.utils.logger import setup_logger


def main():
    """Main application entry point."""
    # Setup logging
    logger = setup_logger()
    logger.info("Starting Center Stage Camera...")
    
    # Enable high DPI scaling
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    
    # Create application
    app = QApplication(sys.argv)
    app.setApplicationName("Center Stage")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("CenterStage")
    
    # Set application style
    app.setStyle("Fusion")
    
    # Create and show main window
    window = MainWindow()
    window.show()
    
    logger.info("Application ready")
    
    # Run event loop
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
