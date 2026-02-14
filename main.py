#!/usr/bin/env python3
"""
Sensor Analysis - Desktop Application
Main entry point for the PyQt6 application.

A standalone desktop application for visualizing camera sensor noise characteristics
from raw DNG/ERF files and aggregate analysis data.
"""

import sys
import os
from pathlib import Path

# Version tracking
VERSION = "0.1"


def _set_macos_app_name(name: str) -> None:
    """Set the application name in macOS menu bar and Dock tooltip."""
    try:
        from AppKit import NSApplication
        from Foundation import NSBundle

        # Get the shared application
        app = NSApplication.sharedApplication()

        # Modify the bundle info
        bundle = NSBundle.mainBundle()
        info = bundle.infoDictionary()
        info['CFBundleName'] = name
        info['CFBundleDisplayName'] = name
        info['CFBundleExecutable'] = name

        # Try to force Dock to update
        app.setActivationPolicy_(0)  # NSApplicationActivationPolicyRegular

    except ImportError:
        pass  # PyObjC not available


# Set macOS app name BEFORE any Qt imports
if sys.platform == 'darwin':
    _set_macos_app_name("Sensor Analysis")

# Add current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor, QFont

from views.main_window import MainWindow
from controllers.app_controller import AppController


def create_app_icon() -> QIcon:
    """
    Create application icon programmatically.

    Returns:
        QIcon for the application
    """
    # Create a 512x512 pixmap for high resolution
    pixmap = QPixmap(512, 512)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    # Draw gradient background circle
    from PyQt6.QtGui import QRadialGradient, QPen
    gradient = QRadialGradient(256, 256, 256)
    gradient.setColorAt(0, QColor(70, 130, 180))  # Steel blue
    gradient.setColorAt(1, QColor(25, 55, 100))   # Dark blue

    painter.setBrush(gradient)
    painter.setPen(QPen(QColor(40, 80, 140), 10))
    painter.drawEllipse(20, 20, 472, 472)

    # Draw camera sensor grid (simplified representation)
    painter.setPen(QPen(QColor(255, 255, 255, 180), 3))
    for i in range(3):
        for j in range(3):
            x = 140 + i * 90
            y = 140 + j * 90
            painter.drawRect(x, y, 70, 70)

    # Draw "S" letter
    font = QFont("Arial", 280, QFont.Weight.Bold)
    painter.setFont(font)
    painter.setPen(QColor(255, 255, 255, 230))
    painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "S")

    painter.end()

    return QIcon(pixmap)


def setup_application() -> QApplication:
    """
    Setup and configure the QApplication.

    Returns:
        QApplication instance
    """
    # Enable high DPI scaling
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    # Set application name BEFORE creating QApplication instance
    QApplication.setApplicationName("Sensor Analysis")

    app = QApplication(sys.argv)

    # Set application metadata
    app.setApplicationDisplayName("Sensor Analysis")
    app.setOrganizationName("Sensor Analysis")
    app.setApplicationVersion(VERSION)

    # Set application icon
    app_icon = create_app_icon()
    app.setWindowIcon(app_icon)

    return app


def check_dependencies() -> bool:
    """
    Check that required files and dependencies are available.

    Returns:
        True if all dependencies are met, False otherwise
    """
    # Note: Analysis data is now stored in SQLite database
    # Database will be created in working directory under db/analysis.db

    # Check for sensor_camera module
    try:
        import sensor_camera
    except ImportError:
        print("ERROR: sensor_camera.py module not found")
        print("Please ensure sensor_camera.py is in the current directory")
        return False

    # Check for required packages
    required_packages = [
        ('PyQt6', 'PyQt6'),
        ('PyQt6.QtWebEngineWidgets', 'PyQt6-WebEngine'),
        ('pandas', 'pandas'),
        ('numpy', 'numpy'),
        ('plotly', 'plotly'),
        ('rawpy', 'rawpy'),
        ('exiftool', 'PyExifTool'),
    ]

    missing_packages = []
    for package, pip_name in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(pip_name)

    if missing_packages:
        print("ERROR: Missing required packages:")
        for pkg in missing_packages:
            print(f"  - {pkg}")
        print("\nInstall missing packages with:")
        print(f"  pip install {' '.join(missing_packages)}")
        return False

    return True


def main():
    """Main entry point"""
    print(f"Sensor Analysis v{VERSION}")
    print("=" * 50)

    # Check dependencies
    if not check_dependencies():
        sys.exit(1)

    print("✓ All dependencies found")

    # Initialize configuration
    from utils.config_manager import get_config
    config = get_config()
    print(f"✓ Working directory: {config.get_working_dir()}")
    print(f"✓ Source directory: {config.get_source_dir()}")

    # Initialize logging
    from utils.app_logger import init_logger
    logger = init_logger(config.get_working_dir(), clear_on_start=True)
    logger.info("Sensor Analysis starting up")
    logger.info(f"Working directory: {config.get_working_dir()}")
    logger.info(f"Source directory: {config.get_source_dir()}")

    print("Starting application...")

    # Create application
    app = setup_application()

    # Create main window
    logger.info("Creating main window")
    main_window = MainWindow(version=VERSION)

    # Create controller and connect to main window
    logger.info("Creating application controller")
    controller = AppController(main_window)

    # Show main window
    logger.info("Showing main window")
    main_window.show()

    print("✓ Application started successfully")
    logger.info("Application started successfully")
    print("\nGUI Controls:")
    print("  - Left Panel: Browse and filter camera data")
    print("  - Center Tabs: View images and interactive plots")
    print("  - Right Panel: Compare images side-by-side (toggle with View menu)")
    print("\nTips:")
    print("  - Double-click a row in the data browser to view the image")
    print("  - Use mouse wheel to zoom in image viewer")
    print("  - Select cameras and click 'Generate Plot' for custom plots")
    print("=" * 50)

    # Run application event loop
    exit_code = app.exec()

    # Cleanup
    print("\nShutting down...")
    logger.info("Application shutting down")
    controller.shutdown()
    logger.info("Application closed successfully")
    print("✓ Application closed")

    sys.exit(exit_code)


if __name__ == '__main__':
    main()
