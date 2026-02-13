# Camera Sensor Analyzer - Desktop Application

A standalone PyQt6 desktop application for visualizing and analyzing camera sensor noise characteristics from raw DNG/ERF files.

## Features

- **Data Browser**: Browse and filter 1456+ analyzed images across 19 camera models
- **Image Viewer**: Display raw DNG/ERF files and TIFF images with zoom/pan
- **Interactive Plots**: Plotly charts for EV vs ISO and EV vs Time analysis
- **Comparison View**: Side-by-side image comparison with synchronized zoom
- **Smart Caching**: LRU cache for recently loaded images
- **Export**: Export filtered data to CSV and plots to HTML/PNG

## Installation

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

Required packages:
- PyQt6 (6.6.1)
- PyQt6-WebEngine (6.6.0)
- pandas, numpy, plotly
- rawpy, PyExifTool

### 2. Verify Files

Ensure these files are present in the project directory:
- `aggregate_analysis.csv` - Pre-analyzed data (1456 images)
- `sensor_camera.py` - Analysis module
- `main.py` - Application entry point

## Quick Start

### Run the Application

```bash
python main.py
```

Or make it executable and run directly:

```bash
chmod +x main.py
./main.py
```

### First Launch

1. The application will check for all dependencies
2. Main window opens with three panels:
   - **Left**: Data browser with filters
   - **Center**: Tabbed interface (Image Viewer, EV vs ISO, EV vs Time)
   - **Right**: Comparison view (initially hidden)

## Usage Guide

### Data Browser (Left Panel)

1. **Browse Data**
   - View all 1456 analyzed images in table format
   - Sort by clicking column headers
   - Double-click row to load image

2. **Filter by Camera**
   - Select one or more camera models from list
   - Multi-select with Cmd/Ctrl+Click

3. **Filter by ISO**
   - Select ISO values to filter results
   - Multi-select supported

4. **Search**
   - Type in search box to filter by any field
   - Real-time filtering

5. **Reset Filters**
   - Click "Reset Filters" to clear all selections

### Image Viewer (Center Panel - Tab 1)

1. **View Images**
   - Double-click row in data browser to load
   - Or use File > Open Image menu

2. **Zoom Controls**
   - Mouse wheel: Zoom in/out
   - Fit to Window: Fit entire image
   - 100%: Actual size
   - Zoom In/Out buttons

3. **Navigation**
   - Click and drag to pan
   - Hover over pixels to see values

4. **Metadata**
   - View file information in bottom panel
   - Camera, ISO, dimensions, file size

### Plot Viewer (Center Panel - Tabs 2-3)

#### EV vs ISO Plot (Tab 2)

1. Select exposure time from dropdown
2. Select cameras to include (multi-select)
3. Click "Generate Plot"
4. Interactive plot with hover tooltips
5. Click legend items to toggle cameras on/off

#### EV vs Time Plot (Tab 3)

1. Select ISO from dropdown
2. Select cameras to include
3. Click "Generate Plot"
4. Interactive plot with hover tooltips

### Comparison View (Right Panel)

1. **Enable**: View > Toggle Comparison View (or Ctrl+Shift+C)
2. **Load Images**:
   - Click "Select Left Image..." and "Select Right Image..."
   - Or drag from data browser
3. **Compare**:
   - Side-by-side viewing
   - Synchronized zoom (toggle with "Sync Zoom/Pan")
   - Metadata comparison table at bottom

## Keyboard Shortcuts

- `Cmd/Ctrl+O` - Open image file
- `Cmd/Ctrl+Q` - Quit application
- `Cmd/Ctrl+Shift+C` - Toggle comparison view

## Menu Options

### File Menu
- **Open Image...** - Open raw image file
- **Export Data...** - Export filtered data to CSV
- **Export Plot...** - Export current plot to HTML
- **Quit** - Exit application

### View Menu
- **Toggle Comparison View** - Show/hide comparison panel
- **Clear Image Cache** - Free memory by clearing cached images

### Help Menu
- **About** - Application information

## Performance Tips

