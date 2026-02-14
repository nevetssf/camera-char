#!/usr/bin/env python3
"""
Standalone Raw Image Viewer Application

A standalone desktop application for viewing raw camera images (DNG, ERF, RAF, etc.)
with greyscale display and detailed statistics.

Features:
- Display raw pixel data as greyscale (not color-processed)
- Show image statistics: bit depth, dimensions, mean, std dev, max
- Zoom and pan controls
- Open files via file dialog
- Apply camera-specific crops
"""

import sys
import numpy as np
import rawpy
from pathlib import Path
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QPixmap, QImage
from views.image_window import ImageWindow
from sensor_camera import Sensor
from utils.config_manager import get_config


def load_raw_image(file_path: str) -> tuple:
    """
    Load a raw image file and return pixmap with statistics.

    Args:
        file_path: Path to raw image file

    Returns:
        tuple: (pixmap, display_array, stats_dict, raw_data, file_hash, camera_id)
    """
    print(f"Loading: {file_path}")

    # Try to determine camera model from filename or directory
    file_path_obj = Path(file_path)
    parent_dir = file_path_obj.parent.name
    camera_model = None

    # Common camera model patterns in directory names
    camera_mapping = {
        'Ricoh-GXR': 'RICOH GXR',
        'Ricoh-GRIII': 'RICOH GR III',
        'Leica-M11': 'LEICA CAMERA AG LEICA M11',
        'Sony-A7': 'SONY ILCE-7',
        # Add more as needed
    }
    camera_model = camera_mapping.get(parent_dir)

    # Load raw data directly without color processing
    with rawpy.imread(str(file_path)) as raw:
        # Get raw pixel data (greyscale)
        raw_data = raw.raw_image.copy()

        # Apply camera-specific crop if available
        if camera_model:
            crop = Sensor.CAMERA_CROPS.get(camera_model)
            if crop is not None:
                print(f"Applying crop for {camera_model}")
                raw_data = raw_data[crop]

        # Calculate statistics
        mean_val = float(np.mean(raw_data))
        std_val = float(np.std(raw_data))
        ydim, xdim = raw_data.shape
        bit_depth = raw_data.dtype.itemsize * 8
        min_val = int(np.min(raw_data))
        max_val = int(np.max(raw_data))

        print(f"  Dimensions: {xdim} × {ydim}")
        print(f"  Bit depth: {bit_depth}")
        print(f"  Mean: {mean_val:.2f}, Std: {std_val:.2f}")
        print(f"  Min: {min_val}, Max: {max_val}")

        # Normalize to 8-bit for display
        if raw_data.dtype == np.uint16:
            display_array = (raw_data.astype(np.float32) / 65535.0 * 255.0).astype(np.uint8)
        elif raw_data.dtype == np.uint8:
            display_array = raw_data
        else:
            # For other types, normalize to full range
            min_val = np.min(raw_data)
            if max_val > min_val:
                display_array = ((raw_data.astype(np.float32) - min_val) / (max_val - min_val) * 255.0).astype(np.uint8)
            else:
                display_array = np.zeros_like(raw_data, dtype=np.uint8)

        # Convert to QImage (greyscale)
        bytes_per_line = xdim
        qimage = QImage(display_array.data, xdim, ydim, bytes_per_line, QImage.Format.Format_Grayscale8)
        pixmap = QPixmap.fromImage(qimage)

        # Prepare statistics dictionary
        stats = {
            'bit_depth': bit_depth,
            'width': xdim,
            'height': ydim,
            'mean': mean_val,
            'std': std_val,
            'min': min_val,
            'max': max_val
        }

    # Calculate file hash and look up camera ID for histogram settings
    file_hash = None
    camera_id = None
    try:
        from utils.db_manager import get_db_manager
        db = get_db_manager()
        file_hash = db.calculate_file_hash(Path(file_path))
        camera_id = db.get_camera_id_by_file_hash(file_hash)
        print(f"  Camera ID: {camera_id}")
    except Exception as e:
        print(f"  Could not look up camera ID: {e}")

    return pixmap, display_array, stats, raw_data, file_hash, camera_id


def main():
    """Main entry point for standalone raw image viewer"""
    print("Raw Image Viewer - Standalone Mode")
    print("=" * 50)

    # Get default directory from config
    config = get_config()
    default_dir = config.get_source_dir()

    if not default_dir or not Path(default_dir).exists():
        default_dir = str(Path.home())

    print(f"Default directory: {default_dir}")

    # Create Qt application
    app = QApplication(sys.argv)
    app.setApplicationName("Raw Image Viewer")

    # Create image window in standalone mode
    window = ImageWindow(
        parent=None,
        standalone=True,
        image_loader_callback=load_raw_image,
        default_dir=default_dir
    )

    # Load default file for development or file from argument
    default_file = "/Users/steve/Library/CloudStorage/SynologyDrive-SF/camera-char/noise_images/Pixii/P0000478.DNG"

    # If a file path is provided as argument, use it; otherwise use default
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
    else:
        file_path = default_file

    if Path(file_path).exists():
        try:
            print(f"\nLoading initial file: {file_path}")
            pixmap, display_array, stats, raw_data, file_hash, camera_id = load_raw_image(file_path)
            window.load_image(
                pixmap, display_array, file_path,
                stats=stats, raw_data=raw_data,
                file_hash=file_hash, camera_id=camera_id
            )
        except Exception as e:
            print(f"Error loading initial file: {e}")
            import traceback
            traceback.print_exc()
    else:
        print(f"\nDefault file not found: {file_path}")

    # Show window
    window.show()

    print("\n✓ Raw Image Viewer started")
    print("  - Click 'Open...' to select a raw image file")
    print("  - Use mouse wheel to zoom")
    print("  - Click and drag to pan")
    print("=" * 50)

    # Run application
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
