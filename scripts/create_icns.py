#!/usr/bin/env python3
"""
Generate macOS .icns icon file from the app's programmatic icon.

Creates an .iconset directory with all required sizes and converts to .icns
using macOS iconutil. Output: resources/SensorAnalysis.icns

Usage:
    python scripts/create_icns.py
"""

import sys
import os
import subprocess
import tempfile
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def create_icon_pixmap(size: int):
    """Create the app icon at a specific pixel size."""
    from PyQt6.QtCore import Qt
    from PyQt6.QtGui import (
        QPixmap, QPainter, QColor, QFont,
        QRadialGradient, QPen
    )

    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    # Scale factor relative to 512
    s = size / 512.0

    # Draw gradient background circle
    gradient = QRadialGradient(size / 2, size / 2, size / 2)
    gradient.setColorAt(0, QColor(70, 130, 180))   # Steel blue
    gradient.setColorAt(1, QColor(25, 55, 100))     # Dark blue

    painter.setBrush(gradient)
    painter.setPen(QPen(QColor(40, 80, 140), max(1, int(10 * s))))
    margin = int(20 * s)
    painter.drawEllipse(margin, margin, size - 2 * margin, size - 2 * margin)

    # Draw camera sensor grid
    painter.setPen(QPen(QColor(255, 255, 255, 180), max(1, int(3 * s))))
    for i in range(3):
        for j in range(3):
            x = int((140 + i * 90) * s)
            y = int((140 + j * 90) * s)
            w = int(70 * s)
            painter.drawRect(x, y, w, w)

    # Draw "S" letter
    font = QFont("Arial", max(1, int(280 * s)), QFont.Weight.Bold)
    painter.setFont(font)
    painter.setPen(QColor(255, 255, 255, 230))
    painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "S")

    painter.end()
    return pixmap


def main():
    from PyQt6.QtWidgets import QApplication

    # Need a QApplication for pixmap operations
    app = QApplication(sys.argv)

    output_dir = project_root / "resources"
    output_dir.mkdir(exist_ok=True)

    icns_path = output_dir / "SensorAnalysis.icns"

    # Required icon sizes for macOS .iconset
    # Format: (filename, pixel_size)
    icon_specs = [
        ("icon_16x16.png", 16),
        ("icon_16x16@2x.png", 32),
        ("icon_32x32.png", 32),
        ("icon_32x32@2x.png", 64),
        ("icon_128x128.png", 128),
        ("icon_128x128@2x.png", 256),
        ("icon_256x256.png", 256),
        ("icon_256x256@2x.png", 512),
        ("icon_512x512.png", 512),
        ("icon_512x512@2x.png", 1024),
    ]

    with tempfile.TemporaryDirectory() as tmpdir:
        iconset_dir = Path(tmpdir) / "SensorAnalysis.iconset"
        iconset_dir.mkdir()

        for filename, pixel_size in icon_specs:
            pixmap = create_icon_pixmap(pixel_size)
            icon_path = iconset_dir / filename
            pixmap.save(str(icon_path), "PNG")
            print(f"  Created {filename} ({pixel_size}x{pixel_size})")

        # Convert to .icns using iconutil
        result = subprocess.run(
            ["iconutil", "-c", "icns", str(iconset_dir), "-o", str(icns_path)],
            capture_output=True, text=True
        )

        if result.returncode != 0:
            print(f"Error: iconutil failed: {result.stderr}")
            sys.exit(1)

    print(f"\nCreated: {icns_path}")
    print(f"Size: {icns_path.stat().st_size / 1024:.1f} KB")


if __name__ == "__main__":
    main()
