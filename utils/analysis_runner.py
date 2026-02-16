"""
Analysis runner for analyzing raw images and storing results in database.
Uses the existing sensor_camera.Analysis class to scan and analyze images.
"""

from pathlib import Path
from typing import List, Dict, Optional
from collections import OrderedDict

from sensor_camera import Analysis, Sensor
from utils.exiftool_helper import get_exiftool_helper
from utils.config_manager import get_config
from utils.db_manager import get_db_manager
from utils.app_logger import get_logger

logger = get_logger()


class AnalysisRunner:
    """Runs camera sensor analysis and generates aggregate CSV"""

    # Default camera specifications for scanning
    DEFAULT_SCAN_SPECS = OrderedDict([
        ('Epson R-D1', {'path': 'Epson-R-D1', 'suffix': 'ERF'}),
        ('Leica Q (24MP)', {'path': 'Q-24MP', 'suffix': 'DNG'}),
        ('Leica M11 (36MP)', {'path': 'M11-36MP', 'suffix': 'DNG'}),
        ('Leica M11 (60MP)', {'path': 'M11-60MP', 'suffix': 'DNG'}),
        ('Leica M11 (18MP)', {'path': 'M11-18MP', 'suffix': 'DNG'}),
        ('Leica M10 (24MP)', {'path': 'M10-24MP', 'suffix': 'DNG'}),
        ('Leica M Monochrome', {'path': 'M-Monochrome', 'suffix': 'DNG'}),
        ('Ricoh GR III', {'path': 'Ricoh-GRIII', 'suffix': 'DNG'}),
        ('Leica CL (24MP)', {'path': 'CL-24MP', 'suffix': 'DNG'}),
        ('Leica Q3 (36MP)', {'path': 'Q3-36MP', 'suffix': 'DNG'}),
        ('Leica SL2-S (24MP)', {'path': 'SL2-S-24MP', 'suffix': 'DNG'}),
        ('Ricoh GXR', {'path': 'Ricoh-GXR', 'suffix': 'DNG'}),
    ])

    def __init__(self):
        """Initialize analysis runner"""
        self.config = get_config()
        self.analysis: Optional[Analysis] = None
        self.scan_results: Optional[Dict] = None

    def initialize_analysis(self) -> None:
        """Initialize Analysis object with source directory"""
        source_dir = self.config.get_source_dir()
        if not source_dir or not source_dir.exists():
            raise ValueError(
                f"Source directory not found: {source_dir}\n"
                "Please set source directory in Settings menu."
            )

        self.analysis = Analysis(str(source_dir))

    def scan_cameras(self, scan_specs: Optional[OrderedDict] = None,
                    progress_callback=None) -> Dict:
        """
        Scan cameras and analyze images.

        Args:
            scan_specs: Camera scan specifications (uses default if None)
            progress_callback: Optional callback function for progress updates

        Returns:
            Dictionary of scan results by camera name
        """
        if self.analysis is None:
            self.initialize_analysis()

        if scan_specs is None:
            scan_specs = self.DEFAULT_SCAN_SPECS

        # Execute scans
        if progress_callback:
            progress_callback("Starting camera scans...")

        self.scan_results = self.analysis.scan(scan_specs)

        if progress_callback:
            progress_callback(f"Scanned {len(scan_specs)} cameras")

        return self.scan_results

    def create_aggregate_data(self, camera_names: Optional[List[str]] = None,
                             progress_callback=None) -> None:
        """
        Create aggregate data from scan results.

        Args:
            camera_names: List of camera names to include (all if None)
            progress_callback: Optional callback for progress updates
        """
        if self.scan_results is None:
            raise ValueError("Must run scan_cameras() first")

        if camera_names is None:
            # Use all cameras from scan results
            camera_names = list(self.scan_results.keys())

        if progress_callback:
            progress_callback("Creating aggregate data...")

        # Create aggregate data
        self.analysis.create_aggregate(camera_names)

        if progress_callback:
            progress_callback("Aggregate data created")

    def save_to_database(self, progress_callback=None, limit=None) -> int:
        """
        Save analysis results to database.

        Args:
            progress_callback: Optional callback for progress updates
            limit: Optional limit on number of images to save

        Returns:
            Number of images saved
        """
        if self.scan_results is None:
            raise ValueError("Must run scan_cameras() first")

        db = get_db_manager()
        images_saved = 0

        if progress_callback:
            progress_callback("Saving to database...")

        # Process each camera's results
        for camera_name, sensor_list in self.scan_results.items():
            # Apply limit if specified
            if limit and images_saved >= limit:
                if progress_callback:
                    progress_callback(f"Reached limit of {limit} images")
                break
            if progress_callback:
                progress_callback(f"Processing {camera_name}...")

            for sensor in sensor_list:
                # Check limit
                if limit and images_saved >= limit:
                    break

                try:
                    # Get image file path
                    file_path = Path(sensor.file)

                    if not file_path.exists():
                        continue

                    # Get EXIF data
                    with get_exiftool_helper() as et:
                        exif_list = et.get_metadata([str(file_path)])
                        exif_data = exif_list[0] if exif_list else {}

                    # Extract camera info
                    camera_make = exif_data.get('EXIF:Make', 'Unknown')
                    camera_model = camera_name
                    camera_serial = exif_data.get('EXIF:SerialNumber')

                    # Extract image dimensions
                    xdim = sensor.xdim
                    ydim = sensor.ydim

                    # Insert image record
                    image_id = db.insert_image(
                        file_path=file_path,
                        xdim=xdim,
                        ydim=ydim,
                        camera_make=camera_make,
                        camera_model=camera_model,
                        camera_serial=camera_serial
                    )

                    # Insert noise analysis results
                    db.insert_analysis_results(
                        image_id=image_id,
                        ev=sensor.ev
                    )

                    # Insert EXIF data with exposure settings and levels
                    db.insert_exif_data(
                        image_id,
                        exif_data,
                        iso=sensor.iso,
                        exposure_time=sensor.time,
                        black_level=sensor.black_level,
                        white_level=sensor.white_level
                    )

                    images_saved += 1

                    if images_saved % 10 == 0 and progress_callback:
                        progress_callback(f"Saved {images_saved} images...")

                except Exception as e:
                    if progress_callback:
                        progress_callback(f"Error processing {file_path.name}: {e}")
                    continue

        if progress_callback:
            progress_callback(f"Saved {images_saved} images to database")

        return images_saved

    def run_full_analysis(self, scan_specs: Optional[OrderedDict] = None,
                         camera_names: Optional[List[str]] = None,
                         progress_callback=None,
                         limit=None) -> int:
        """
        Run complete analysis: scan and save to database.

        Args:
            scan_specs: Camera scan specifications
            camera_names: Camera names to include (not used for database)
            progress_callback: Optional callback for progress updates
            limit: Optional limit on number of images to analyze

        Returns:
            Number of images analyzed and saved
        """
        try:
            # Step 1: Initialize
            if progress_callback:
                progress_callback("Initializing analysis...")
            self.initialize_analysis()

            # Step 2: Scan cameras
            if progress_callback:
                progress_callback("Scanning cameras...")
            self.scan_cameras(scan_specs, progress_callback)

            # Step 3: Save to database
            if progress_callback:
                msg = "Saving to database..."
                if limit:
                    msg += f" (limit: {limit})"
                progress_callback(msg)
            images_saved = self.save_to_database(progress_callback, limit=limit)

            if progress_callback:
                progress_callback(f"✓ Analysis complete! Saved {images_saved} images to database")

            return images_saved

        except Exception as e:
            if progress_callback:
                progress_callback(f"✗ Error: {str(e)}")
            raise

    def scan_images_to_database(self, progress_callback=None, limit=None) -> int:
        """
        Scan images in source directory and add to database without analysis.

        Args:
            progress_callback: Optional callback for progress updates
            limit: Optional limit on number of images to process

        Returns:
            Number of images added to database
        """
        source_dir = self.config.get_source_dir()
        if not source_dir or not source_dir.exists():
            raise ValueError(
                f"Source directory not found: {source_dir}\n"
                "Please set source directory in Settings menu."
            )

        db = get_db_manager()
        images_added = 0
        images_skipped = 0

        if progress_callback:
            progress_callback("Scanning source directory...")

        # Find all DNG and ERF files recursively
        image_extensions = ['.dng', '.DNG', '.erf', '.ERF']
        image_files = []
        for ext in image_extensions:
            image_files.extend(source_dir.rglob(f'*{ext}'))

        # Apply limit if specified
        if limit:
            image_files = image_files[:limit]

        total_files = len(image_files)
        if progress_callback:
            msg = f"Found {total_files} image files"
            if limit:
                msg += f" (limited to {limit})"
            progress_callback(msg)

        # Process each image file
        for idx, file_path in enumerate(image_files):
            if progress_callback and idx % 10 == 0:
                progress_callback(f"Processing {idx + 1}/{total_files}...")

            try:
                # Check if image already exists in database
                existing = db.get_image_by_path(file_path)
                if existing:
                    images_skipped += 1
                    continue

                # Get EXIF data
                with get_exiftool_helper() as et:
                    exif_list = et.get_metadata([str(file_path)])
                    exif_data = exif_list[0] if exif_list else {}

                # Extract basic image info
                camera_make = exif_data.get('EXIF:Make', 'Unknown')
                camera_model = exif_data.get('EXIF:Model', 'Unknown')
                camera_serial = exif_data.get('EXIF:SerialNumber')

                # Get image dimensions
                xdim = exif_data.get('EXIF:ImageWidth') or exif_data.get('File:ImageWidth')
                ydim = exif_data.get('EXIF:ImageHeight') or exif_data.get('File:ImageHeight')

                if not xdim or not ydim:
                    # Try SubIFD dimensions
                    xdim = exif_data.get('SubIFD:ImageWidth')
                    ydim = exif_data.get('SubIFD:ImageHeight')

                if not xdim or not ydim:
                    if progress_callback:
                        progress_callback(f"⚠ Skipping {file_path.name}: No dimensions found")
                    images_skipped += 1
                    continue

                # Insert image record
                image_id = db.insert_image(
                    file_path=file_path,
                    xdim=int(xdim),
                    ydim=int(ydim),
                    camera_make=camera_make,
                    camera_model=camera_model,
                    camera_serial=camera_serial
                )

                # Insert EXIF data (will extract ISO/exposure from exif_dict)
                db.insert_exif_data(image_id, exif_data)

                images_added += 1

            except Exception as e:
                if progress_callback:
                    progress_callback(f"⚠ Error processing {file_path.name}: {e}")
                continue

        if progress_callback:
            progress_callback(
                f"✓ Scan complete! Added {images_added} images, skipped {images_skipped}"
            )

        return images_added

    def quick_scan_images_to_database(self, progress_callback=None, limit=None) -> Dict[str, int]:
        """
        Quick scan using checksums to skip existing images.

        Args:
            progress_callback: Optional callback for progress updates
            limit: Optional limit on number of images to process

        Returns:
            Dictionary with 'added' and 'skipped' counts
        """
        source_dir = self.config.get_source_dir()
        if not source_dir or not source_dir.exists():
            raise ValueError(
                f"Source directory not found: {source_dir}\n"
                "Please set source directory in Settings menu."
            )

        db = get_db_manager()
        images_added = 0
        images_skipped = 0

        if progress_callback:
            progress_callback("Quick scanning source directory...")

        # Find all DNG and ERF files recursively
        image_extensions = ['.dng', '.DNG', '.erf', '.ERF']
        image_files = []
        for ext in image_extensions:
            image_files.extend(source_dir.rglob(f'*{ext}'))

        # Apply limit if specified
        if limit:
            image_files = image_files[:limit]

        total_files = len(image_files)
        if progress_callback:
            msg = f"Found {total_files} image files"
            if limit:
                msg += f" (limited to {limit})"
            progress_callback(msg)

        # Process each image file
        for idx, file_path in enumerate(image_files):
            if progress_callback and idx % 50 == 0:
                progress_callback(f"Checking {idx + 1}/{total_files}...")

            try:
                # Calculate file hash
                file_hash = db.calculate_file_hash(file_path)

                # Check if image with this hash already exists
                existing = db.get_image_by_hash(file_hash)
                if existing:
                    images_skipped += 1
                    continue

                # Get EXIF data
                with get_exiftool_helper() as et:
                    exif_list = et.get_metadata([str(file_path)])
                    exif_data = exif_list[0] if exif_list else {}

                # Extract basic image info
                camera_make = exif_data.get('EXIF:Make', 'Unknown')
                camera_model = exif_data.get('EXIF:Model', 'Unknown')
                camera_serial = exif_data.get('EXIF:SerialNumber')

                # Get image dimensions
                xdim = exif_data.get('EXIF:ImageWidth') or exif_data.get('File:ImageWidth')
                ydim = exif_data.get('EXIF:ImageHeight') or exif_data.get('File:ImageHeight')

                if not xdim or not ydim:
                    # Try SubIFD dimensions
                    xdim = exif_data.get('SubIFD:ImageWidth')
                    ydim = exif_data.get('SubIFD:ImageHeight')

                if not xdim or not ydim:
                    if progress_callback:
                        progress_callback(f"⚠ Skipping {file_path.name}: No dimensions found")
                    images_skipped += 1
                    continue

                # Insert image record
                image_id = db.insert_image(
                    file_path=file_path,
                    xdim=int(xdim),
                    ydim=int(ydim),
                    camera_make=camera_make,
                    camera_model=camera_model,
                    camera_serial=camera_serial
                )

                # Insert EXIF data (will extract ISO/exposure from exif_dict)
                db.insert_exif_data(image_id, exif_data)

                images_added += 1

                if progress_callback and images_added % 10 == 0:
                    progress_callback(f"✓ Added {images_added}, skipped {images_skipped}")

            except Exception as e:
                if progress_callback:
                    progress_callback(f"⚠ Error processing {file_path.name}: {e}")
                images_skipped += 1
                continue

        if progress_callback:
            progress_callback(
                f"✓ Quick scan complete! Added {images_added} new images, skipped {images_skipped} existing"
            )

        return {'added': images_added, 'skipped': images_skipped}

    def load_new_images(self, progress_callback=None, limit=20, cancel_flag=None) -> Dict[str, int]:
        """
        Load new images with full analysis (checksum-based duplicate detection + analysis).

        Scans source directory for images, checks if they exist in database using checksum,
        and performs full analysis on new images. Also re-analyzes existing images to update
        metadata and calculations with corrected white_level values.

        Args:
            progress_callback: Optional callback for progress updates
            limit: Optional limit on number of images to process
            cancel_flag: Optional callable that returns True if cancellation is requested

        Returns:
            Dictionary with 'added', 'updated', and 'skipped' counts
        """
        source_dir = self.config.get_source_dir()
        if not source_dir or not source_dir.exists():
            raise ValueError(
                f"Source directory not found: {source_dir}\n"
                "Please set source directory in Settings menu."
            )

        db = get_db_manager()
        images_added = 0
        images_skipped = 0

        if progress_callback:
            progress_callback("Building file list: Searching source directory for DNG and ERF files...")

        # Find all DNG and ERF files recursively (this can take time for large directories)
        image_extensions = ['.dng', '.DNG', '.erf', '.ERF']
        image_files = []
        for ext in image_extensions:
            if progress_callback:
                progress_callback(f"Building file list: Searching for *{ext} files...")
            image_files.extend(source_dir.rglob(f'*{ext}'))

        # Check for cancellation after file list is built
        if cancel_flag and cancel_flag():
            if progress_callback:
                progress_callback("Load cancelled by user")
            return {'added': images_added, 'skipped': images_skipped}

        # Apply limit if specified
        if limit:
            image_files = image_files[:limit]

        total_files = len(image_files)
        if progress_callback:
            msg = f"File list complete: Found {total_files} image files"
            if limit:
                msg += f" (limited to {limit})"
            msg += ". Starting analysis..."
            progress_callback(msg)

        # Calculate padding width for numbers
        num_width = len(str(total_files))

        # Process each image file
        for idx, file_path in enumerate(image_files):
            # Check for cancellation
            if cancel_flag and cancel_flag():
                if progress_callback:
                    progress_callback("Load cancelled by user")
                return {'added': images_added, 'skipped': images_skipped}

            current = idx + 1
            remaining = total_files - idx

            # Show which file we're checking
            if progress_callback:
                progress_callback(f"Loading: Checking {current}/{total_files} - {file_path.name}")

            try:
                # Calculate file hash
                file_hash = db.calculate_file_hash(file_path)

                # Check if image with this hash already exists
                existing = db.get_image_by_hash(file_hash)

                if existing is not None:
                    # Image already exists in database - skip it
                    logger.info(f"Skipping existing image: {file_path.name} (ID: {existing['id']})")
                    if progress_callback:
                        progress_callback(f"Loading: Skipped {current}/{total_files} - {file_path.name} (already in database)")
                    images_skipped += 1
                    continue

                # New image - analyze it
                logger.info(f"New image found: {file_path.name}")
                if progress_callback:
                    progress_callback(f"Loading: Analyzing {current}/{total_files} - {file_path.name}")

                # Get EXIF data
                with get_exiftool_helper() as et:
                    exif_list = et.get_metadata([str(file_path)])
                    exif_data = exif_list[0] if exif_list else {}
                    # Log EXIF keys related to white level
                    white_keys = [k for k in exif_data.keys() if 'white' in k.lower() or 'bits' in k.lower()]
                    logger.info(f"EXIF keys with 'white' or 'bits': {white_keys}")

                # Process raw file for noise analysis
                import rawpy
                import numpy as np

                raw = rawpy.imread(str(file_path))
                image = raw.raw_image.copy()

                # Get camera information for crop lookup
                camera_make = exif_data.get('EXIF:Make', 'Unknown')
                camera_model = exif_data.get('EXIF:Model', 'Unknown')
                camera_serial = exif_data.get('EXIF:SerialNumber')

                # Get or create camera to get camera_id for crop lookup
                camera_id = db.get_or_create_camera(camera_make, camera_model, camera_serial)

                # Apply crop from database if available, otherwise use hardcoded CAMERA_CROPS
                crop_applied = False
                camera_attrs = db.get_camera_attributes(camera_id)

                if camera_attrs:
                    x_min = camera_attrs.get('x_min')
                    x_max = camera_attrs.get('x_max')
                    y_min = camera_attrs.get('y_min')
                    y_max = camera_attrs.get('y_max')

                    if all(v is not None for v in [x_min, x_max, y_min, y_max]):
                        logger.info(f"Applying database crop for {camera_model}: x[{x_min}:{x_max+1}], y[{y_min}:{y_max+1}]")
                        image = image[y_min:y_max+1, x_min:x_max+1]
                        crop_applied = True

                # Fall back to hardcoded crops if no database crop
                if not crop_applied and camera_model in Sensor.CAMERA_CROPS:
                    logger.info(f"Applying hardcoded crop for {camera_model}")
                    crop = Sensor.CAMERA_CROPS[camera_model]
                    image = image[crop]

                # Calculate noise statistics
                noise_std = float(np.std(image))
                noise_mean = float(np.mean(image))

                # Get black and white levels from raw file first, then EXIF as fallback
                # Try to get from raw file (most accurate)
                try:
                    black_level = raw.black_level_per_channel[0] if hasattr(raw, 'black_level_per_channel') else None
                    logger.info(f"Black level from raw: {black_level}")
                except Exception as e:
                    logger.warning(f"Failed to get black_level from raw: {e}")
                    black_level = None

                try:
                    white_level = raw.camera_whitelevel_per_channel[0] if hasattr(raw, 'camera_whitelevel_per_channel') else None
                    logger.info(f"White level from raw: {white_level}")
                except Exception as e:
                    logger.warning(f"Failed to get white_level from raw: {e}")
                    white_level = None

                # Fallback to EXIF if not available in raw
                if black_level is None:
                    black_level = exif_data.get('SubIFD:BlackLevel')
                    logger.info(f"Black level from EXIF SubIFD:BlackLevel: {black_level}")
                    if black_level is None:
                        black_level = exif_data.get('EXIF:BlackLevel')
                        logger.info(f"Black level from EXIF EXIF:BlackLevel: {black_level}")
                    if black_level is None:
                        black_level = 0
                        logger.info(f"Using default black_level: {black_level}")
                    elif isinstance(black_level, str):
                        black_level = int(black_level.split()[0])

                if white_level is None:
                    white_level = exif_data.get('EXIF:WhiteLevel')
                    logger.info(f"White level from EXIF EXIF:WhiteLevel: {white_level}")
                    if white_level is None:
                        # Try SubIFD as fallback
                        white_level = exif_data.get('SubIFD:WhiteLevel')
                        logger.info(f"White level from EXIF SubIFD:WhiteLevel: {white_level}")
                    if white_level is None:
                        # Last resort: calculate from BitsPerSample
                        bits_per_sample = exif_data.get('EXIF:BitsPerSample')
                        if bits_per_sample is None:
                            bits_per_sample = exif_data.get('SubIFD:BitsPerSample')
                        logger.info(f"BitsPerSample from EXIF: {bits_per_sample}")
                        if bits_per_sample is not None:
                            white_level = 2 ** int(bits_per_sample) - 1
                            logger.info(f"Calculated white_level from BitsPerSample: {white_level}")
                        else:
                            # Set to NaN to track missing data
                            white_level = np.nan
                            logger.warning(f"No white_level found, setting to nan")

                # Calculate EV: log2((white_level - black_level) / std)
                logger.info(f"EV calculation for {file_path.name}: white_level={white_level}, black_level={black_level}, noise_std={noise_std}")
                if not np.isnan(white_level) and noise_std > 0:
                    ev = np.log((white_level - black_level) / noise_std) / np.log(2)
                    logger.info(f"Calculated EV={ev}")
                else:
                    ev = np.nan
                    logger.warning(f"EV is nan for {file_path.name}: white_level_is_nan={np.isnan(white_level)}, noise_std={noise_std}")

                # Get exposure settings
                iso = exif_data.get('EXIF:ISO')
                exposure_time = exif_data.get('EXIF:ExposureTime')

                raw.close()

                # Extract camera info
                camera_make = exif_data.get('EXIF:Make', 'Unknown')
                camera_model = exif_data.get('EXIF:Model', 'Unknown')
                camera_serial = exif_data.get('EXIF:SerialNumber')

                # Get image dimensions from EXIF
                xdim = exif_data.get('EXIF:ImageWidth') or exif_data.get('File:ImageWidth')
                ydim = exif_data.get('EXIF:ImageHeight') or exif_data.get('File:ImageHeight')

                if not xdim or not ydim:
                    # Try SubIFD dimensions
                    xdim = exif_data.get('SubIFD:ImageWidth')
                    ydim = exif_data.get('SubIFD:ImageHeight')

                # Send updated progress with file details
                if progress_callback and xdim and ydim and iso:
                    megapixels = (xdim * ydim) / 1_000_000.0
                    exposure_str = f"1/{round(1/exposure_time)}s" if exposure_time and exposure_time > 0 else "N/A"
                    progress_callback(f"Loading: Analyzing {current}/{total_files} - {file_path.name}|ISO{iso}|{exposure_str}|{megapixels:.1f}MP")

                if not xdim or not ydim:
                    if progress_callback:
                        progress_callback(f"⚠ Skipping {file_path.name}: No dimensions found")
                    images_skipped += 1
                    continue

                # Insert new image record
                # Insert new image record
                image_id = db.insert_image(
                    file_path=file_path,
                    xdim=int(xdim),
                    ydim=int(ydim),
                    camera_make=camera_make,
                    camera_model=camera_model,
                    camera_serial=camera_serial
                )

                # Insert analysis results with calculated values
                db.insert_analysis_results(
                    image_id=image_id,
                    ev=float(ev) if not np.isnan(ev) else None,
                    noise_std=noise_std,
                    noise_mean=noise_mean
                )

                # Insert EXIF data with exposure settings and levels
                db.insert_exif_data(
                    image_id,
                    exif_data,
                    iso=iso,
                    exposure_time=exposure_time,
                    black_level=black_level,
                    white_level=white_level
                )

                images_added += 1

                if progress_callback and images_added % 10 == 0:
                    progress_callback(f"[{current:>{num_width}}/{total_files}] ✓ Added {images_added}, skipped {images_skipped}")

            except Exception as e:
                logger.error(f"Error processing {file_path.name}: {e}", exc_info=True)
                if progress_callback:
                    progress_callback(f"⚠ Error processing {file_path.name}: {e}")
                images_skipped += 1
                continue

        if progress_callback:
            progress_callback(
                f"✓ Load complete! Added {images_added} new images, skipped {images_skipped} existing images"
            )

        return {'added': images_added, 'skipped': images_skipped}

    def rescan_database(self, progress_callback=None, reanalyze_existing=True, add_new_images=True, cancel_flag=None) -> Dict[str, int]:
        """
        Rescan database: remove missing images, re-analyze existing, optionally add new images.

        Args:
            progress_callback: Optional callback for progress updates
            reanalyze_existing: If True, recalculate analysis for existing images
            add_new_images: If True, scan for and add new images
            cancel_flag: Optional callable that returns True if cancellation is requested

        Returns:
            Dictionary with 'removed', 'reanalyzed', 'added', and 'skipped' counts
        """
        source_dir = self.config.get_source_dir()
        if not source_dir or not source_dir.exists():
            raise ValueError(
                f"Source directory not found: {source_dir}\n"
                "Please set source directory in Settings menu."
            )

        db = get_db_manager()
        images_removed = 0
        images_reanalyzed = 0
        images_added = 0
        images_skipped = 0

        # Step 1: Check existing database images and remove missing ones
        if progress_callback:
            progress_callback("Checking existing database images...")

        # Get all images from database
        with db.get_connection() as conn:
            cursor = conn.execute("SELECT id, file_path FROM images")
            db_images = cursor.fetchall()

        total_db_images = len(db_images)
        if progress_callback:
            progress_callback(f"Found {total_db_images} images in database")

        # Check each database image
        for idx, row in enumerate(db_images):
            # Check for cancellation
            if cancel_flag and cancel_flag():
                if progress_callback:
                    progress_callback("Rescan cancelled by user")
                return {'removed': images_removed, 'reanalyzed': images_reanalyzed, 'added': images_added, 'skipped': images_skipped}

            image_id = row['id']
            file_path = Path(row['file_path'])
            current = idx + 1

            # Check if file exists
            if not file_path.exists():
                # File missing - remove from database
                try:
                    with db.get_connection() as conn:
                        conn.execute("DELETE FROM exif_data WHERE image_id = ?", (image_id,))
                        conn.execute("DELETE FROM analysis_results WHERE image_id = ?", (image_id,))
                        conn.execute("DELETE FROM images WHERE id = ?", (image_id,))
                    images_removed += 1
                except Exception as e:
                    if progress_callback:
                        progress_callback(f"Database Check: Image {current}/{total_db_images} - Error removing {file_path.name}")
            elif reanalyze_existing:
                # File exists - optionally re-analyze it
                try:
                    # Get EXIF data
                    with get_exiftool_helper() as et:
                        exif_list = et.get_metadata([str(file_path)])
                        exif_data = exif_list[0] if exif_list else {}

                    # Get info for status message
                    camera_model = exif_data.get('EXIF:Model', 'Unknown')
                    iso = exif_data.get('EXIF:ISO', 'N/A')
                    exposure_time = exif_data.get('EXIF:ExposureTime')
                    if exposure_time and exposure_time > 0:
                        # Format exposure: <1s as "1/Xs", >=1s as "Xs"
                        if exposure_time < 1:
                            exposure_setting = f"1/{round(1.0/exposure_time)}s"
                        elif exposure_time == int(exposure_time):
                            exposure_setting = f"{int(exposure_time)}s"
                        else:
                            exposure_setting = f"{exposure_time:.1f}s"
                    else:
                        exposure_setting = 'N/A'

                    # Show progress with detailed info
                    if progress_callback:
                        progress_callback(f"Database Check: Image {current}/{total_db_images} - {camera_model} | ISO {iso} | {exposure_setting}")

                    # Process raw file for noise analysis
                    import rawpy
                    import numpy as np

                    raw = rawpy.imread(str(file_path))
                    image = raw.raw_image.copy()

                    # Get camera_id for this image to look up crop settings
                    with db.get_connection() as conn:
                        cursor = conn.execute("SELECT camera_id FROM images WHERE id = ?", (image_id,))
                        result = cursor.fetchone()
                        camera_id = result['camera_id'] if result else None

                    # Apply crop from database if available, otherwise use hardcoded CAMERA_CROPS
                    crop_applied = False
                    if camera_id:
                        camera_attrs = db.get_camera_attributes(camera_id)
                        if camera_attrs:
                            x_min = camera_attrs.get('x_min')
                            x_max = camera_attrs.get('x_max')
                            y_min = camera_attrs.get('y_min')
                            y_max = camera_attrs.get('y_max')

                            if all(v is not None for v in [x_min, x_max, y_min, y_max]):
                                image = image[y_min:y_max+1, x_min:x_max+1]
                                crop_applied = True

                    # Fall back to hardcoded crops if no database crop
                    if not crop_applied and camera_model in Sensor.CAMERA_CROPS:
                        crop = Sensor.CAMERA_CROPS[camera_model]
                        image = image[crop]

                    # Calculate noise statistics
                    noise_std = float(np.std(image))
                    noise_mean = float(np.mean(image))

                    # Get black and white levels from raw file first, then EXIF as fallback
                    # Try to get from raw file (most accurate)
                    try:
                        black_level = raw.black_level_per_channel[0] if hasattr(raw, 'black_level_per_channel') else None
                    except:
                        black_level = None

                    try:
                        white_level = raw.camera_whitelevel_per_channel[0] if hasattr(raw, 'camera_whitelevel_per_channel') else None
                    except:
                        white_level = None

                    # Fallback to EXIF if not available in raw
                    if black_level is None:
                        black_level = exif_data.get('SubIFD:BlackLevel')
                        if black_level is None:
                            black_level = 0

                    if white_level is None:
                        white_level = exif_data.get('EXIF:WhiteLevel')
                        if white_level is None:
                            # Try SubIFD as fallback
                            white_level = exif_data.get('SubIFD:WhiteLevel')
                        if white_level is None:
                            # Last resort: calculate from BitsPerSample
                            bits_per_sample = exif_data.get('EXIF:BitsPerSample')
                            if bits_per_sample is None:
                                bits_per_sample = exif_data.get('SubIFD:BitsPerSample')
                            if bits_per_sample is not None:
                                white_level = 2 ** int(bits_per_sample) - 1
                            else:
                                # Set to NaN to track missing data
                                white_level = np.nan

                    # Calculate EV: log2((white_level - black_level) / std)
                    if noise_std > 0 and not np.isnan(white_level):
                        ev = np.log2((white_level - black_level) / noise_std)
                    else:
                        ev = None

                    # Update analysis results and EXIF data
                    if ev is not None:
                        with db.get_connection() as conn:
                            # Update analysis results
                            conn.execute(
                                "UPDATE analysis_results SET ev = ?, noise_std = ?, noise_mean = ? WHERE image_id = ?",
                                (float(ev), noise_std, noise_mean, image_id)
                            )
                            # Update EXIF data with refreshed black_level and white_level
                            conn.execute(
                                "UPDATE exif_data SET black_level = ?, white_level = ? WHERE image_id = ?",
                                (black_level, white_level, image_id)
                            )
                        images_reanalyzed += 1

                except Exception as e:
                    if progress_callback:
                        progress_callback(f"Database Check: Image {current}/{total_db_images} - Error: {file_path.name}")

        if progress_callback:
            progress_callback(f"Database check complete: {images_removed} removed, {images_reanalyzed} re-analyzed")

        # Step 2: Scan for new images (optional)
        if add_new_images:
            if progress_callback:
                progress_callback("Building file list: Searching source directory for DNG and ERF files...")

            # Find all DNG and ERF files recursively (this can take time for large directories)
            image_extensions = ['.dng', '.DNG', '.erf', '.ERF']
            image_files = []
            for ext in image_extensions:
                if progress_callback:
                    progress_callback(f"Building file list: Searching for *{ext} files...")
                image_files.extend(source_dir.rglob(f'*{ext}'))

            total_files = len(image_files)
            if progress_callback:
                progress_callback(f"File list complete: Found {total_files} image files. Starting analysis...")

            # Check for cancellation before processing
            if cancel_flag and cancel_flag():
                if progress_callback:
                    progress_callback("Rescan cancelled by user")
                return {'removed': images_removed, 'reanalyzed': images_reanalyzed, 'added': images_added, 'skipped': images_skipped}

            # Calculate padding width for numbers
            num_width = len(str(total_files))

            # Process each image file
            for idx, file_path in enumerate(image_files):
                # Check for cancellation
                if cancel_flag and cancel_flag():
                    if progress_callback:
                        progress_callback("Rescan cancelled by user")
                    return {'removed': images_removed, 'reanalyzed': images_reanalyzed, 'added': images_added, 'skipped': images_skipped}

                current = idx + 1

                try:
                    # Show which file we're checking
                    if progress_callback:
                        progress_callback(f"Scanning Files: Checking {current}/{total_files} - {file_path.name}")

                    # Calculate file hash
                    file_hash = db.calculate_file_hash(file_path)

                    # Check if image with this hash already exists
                    existing = db.get_image_by_hash(file_hash)
                    if existing:
                        images_skipped += 1
                        if progress_callback:
                            progress_callback(f"Scanning Files: Skipped {current}/{total_files} - {file_path.name} (already in database)")
                        continue

                    # New image - get EXIF data for status message
                    with get_exiftool_helper() as et:
                        exif_list = et.get_metadata([str(file_path)])
                        exif_data = exif_list[0] if exif_list else {}

                    # Get info for status message
                    camera_model = exif_data.get('EXIF:Model', 'Unknown')
                    iso = exif_data.get('EXIF:ISO', 'N/A')
                    exposure_time = exif_data.get('EXIF:ExposureTime')
                    if exposure_time and exposure_time > 0:
                        # Format exposure: <1s as "1/Xs", >=1s as "Xs"
                        if exposure_time < 1:
                            exposure_setting = f"1/{round(1.0/exposure_time)}s"
                        elif exposure_time == int(exposure_time):
                            exposure_setting = f"{int(exposure_time)}s"
                        else:
                            exposure_setting = f"{exposure_time:.1f}s"
                    else:
                        exposure_setting = 'N/A'

                    # Show progress with detailed info
                    if progress_callback:
                        progress_callback(f"Scanning Files: Image {current}/{total_files} - {camera_model} | ISO {iso} | {exposure_setting}")

                    # Process raw file for noise analysis
                    import rawpy
                    import numpy as np

                    raw = rawpy.imread(str(file_path))
                    image = raw.raw_image.copy()

                    # Get camera information for crop lookup
                    camera_make = exif_data.get('EXIF:Make', 'Unknown')
                    camera_model = exif_data.get('EXIF:Model', 'Unknown')
                    camera_serial = exif_data.get('EXIF:SerialNumber')

                    # Get or create camera to get camera_id for crop lookup
                    camera_id = db.get_or_create_camera(camera_make, camera_model, camera_serial)

                    # Apply crop from database if available, otherwise use hardcoded CAMERA_CROPS
                    crop_applied = False
                    camera_attrs = db.get_camera_attributes(camera_id)

                    if camera_attrs:
                        x_min = camera_attrs.get('x_min')
                        x_max = camera_attrs.get('x_max')
                        y_min = camera_attrs.get('y_min')
                        y_max = camera_attrs.get('y_max')

                        if all(v is not None for v in [x_min, x_max, y_min, y_max]):
                            image = image[y_min:y_max+1, x_min:x_max+1]
                            crop_applied = True

                    # Fall back to hardcoded crops if no database crop
                    if not crop_applied and camera_model in Sensor.CAMERA_CROPS:
                        crop = Sensor.CAMERA_CROPS[camera_model]
                        image = image[crop]

                    # Calculate noise statistics
                    noise_std = float(np.std(image))
                    noise_mean = float(np.mean(image))

                    # Get black and white levels from raw file first, then EXIF as fallback
                    # Try to get from raw file (most accurate)
                    try:
                        black_level = raw.black_level_per_channel[0] if hasattr(raw, 'black_level_per_channel') else None
                    except:
                        black_level = None

                    try:
                        white_level = raw.camera_whitelevel_per_channel[0] if hasattr(raw, 'camera_whitelevel_per_channel') else None
                    except:
                        white_level = None

                    # Fallback to EXIF if not available in raw
                    if black_level is None:
                        black_level = exif_data.get('SubIFD:BlackLevel')
                        if black_level is None:
                            black_level = 0

                    if white_level is None:
                        white_level = exif_data.get('SubIFD:WhiteLevel')
                        if white_level is None:
                            # Last resort: calculate from BitsPerSample
                            bits_per_sample = exif_data.get('SubIFD:BitsPerSample')
                            if bits_per_sample is not None:
                                white_level = 2 ** int(bits_per_sample) - 1
                            else:
                                # Set to NaN to track missing data
                                white_level = np.nan

                    # Calculate EV: log2((white_level - black_level) / std)
                    if noise_std > 0 and not np.isnan(white_level):
                        ev = np.log2((white_level - black_level) / noise_std)
                    else:
                        ev = None

                    # Get camera info
                    camera_make = exif_data.get('EXIF:Make', 'Unknown')
                    camera_serial = exif_data.get('EXIF:SerialNumber')

                    # Get dimensions from EXIF
                    xdim = exif_data.get('SubIFD:ImageWidth')
                    ydim = exif_data.get('SubIFD:ImageHeight')

                    if not xdim or not ydim:
                        images_skipped += 1
                        continue

                    # Insert image record
                    image_id = db.insert_image(
                        file_path=file_path,
                        xdim=int(xdim),
                        ydim=int(ydim),
                        camera_make=camera_make,
                        camera_model=camera_model,
                        camera_serial=camera_serial
                    )

                    # Insert analysis results with calculated values
                    if ev is not None:
                        db.insert_analysis_results(
                            image_id=image_id,
                            ev=float(ev),
                            noise_std=noise_std,
                            noise_mean=noise_mean
                        )

                    # Insert EXIF data with exposure settings and levels
                    db.insert_exif_data(
                        image_id,
                        exif_data,
                        iso=iso,
                        exposure_time=exposure_time,
                        black_level=black_level,
                        white_level=white_level
                    )

                    images_added += 1

                except Exception as e:
                    if progress_callback:
                        progress_callback(f"Scanning Files: Image {current}/{total_files} - Error: {file_path.name}")
                    images_skipped += 1
                    continue

        if progress_callback:
            progress_callback(
                f"✓ Rescan complete! Removed {images_removed}, re-analyzed {images_reanalyzed}, added {images_added}, skipped {images_skipped}"
            )

        return {
            'removed': images_removed,
            'reanalyzed': images_reanalyzed,
            'added': images_added,
            'skipped': images_skipped
        }

    def get_status(self) -> Dict[str, any]:
        """Get current analysis status"""
        db = get_db_manager()
        db_stats = db.get_stats()

        return {
            'initialized': self.analysis is not None,
            'scanned': self.scan_results is not None,
            'num_cameras': len(self.scan_results) if self.scan_results else 0,
            'source_dir': str(self.config.get_source_dir()),
            'working_dir': str(self.config.get_working_dir()),
            'database': str(db.db_path),
            'db_stats': db_stats
        }


def run_analysis(progress_callback=None) -> int:
    """
    Convenience function to run full analysis with defaults.

    Args:
        progress_callback: Optional callback for progress updates

    Returns:
        Number of images analyzed and saved
    """
    runner = AnalysisRunner()
    return runner.run_full_analysis(progress_callback=progress_callback)