1. **Fast Preview Mode**
   - Uses embedded JPEG thumbnails for quick loading
   - Enabled automatically for large files

2. **Memory Management**
   - Cache stores max 10 recent images
   - Clear cache if memory is tight (View > Clear Image Cache)

3. **Filtering**
   - Filter data before generating plots for better performance
   - Select fewer cameras for faster plot generation

## File Format Support

### Raw Files
- **DNG** - Digital Negative (Adobe)
- **ERF** - Epson Raw Format
- **NEF** - Nikon Electronic Format
- **CR2** - Canon Raw 2
- **ARW** - Sony Alpha Raw

### Processed Files
- **TIFF/TIF** - Tagged Image File Format (16-bit supported)
- **JPEG/JPG** - Standard compressed images
- **PNG** - Portable Network Graphics

## Camera-Specific Features

The application supports camera-specific crops for:
- LEICA Q (Typ 116)
- RICOH GR III
- LEICA CL
- LEICA Q3
- LEICA SL2-S

These crops are automatically applied when loading images.

## Troubleshooting

### Application Won't Start

**Error: aggregate_analysis.csv not found**
- Run from the camera-char project directory
- Verify file exists with `ls aggregate_analysis.csv`

**Error: Missing required packages**
- Install dependencies: `pip install -r requirements.txt`

**Error: sensor_camera.py module not found**
- Ensure sensor_camera.py is in the same directory

### Images Won't Load

**File not found error**
- Check that noise_images/ directory exists
- Verify raw files are present

**Corrupted image error**
- Try another image
- File may be damaged

### Plots Won't Generate

**No data points error**
- Check filter selections
- Ensure cameras are selected
- Verify exposure time/ISO exists in data

**WebEngine error**
- Ensure PyQt6-WebEngine is installed
- Try reinstalling: `pip install --force-reinstall PyQt6-WebEngine`

### Memory Issues

**Application slow or crashes**
- Clear image cache (View > Clear Image Cache)
- Close other applications
- Reduce number of cached images (edit utils/image_loader.py)

### Display Issues

**Blank plots or images**
- Try restarting application
- Check terminal for error messages

**High DPI scaling issues**
- Adjust display scaling in system settings
- Application supports high DPI displays

## Architecture

### Project Structure

```
camera-char/
├── main.py                 # Application entry point
├── models/
│   ├── data_model.py      # CSV data management
│   └── image_model.py     # Image loading
├── views/
│   ├── main_window.py     # Main window UI
│   ├── data_browser.py    # Data table view
│   ├── image_viewer.py    # Image display
│   ├── plot_viewer.py     # Plotly integration
│   └── comparison_view.py # Side-by-side comparison
├── controllers/
│   └── app_controller.py  # Application logic
├── utils/
│   ├── image_loader.py    # Image utilities
│   └── plot_generator.py  # Plot generation
└── sensor_camera.py        # Existing analysis module
```

### MVC Pattern

- **Models**: Data management (CSV, images)
- **Views**: UI components (widgets, windows)
- **Controllers**: Application logic and coordination

### Key Technologies

- **PyQt6**: Cross-platform GUI framework
- **QtWebEngine**: Embedded browser for Plotly plots
- **rawpy**: Raw image processing (libraw wrapper)
- **Plotly**: Interactive plotting
- **pandas**: Data manipulation
- **numpy**: Image array operations

## Future Enhancements

Potential features for future versions:

1. **Real-time Analysis**: Analyze new raw files from within the app
2. **Batch Processing**: Process multiple files at once
3. **Custom Plots**: Create custom plot configurations
4. **Report Generation**: Export analysis reports as PDF
5. **Histogram Overlay**: Show histogram on image viewer
6. **Pixel Inspector**: Click to get detailed pixel info
7. **Zoom Synchronization**: Sync zoom between comparison views
8. **Plugin System**: Support for custom analysis modules

## Support

For issues or questions:
1. Check this documentation
2. Review error messages in terminal
3. Check GitHub issues (if available)

## License

Same license as the parent camera-char project.

## Credits

Built with PyQt6, rawpy, Plotly, and pandas.
Based on the sensor_camera analysis module.
