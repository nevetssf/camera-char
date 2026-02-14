# Image Browser Updates - Change Log

## Summary
Enhanced the data browser with file browsing capabilities and automatic image loading on row selection.

## Changes Made

### 1. Added Browse Button for Source Directory

**Location:** Left panel, above the Search box

**UI Layout:**
```
┌─────────────────────────────────────┐
│ Data Browser                        │
├─────────────────────────────────────┤
│ [Filters section]                   │
├─────────────────────────────────────┤
│ Source: [Browse...]                 │  ← NEW!
│ 📁 /path/to/noise_images         │  ← NEW!
├─────────────────────────────────────┤
│ Search: [________________]          │
├─────────────────────────────────────┤
│ [Data table]                        │
└─────────────────────────────────────┘
```

**Functionality:**
- Click "Browse..." to open directory selection dialog
- Selected path displays below button with folder icon 📁
- Path stored in `DataBrowser.source_directory`
- Used to construct full file paths for images

### 2. Clean Filename Display in Source Column

**Before:**
```
| source                                                    |
|----------------------------------------------------------|
| /home/steven/git/camera-char/noise_images/M11/L10.DNG |
```

**After:**
```
| source      |
|-------------|
| L10.DNG     |
```

**Implementation:**
- Modified `PandasTableModel.data()` to extract filename with `Path(value).name`
- Full paths still stored in CSV data
- Only display changed for cleaner UI

### 3. Automatic Image Loading on Row Click

**Behavior:**
1. User clicks any row in the data table
2. Application automatically:
   - Constructs full file path using source directory
   - Loads image in Image Viewer
   - Switches to Image Viewer tab
   - Displays metadata
   - Updates status bar

**Status Bar Messages:**
- `Selected: Leica M11 (60MP) | ISO 100 | Exp: 0.004s | File: L1000467.DNG`
- `Loaded: L1000467.DNG` (success)
- `Source file not found. Use Browse to set source directory.` (not found)
- `Failed to load image: [error]` (loading error)

### 4. Smart Path Resolution

**Path Construction Logic:**
```python
def get_file_path_for_row(row):
    # 1. Try: source_directory + filename
    if source_directory:
        path = source_directory / source
        if path.exists():
            return path

    # 2. Try: source as absolute path
    if Path(source).exists():
        return source

    # 3. Try: relative to current directory
    if Path(f"./{source}").exists():
        return resolve(f"./{source}")

    # 4. Return None (file not found)
    return None
```

**Handles:**
- Full paths in CSV (legacy)
- Relative paths
- User-selected source directory
- Missing files (graceful degradation)

## Modified Files

### views/data_browser.py
**Lines Changed:** ~60 lines added/modified

**New Imports:**
- `QFileDialog` for directory selection

**New Attributes:**
- `source_directory: Optional[str]` - Selected source directory path
- `browse_button: QPushButton` - Browse button widget
- `source_path_label: QLabel` - Path display label

**New Methods:**
- `_on_browse_source()` - Handle Browse button click
- `get_file_path_for_row(row)` - Construct full file path from row data

**Modified Methods:**
- `_create_ui()` - Added Browse button and path label
- `PandasTableModel.data()` - Extract filename from source column

### views/main_window.py
**Lines Changed:** ~15 lines modified

**Modified Methods:**
- `_on_row_selected(row_index)` - Enhanced to:
  - Use `get_file_path_for_row()` instead of looking for 'file_path' key
  - Load image automatically with proper error handling
  - Show filename in status bar
  - Display helpful messages when file not found

## Usage Example

### Step-by-Step Workflow

1. **Launch Application**
   ```bash
   python main.py
   ```

2. **Set Source Directory**
   - Click "Browse..." button in left panel
   - Navigate to your raw files directory
   - Example: `/home/steven/git/camera-char/noise_images/`
   - Click "Select" or "Choose"
   - Path displays: `📁 /home/steven/git/camera-char/noise_images/`

3. **Browse Images**
   - Scroll through the data table
   - See clean filenames in source column (e.g., `L1000467.DNG`)
   - Click any row to view the image

4. **View Image**
   - Image loads automatically in Image Viewer tab
   - Metadata displays below image
   - Status bar shows: `Loaded: L1000467.DNG`

5. **Continue Browsing**
   - Click another row to load different image
   - Use filters to narrow down selections
   - Search for specific cameras or ISOs

## Benefits

### User Experience
- ✅ One-click image loading (no File > Open needed)
- ✅ Cleaner table display (filenames only)
- ✅ Persistent source directory (set once, use many times)
- ✅ Clear feedback via status bar messages
- ✅ Automatic tab switching to viewer

### Technical
- ✅ Flexible path resolution (absolute, relative, or source directory)
- ✅ Graceful error handling (missing files don't crash app)
- ✅ Backward compatible (works with full paths in CSV)
- ✅ Clean separation of concerns (DataBrowser handles paths)

## Testing

### Manual Test Cases

**Test 1: Browse and Load**
1. Click Browse → Select directory with raw files
2. Click any row in table
3. ✓ Image should load and display

**Test 2: Missing File**
1. Don't set source directory (or set wrong one)
2. Click any row
3. ✓ Should show: "Source file not found. Use Browse..."

**Test 3: Filename Display**
1. Look at source column in table
2. ✓ Should show only filename (e.g., `L1000467.DNG`)
3. ✓ Should NOT show full path

**Test 4: Multiple Selections**
1. Click row 1 → verify image loads
2. Click row 2 → verify different image loads
3. ✓ Images should change correctly

**Test 5: Filter and Load**
1. Filter by camera (e.g., Leica M11)
2. Click a filtered row
3. ✓ Should load correctly

## Future Enhancements

Potential improvements for next version:
- [ ] Remember last source directory (save to settings)
- [ ] Auto-detect common directories (noise_images/, raw/, etc.)
- [ ] Thumbnail preview in table
- [ ] Double-click to load (single-click for selection only)
- [ ] Keyboard navigation (arrow keys + Enter to load)
- [ ] Recent directories dropdown
- [ ] Drag-and-drop directory selection

## Notes

- Source directory setting is session-based (not saved between app restarts)
- CSV data still contains full paths (only display is modified)
- File path resolution checks multiple locations for compatibility
- Works with DNG, ERF, TIFF, JPEG, and other supported formats

---
**Date:** 2026-02-12
**Version:** 1.1
**Author:** Enhanced by Claude Sonnet 4.5
