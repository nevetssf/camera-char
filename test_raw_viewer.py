#!/usr/bin/env python3
"""
Standalone test for raw image viewer with statistics overlay.
Usage: python test_raw_viewer.py <path_to_dng_file>
"""

import sys
import numpy as np
import rawpy
from pathlib import Path
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QPixmap, QImage
from views.image_window import ImageWindow
from sensor_camera import Sensor


def load_raw_with_stats(file_path: str, camera_model: str = None) -> tuple:
    """
    Load raw image and create pixmap with statistics overlay.

    Returns:
        tuple: (pixmap_with_stats, display_array, file_path)
    """
    print(f"Loading raw file: {file_path}")

    # Load raw data directly without color processing
    with rawpy.imread(str(file_path)) as raw:
        # Get raw pixel data (greyscale)
        raw_data = raw.raw_image.copy()
        print(f"Raw data shape: {raw_data.shape}, dtype: {raw_data.dtype}")

        # Apply camera-specific crop if available
        if camera_model:
            crop = Sensor.CAMERA_CROPS.get(camera_model)
            if crop is not None:
                print(f"Applying crop for {camera_model}: {crop}")
                raw_data = raw_data[crop]

        # Calculate statistics
        mean_val = float(np.mean(raw_data))
        std_val = float(np.std(raw_data))
        ydim, xdim = raw_data.shape
        bit_depth = raw_data.dtype.itemsize * 8
        max_val = np.max(raw_data)

        print(f"Statistics:")
        print(f"  Bit depth: {bit_depth}")
        print(f"  Dimensions: {xdim} x {ydim}")
        print(f"  Mean: {mean_val:.2f}")
        print(f"  Std Dev: {std_val:.2f}")
        print(f"  Max: {max_val}")

        # Normalize to 8-bit for display
        if raw_data.dtype == np.uint16:
            display_array = (raw_data.astype(np.float32) / 65535.0 * 255.0).astype(np.uint8)
        elif raw_data.dtype == np.uint8:
            display_array = raw_data
        else:
            # For other types, normalize to full range
            min_val = np.min(raw_data)
            max_val = np.max(raw_data)
            if max_val > min_val:
                display_array = ((raw_data.astype(np.float32) - min_val) / (max_val - min_val) * 255.0).astype(np.uint8)
            else:
                display_array = np.zeros_like(raw_data, dtype=np.uint8)

        print(f"Display array shape: {display_array.shape}, dtype: {display_array.dtype}")

        # Convert to QImage (greyscale)
        bytes_per_line = xdim
        qimage = QImage(display_array.data, xdim, ydim, bytes_per_line, QImage.Format.Format_Grayscale8)
        pixmap = QPixmap.fromImage(qimage)

        print(f"Created pixmap: {pixmap.width()} x {pixmap.height()}")

        # Prepare statistics dictionary
        stats = {
            'bit_depth': bit_depth,
            'width': xdim,
            'height': ydim,
            'mean': mean_val,
            'std': std_val,
            'max': max_val
        }

        print("Statistics prepared")

    return pixmap, display_array, file_path, stats


def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print("Usage: python test_raw_viewer.py <path_to_dng_file> [camera_model]")
        print("\nExample:")
        print("  python test_raw_viewer.py noise_images/Ricoh-GXR/_0019442.DNG 'RICOH GXR'")
        sys.exit(1)

    file_path = sys.argv[1]
    camera_model = sys.argv[2] if len(sys.argv) > 2 else None

    if not Path(file_path).exists():
        print(f"ERROR: File not found: {file_path}")
        sys.exit(1)

    # Create Qt application
    app = QApplication(sys.argv)

    # Create image window
    window = ImageWindow()
    window.setWindowTitle(f"Raw Image Viewer - {Path(file_path).name}")

    try:
        # Load image with statistics
        pixmap, display_array, path, stats = load_raw_with_stats(file_path, camera_model)

        # Display in window
        window.load_image(pixmap, display_array, path, stats=stats)
        window.show()

        print("\n✓ Window opened successfully!")
        print("  - Use mouse wheel to zoom")
        print("  - Click and drag to pan")
        print("  - Use buttons for preset zoom levels")

    except Exception as e:
        print(f"\nERROR: Failed to load image: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    # Run application
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
