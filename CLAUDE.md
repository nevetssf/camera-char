# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

PyQt6 desktop application for analyzing and visualizing camera sensor noise characteristics from raw DNG/ERF image files. Combines a scientific analysis backend (`sensor_camera.py`) with an interactive GUI.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt
# ExifTool required: sudo apt install libimage-exiftool-perl (Linux) or brew install exiftool (macOS)

python main.py                     # Run the desktop application
python test_app.py                 # Run component tests (no GUI required, custom framework)
python test_raw_viewer.py <path_to_dng> [camera_model]  # Interactive raw viewer test

# Jupyter notebook workflow (standalone, no GUI)
jupyter lab sensor_noise.ipynb     # Uses sensor_camera.py directly for analysis
```

No formal test framework (pytest/unittest) — tests use custom print-based assertions with sys.exit(1) on failure. No linter or formatter configured.

## Architecture

**MVC pattern** with PyQt6 signals/slots for component communication.

### Signal Flow (Critical to understand)

Filter changes flow through a single path — do NOT add duplicate handlers:
```
DataBrowser._on_filter_changed()
  → emits data_filtered signal
  → MainWindow._on_data_filtered()     # THE handler for plot updates
  → PlotViewer.generate_plot_from_data()
  → QWebEngineView.setHtml()           # Async — calling twice = blank plot
```

`AppController._on_data_filtered()` handles status bar updates only. Plot generation must happen in exactly one place to avoid double `setHtml()` on QWebEngineView.

### Key Modules

- **main.py** — Entry point. macOS/PyInstaller integration, dependency checks, config/db/logger init, creates MainWindow + AppController
- **sensor_camera.py** — Core analysis engine. `Sensor` class (single camera scan, noise stats, EV calculation) and `Analysis` class (multi-camera aggregate). EV = log2((white_level - black_level) / std_dev). Optional GPU acceleration via CuPy. Also used standalone from `sensor_noise.ipynb`
- **controllers/app_controller.py** — Signal routing, background image loading, state coordination
- **models/data_model.py** — DataFrame filtering, exposes data to views
- **utils/db_manager.py** — SQLite database (images, cameras, analysis_results, exif_data, camera_attributes tables)
- **utils/analysis_runner.py** — Orchestrates scanning and analyzing images, with progress callbacks and cancellation
- **utils/config_manager.py** — Singleton. Working dir (`~/.camera-char/`), source dir (raw images path)
- **utils/image_loader.py** — LRU-cached raw file loading with camera-specific crops

### Views

- **main_window.py** — QMainWindow with QSplitter layout: DataBrowser (left), TabWidget with Plot/Metadata (center), ComparisonView (right, hidden)
- **data_browser.py** — Cascading filter columns + QTableView. Filters block signals during repopulation to prevent recursive triggers
- **plot_viewer.py** — Plotly charts in QWebEngineView. Controls: Group/Y-Axis/X-Axis combos, log scale checkbox. Has "Show Data" debug window
- **image_viewer.py** — Raw image display with metadata
- **image_window.py** — Pop-out image viewer with histogram

## Important Patterns

- **Exposure time formatting**: Always use `round(1/exposure_time)` not `int()` — e.g., 0.016667s → "1/60s" not "1/59s". Format: `1/{n}s` for < 1s, `{n}s` for >= 1s. There is no `exposure_setting` column — derive formatted display from `exposure_time` using `format_exposure_time()` in data_browser.py
- **QWebEngineView.setHtml()** is async — calling it twice rapidly causes blank renders. Always ensure single call path
- **Singletons**: `get_config()`, `get_db_manager()`, `get_logger()`, `get_plot_generator()` all return global instances
- **Camera crops**: Defined in `sensor_camera.CAMERA_CROPS` dict, applied during image loading
- **Working directory**: `~/.camera-char/` contains config.json, debug.log, db/analysis.db, .archive/ backups

## Two Workflows

1. **Desktop app** (`main.py`) — GUI for browsing, filtering, and plotting analysis data stored in SQLite
2. **Notebook** (`sensor_noise.ipynb`) — Scripted analysis using `sensor_camera.py` directly, outputs to CSV files and Plotly figures

Both share `sensor_camera.py` as the analysis engine. The desktop app can import data produced by the notebook workflow.

## Data Storage

- **Database**: SQLite at `~/.camera-char/db/analysis.db` — images deduplicated by file hash
- **Aggregate CSV**: `aggregate_analysis.csv` in project root (from notebook workflow)
- **Per-camera CSV**: `noise_results.csv` in each camera's scan directory (cached scan results)
- **DB backups**: Timestamped copies in `~/.camera-char/.archive/` on each startup
- **Raw images**: Stored in `detector-noise/` directory (gitignored), organized by camera model subdirectories
