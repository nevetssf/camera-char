#!/bin/bash
#
# Build Sensor Analysis as a standalone macOS .app bundle.
#
# Usage:
#   ./scripts/build_app.sh
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

echo "=== Sensor Analysis - macOS App Build ==="
echo ""

# 1. Check dependencies
echo "Checking dependencies..."

if ! command -v python3 &>/dev/null; then
    echo "ERROR: python3 not found"
    exit 1
fi

if ! python3 -c "import PyInstaller" &>/dev/null; then
    echo "Installing PyInstaller..."
    pip install pyinstaller
fi

if [ ! -f /usr/local/bin/exiftool ]; then
    echo "ERROR: ExifTool not found at /usr/local/bin/exiftool"
    echo "Install with: brew install exiftool"
    exit 1
fi

echo "  OK: python3, pyinstaller, exiftool"

# 2. Generate icon
echo ""
echo "Generating app icon..."
if [ ! -f resources/SensorAnalysis.icns ]; then
    python3 scripts/create_icns.py
else
    echo "  Icon already exists, skipping (delete resources/SensorAnalysis.icns to regenerate)"
fi

# 3. Build with PyInstaller
echo ""
echo "Building app with PyInstaller..."
echo "  This may take several minutes..."
python3 -m PyInstaller SensorAnalysis.spec --noconfirm --clean

# 4. Fix permissions on bundled exiftool
echo ""
echo "Fixing permissions..."
EXIFTOOL_PATH="dist/Sensor Analysis.app/Contents/Resources/exiftool_perl/exiftool"
if [ -f "$EXIFTOOL_PATH" ]; then
    chmod +x "$EXIFTOOL_PATH"
    echo "  OK: exiftool is executable"
else
    echo "  WARNING: Bundled exiftool not found at expected path"
fi

# 5. Report
echo ""
echo "=== Build Complete ==="
APP_PATH="dist/Sensor Analysis.app"
if [ -d "$APP_PATH" ]; then
    SIZE=$(du -sh "$APP_PATH" | cut -f1)
    echo "  App: $APP_PATH"
    echo "  Size: $SIZE"
    echo ""
    echo "To test from Terminal:"
    echo "  \"$APP_PATH/Contents/MacOS/SensorAnalysis\""
    echo ""
    echo "To install:"
    echo "  cp -R \"$APP_PATH\" /Applications/"
else
    echo "ERROR: App bundle not found at $APP_PATH"
    exit 1
fi
