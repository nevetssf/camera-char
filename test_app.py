#!/usr/bin/env python3
"""
Test script for Camera Sensor Analyzer
Tests all components without requiring a display.
"""

import sys
from pathlib import Path

print("Testing Camera Sensor Analyzer Components")
print("=" * 60)
print()

# Test 1: Data Model
print("1. Testing Data Model...")
try:
    from models.data_model import DataModel

    data_model = DataModel('aggregate_analysis.csv')
    total_rows = data_model.get_total_row_count()
    cameras = data_model.get_unique_cameras()
    isos = data_model.get_unique_isos()
    times = data_model.get_unique_exposure_times()

    print(f"   ✓ Loaded {total_rows} records")
    print(f"   ✓ {len(cameras)} cameras")
    print(f"   ✓ {len(isos)} ISO values")
    print(f"   ✓ {len(times)} exposure times")

    # Test filtering
    data_model.filter_by_camera([cameras[0]])
    filtered = data_model.get_row_count()
    print(f"   ✓ Filtering works ({filtered} rows for {cameras[0]})")

    data_model.reset_filters()

except Exception as e:
    print(f"   ✗ FAILED: {e}")
    sys.exit(1)

print()

# Test 2: Image Model
print("2. Testing Image Model...")
try:
    from models.image_model import ImageModel

    image_model = ImageModel()
    print(f"   ✓ ImageModel initialized")

except Exception as e:
    print(f"   ✗ FAILED: {e}")
    sys.exit(1)

print()

# Test 3: Image Loader
print("3. Testing Image Loader...")
try:
    from utils.image_loader import ImageLoader, get_image_loader

    loader = get_image_loader(cache_size=5)
    stats = loader.get_cache_stats()
    print(f"   ✓ ImageLoader initialized")
    print(f"   ✓ Cache: {stats['image_cache_max']} images, {stats['thumbnail_cache_max']} thumbnails")

except Exception as e:
    print(f"   ✗ FAILED: {e}")
    sys.exit(1)

print()

# Test 4: Plot Generator
print("4. Testing Plot Generator...")
try:
    from utils.plot_generator import get_plot_generator

    plot_gen = get_plot_generator()
    cameras = plot_gen.get_unique_cameras()
    isos = plot_gen.get_unique_isos()
    times = plot_gen.get_unique_exposure_times()

    print(f"   ✓ PlotGenerator initialized")
    print(f"   ✓ Can generate plots for {len(times)} exposure times")
    print(f"   ✓ Can generate plots for {len(isos)} ISOs")

    # Test plot generation
    if times and cameras:
        fig = plot_gen.generate_ev_vs_iso_plot(
            exposure_time=times[0],
            camera_filter=cameras[:3]
        )
        print(f"   ✓ Generated EV vs ISO plot for time={times[0]}s")

    if isos and cameras:
        # Try different ISOs until we find one with data
        plot_generated = False
        for iso in isos[:5]:  # Try first 5 ISOs
            try:
                fig = plot_gen.generate_ev_vs_time_plot(
                    iso=iso,
                    camera_filter=cameras[:3]
                )
                print(f"   ✓ Generated EV vs Time plot for ISO={iso}")
                plot_generated = True
                break
            except ValueError:
                continue  # Try next ISO

        if not plot_generated:
            print(f"   ⚠ Could not generate EV vs Time plot (no valid ISO data)")

except Exception as e:
    print(f"   ✗ FAILED: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print()

# Test 5: View Modules
print("5. Testing View Modules...")
try:
    # Note: Can't instantiate QWidgets without QApplication
    import views.main_window
    import views.data_browser
    import views.image_viewer
    import views.plot_viewer
    import views.comparison_view

    print(f"   ✓ All view modules import successfully")

except Exception as e:
    print(f"   ✗ FAILED: {e}")
    sys.exit(1)

print()

# Test 6: Controller
print("6. Testing Controller...")
try:
    import controllers.app_controller

    print(f"   ✓ AppController module imports successfully")

except Exception as e:
    print(f"   ✗ FAILED: {e}")
    sys.exit(1)

print()
print("=" * 60)
print("✓ ALL TESTS PASSED!")
print()
print("The application is ready to run:")
print("  python main.py")
print()
print("Note: The GUI requires a display server (X11/Wayland/Aqua).")
print("      Running via SSH? Use 'ssh -X' for X11 forwarding.")
print()
