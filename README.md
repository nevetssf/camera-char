# Camera Sensor Noise Characterization

A Python toolkit for analyzing noise characteristics and dynamic range of digital camera sensors from raw image files.

## Overview

This project provides tools to measure and compare the noise performance of different camera sensors by analyzing raw image files (DNG, ERF, etc.). It calculates the sensor's dynamic range in Exposure Value (EV) units and provides professional visualizations for comparison.

## Features

- **Automated Raw File Scanning**: Process directories of raw images from multiple cameras
- **Noise Analysis**: Calculate standard deviation, mean, min, and max values from raw sensor data
- **Dynamic Range Calculation**: Compute Exposure Value (EV) as a measure of sensor dynamic range
- **GPU Acceleration**: Optional CUDA support for faster processing of large raw files
- **Result Caching**: Automatically saves and loads analysis results to avoid reprocessing
- **Progress Tracking**: Visual progress bars during file processing
- **Professional Visualizations**: Interactive plots with grouped legends and consistent styling
- **Multi-Camera Comparison**: Aggregate analysis across multiple camera models and variants

## Installation

### Prerequisites

- Python 3.8+
- [ExifTool](https://exiftool.org/) command-line tool
- NVIDIA GPU with CUDA (optional, for GPU acceleration)

### Install ExifTool

**Linux (Ubuntu/Debian):**
```bash
sudo apt update && sudo apt install libimage-exiftool-perl
```

**macOS:**
```bash
brew install exiftool
```

### Install Python Dependencies

```bash
pip install -r requirements.txt
```

### Optional: GPU Acceleration

If you have an NVIDIA GPU with CUDA installed:

```bash
# Check your CUDA version
nvcc --version

# Install CuPy (for CUDA 12.x/13.x)
pip install cupy-cuda12x
```

## Quick Start

### Basic Usage

```python
import sensor_camera
from collections import OrderedDict

# Create Analysis object with path to your raw files
analysis = sensor_camera.Analysis('path/to/raw/files')

# Define cameras to scan
scan_specs = OrderedDict([
    ('Leica M11 (60MP)', {'path': 'M11-60MP', 'suffix': 'DNG'}),
    ('Leica Q3 (36MP)', {'path': 'Q3-36MP', 'suffix': 'DNG'}),
])

# Scan all cameras
scan_results = analysis.scan(scan_specs)

# Create aggregate dataset
data = analysis.create_aggregate()

# Save results
analysis.save_aggregate('results.csv')

# Create plots
figures = analysis.plot_ev_vs_iso()  # EV vs ISO for all exposure times
for fig in figures:
    fig.show()
```

## API Documentation

### Sensor Class

The `Sensor` class handles scanning individual camera directories:

```python
sensor = Sensor(path='path/to/camera/files')
data = sensor.scan(path='subdirectory', suffix='DNG', force_rescan=False)
```

**Parameters:**
- `path`: Base directory or subdirectory containing raw files
- `suffix`: File extension to scan for (e.g., 'DNG', 'ERF')
- `force_rescan`: If `True`, rescan even if cached results exist

**Features:**
- Automatically crops sensor data for known camera artifacts
- Extracts EXIF metadata (ISO, exposure time, dimensions)
- Computes noise statistics (std, mean, min, max)
- Calculates Exposure Value (EV)
- Saves results to `noise_results.csv` in the scanned directory

### Analysis Class

The `Analysis` class manages aggregate analysis across multiple cameras:

```python
analysis = Analysis(base_path='path/to/data')
```

#### Methods

**`scan(scan_specs, force_rescan=False)`**
- Scans multiple cameras according to specifications
- Returns OrderedDict with results for each camera

**`create_aggregate(camera_list=None)`**
- Combines data from selected cameras into single DataFrame
- Preserves camera variant information

**`save_aggregate(filename='aggregate_analysis.csv')`**
- Saves aggregate data to CSV file

**`plot_ev_vs_iso(data=None, exposure_time=None, title=None, height=700, ev_range=None)`**
- Creates professional EV vs ISO plot(s)
- `exposure_time`: Single value, list, or None (all times)
- Returns single figure or list of figures

**`plot_ev_vs_time(data=None, iso=None, title=None, height=700, ev_range=None)`**
- Creates professional EV vs Exposure Time plot(s)
- `iso`: Single value, list, or None (all ISOs)
- Returns single figure or list of figures

**`get_aliases(short_names=None)`**
- Creates convenient variable aliases for backward compatibility

## Exposure Value (EV) Calculation

The sensor's dynamic range is quantified as:

$$\text{EV} = \log_2\left(\frac{W - B}{\sigma}\right)$$

Where:
- $W$ = white level (sensor saturation point)
- $B$ = black level (sensor baseline)
- $\sigma$ = standard deviation of raw sensor data (noise)

This represents the signal-to-noise ratio in stops (each stop = 2× light).

## Supported Cameras

The toolkit includes optimized handling for:

- **Leica**: M11, M10, Q, Q3, SL2-S, CL, TL2, M Monochrome
- **Ricoh**: GR III, GXR
- **Epson**: R-D1
- **Apple**: iPhone 13 Pro
- **Pixii**: Pixii cameras

Camera-specific crops are applied to remove known sensor artifacts.

## Visualization Features

### Professional Plots

- **Grouped Legends**: Camera variants grouped by base model
- **Consistent Colors**: Same color for all variants of a model
- **Line Style Differentiation**: Different dash patterns for variants
- **Interactive**: Hover to compare, click to toggle cameras
- **Auto-scaling**: Y-axis automatically adjusts to show all data
- **Publication Ready**: Clean styling suitable for presentations and papers

### Plot Types

1. **EV vs ISO**: Shows how dynamic range degrades with higher ISO
2. **EV vs Exposure Time**: Shows noise characteristics at different shutter speeds

## Project Structure

```
camera-char/
├── sensor_camera.py       # Main module with Sensor and Analysis classes
├── sensor_noise.ipynb     # Jupyter notebook for analysis
├── requirements.txt       # Python dependencies
├── aggregate_analysis.csv # Combined results from all cameras
└── detector-noise/        # Directory containing raw image files
    ├── M11-60MP/
    │   ├── *.DNG
    │   └── noise_results.csv
    ├── Q3-36MP/
    └── ...
```

## Performance

### GPU Acceleration

With CuPy installed, statistical calculations are performed on GPU:
- **5-10x speedup** for large raw files (20-60MP)
- Automatic fallback to CPU if GPU unavailable
- Explicit memory management to prevent GPU memory issues

### Caching

Results are automatically cached in `noise_results.csv`:
- First scan: Processes all raw files (slower)
- Subsequent scans: Loads from CSV (instant)
- Use `force_rescan=True` to regenerate

## Contributing

This is a research project for camera sensor noise analysis. Contributions are welcome!

## License

See repository for license information.

## References

- [ISO 12232](https://www.iso.org/obp/ui/#iso:std:iso:12232:ed-3:v1:en) - Photography — Digital still cameras — Determination of exposure index, ISO speed ratings, standard output sensitivity, and recommended exposure index

## Author

Created for systematic camera sensor noise characterization and comparison.

