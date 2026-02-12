# Installation & Quick Start Guide

## Camera Sensor Analyzer Desktop Application

### Prerequisites

- Python 3.9 or higher
- macOS, Linux, or Windows
- Display server (GUI environment)

### Installation Steps

#### 1. Install All Dependencies

```bash
pip install -r requirements.txt
```

This will install:
- PyQt6 (6.10.2) - GUI framework
- PyQt6-WebEngine (6.10.0) - For Plotly integration
- pandas, numpy - Data processing
- plotly - Interactive plots
- rawpy - Raw image processing
- PyExifTool - Metadata extraction
- All other required packages

#### 2. Verify Installation

Run the test suite to verify all components:

```bash
python test_app.py
```

You should see:
```
✓ ALL TESTS PASSED!
```

#### 3. Launch the Application

```bash
python main.py
```

Or use the quick-start script:

```bash
./run_app.sh
```

### First Time Setup

No additional setup required! The application will:
- Automatically load `aggregate_analysis.csv` (1457 images)
- Initialize 12 camera models
- Prepare 17 ISO values and 30 exposure times for plotting

### Verifying It Works

When you launch the application, you should see:

1. **Main window** with three panels
2. **Data browser** (left) showing 1457 records
3. **Tabbed interface** (center) with:
   - Image Viewer tab
   - EV vs ISO plot tab
   - EV vs Time plot tab
4. **Status bar** (bottom) showing "Ready"

### Quick Test

1. **Filter data**: In the left panel, select a camera (e.g., "Leica M11 (36MP)")
2. **Generate plot**: Switch to "EV vs ISO" tab, select an exposure time, click "Generate Plot"
3. **Interact**: Hover over plot points to see details, click legend items to toggle

### Troubleshooting

#### "No module named 'PyQt6'"

```bash
pip install PyQt6==6.10.2 PyQt6-WebEngine==6.10.0
```

#### "aggregate_analysis.csv not found"

Make sure you're running from the camera-char directory:
```bash
cd /Users/steve/Projects/camera-char
python main.py
```

#### "No display server"

If running over SSH:
```bash
ssh -X user@host
python main.py
```

#### Application crashes on startup

1. Check Python version: `python --version` (need 3.9+)
2. Reinstall dependencies: `pip install --force-reinstall -r requirements.txt`
3. Run test suite: `python test_app.py`

### Available Cameras

The application includes data for these 12 camera models:

1. Epson R-D1 (54 images)
2. Leica CL 24MP (135 images)
3. Leica M Monochrome (104 images)
4. Leica M10 24MP (130 images)
5. Leica M11 18MP (130 images)
6. Leica M11 36MP (130 images)
7. Leica M11 60MP (133 images)
8. Leica Q 24MP (121 images)
9. Leica Q3 36MP (135 images)
10. Leica SL2-S 24MP (156 images)
11. Ricoh GR III (147 images)
12. Ricoh GXR (82 images)

### Performance

- **First launch**: ~2-3 seconds
- **Filter update**: Instant
- **Plot generation**: 1-2 seconds
- **Image loading**: 1-3 seconds (depends on file size)

### Memory Usage

- Base application: ~150MB
- With 10 cached images: ~500MB
- Single plot: ~50MB

### Next Steps

See `DESKTOP_APP.md` for:
- Detailed feature documentation
- Keyboard shortcuts
- Advanced usage
- Export options
- Troubleshooting guide

### Support Files

- `main.py` - Application entry point
- `test_app.py` - Test suite
- `run_app.sh` - Quick launch script
- `DESKTOP_APP.md` - Full documentation
- `INSTALLATION.md` - This file

### Development

To modify the application:

- **Models**: `models/` - Data handling
- **Views**: `views/` - UI components
- **Controllers**: `controllers/` - Application logic
- **Utils**: `utils/` - Helper functions

### License

Same as camera-char project.
