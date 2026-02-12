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
    # Check for aggregate_analysis.csv
    csv_path = Path('aggregate_analysis.csv')
    if not csv_path.exists():
        print("ERROR: aggregate_analysis.csv not found in current directory")
        print("Please run the application from the camera-char project directory")
        return False

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
    print("Starting application...")

    # Create application
    app = setup_application()

    # Create main window
    main_window = MainWindow()

    # Create controller and connect to main window
    controller = AppController(main_window)

    # Show main window
    main_window.show()

    print("✓ Application started successfully")
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
    controller.shutdown()
    print("✓ Application closed")

    sys.exit(exit_code)


if __name__ == '__main__':
    main()
