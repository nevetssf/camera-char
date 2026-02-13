#!/usr/bin/env python3
"""
Camera Sensor Analyzer - Desktop Application
Main entry point for the PyQt6 application.

A standalone desktop application for visualizing camera sensor noise characteristics
from raw DNG/ERF files and aggregate analysis data.
"""

import sys
import os
from pathlib import Path

# Add current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon

from views.main_window import MainWindow
from controllers.app_controller import AppController


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

    app = QApplication(sys.argv)

    # Set application metadata
    app.setApplicationName("Camera Sensor Analyzer")
    app.setOrganizationName("Camera Sensor Analysis")
    app.setApplicationVersion("1.0.0")

    # Set application style (optional)
    # app.setStyle('Fusion')  # Modern cross-platform style

    return app


def check_dependencies() -> bool:
    """
    Check that required files and dependencies are available.

    Returns:
        True if all dependencies are met, False otherwise
    """
    # Note: aggregate_analysis.csv will be loaded from working directory
    # Not required in current directory anymore

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
    print("Camera Sensor Analyzer v1.0.0")
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
    logger.info("Camera Sensor Analyzer starting up")
    logger.info(f"Working directory: {config.get_working_dir()}")
    logger.info(f"Source directory: {config.get_source_dir()}")

    print("Starting application...")

    # Create application
    app = setup_application()

    # Create main window
    logger.info("Creating main window")
    main_window = MainWindow()

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
