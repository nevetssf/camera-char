# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

PyQt6 desktop application for analyzing and visualizing camera sensor noise characteristics from raw DNG/ERF image files. Combines a scientific analysis backend (`sensor_camera.py`) with an interactive GUI.

## Commands

```bash
pip install -r requirements.txt   # Install dependencies (requires ExifTool: brew install exiftool)
python main.py                     # Run the application
python test_app.py                 # Run component tests (no GUI required)
```

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

- **main.py** — Entry point. macOS integration, dependency checks, config/db/logger init, creates MainWindow + AppController
- **sensor_camera.py** — Core analysis engine. `Sensor` class (single camera scan, noise stats, EV calculation) and `Analysis` class (multi-camera aggregate). EV = log2((white_level - black_level) / std_dev)
- **controllers/app_controller.py** — Signal routing, background image loading, state coordination
- **models/data_model.py** — DataFrame filtering, exposes data to views. `exposure_setting` is a calculated display column (not in DB)
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

- **Exposure time formatting**: Always use `round(1/exposure_time)` not `int()` — e.g., 0.016667s → "1/60s" not "1/59s". Format: `1/{n}s` for < 1s, `{n}s` for >= 1s
- **exposure_setting column**: Calculated from exposure_time at load time in data_model.py, NOT stored in database. Placed before exposure_time in column order
- **QWebEngineView.setHtml()** is async — calling it twice rapidly causes blank renders. Always ensure single call path
- **Singletons**: `get_config()`, `get_db_manager()`, `get_logger()`, `get_plot_generator()` all return global instances
- **Camera crops**: Defined in `sensor_camera.CAMERA_CROPS` dict, applied during image loading
- **Working directory**: `~/.camera-char/` contains config.json, debug.log, db/analysis.db, .archive/ backups

## Data Storage

- **Database**: SQLite at `~/.camera-char/db/analysis.db` — images deduplicated by file hash
- **Aggregate CSV**: `aggregate_analysis.csv` in project root (legacy, from notebook workflow)
- **DB backups**: Timestamped copies in `~/.camera-char/.archive/` on each startup
