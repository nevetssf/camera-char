"""
Analysis runner for analyzing raw images and storing results in database.
Uses the existing sensor_camera.Analysis class to scan and analyze images.
"""

from pathlib import Path
from typing import List, Dict, Optional
from collections import OrderedDict
import exiftool

from sensor_camera import Analysis, Sensor
from utils.config_manager import get_config
from utils.db_manager import get_db_manager


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
                    with exiftool.ExifToolHelper() as et:
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
                with exiftool.ExifToolHelper() as et:
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
                with exiftool.ExifToolHelper() as et:
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

    def load_new_images(self, progress_callback=None, limit=None) -> Dict[str, int]:
        """
        Load new images with full analysis (checksum-based duplicate detection + analysis).

        Scans source directory for images, checks if they exist in database using checksum,
        and performs full analysis on new images (EV, noise_std, noise_mean).

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
            progress_callback("Scanning for new images...")

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

        # Calculate padding width for numbers
        num_width = len(str(total_files))

        # Process each image file
        for idx, file_path in enumerate(image_files):
            current = idx + 1
            remaining = total_files - idx

            # Get relative path from source directory
            try:
                relative_path = file_path.relative_to(source_dir)
            except ValueError:
                # Fallback to filename if relative_to fails
                relative_path = file_path.name

            # Show progress every 10 files
            if progress_callback and idx % 10 == 0:
                progress_callback(f"Checking [{current:>{num_width}}/{total_files}] {relative_path}")

            try:
                # Calculate file hash
                file_hash = db.calculate_file_hash(file_path)

                # Check if image with this hash already exists
                existing = db.get_image_by_hash(file_hash)
                if existing:
                    images_skipped += 1
                    continue

                # New image - analyze it
                if progress_callback:
                    progress_callback(f"Analyzing [{current:>{num_width}}/{total_files}] {relative_path}")

                # Get EXIF data
                with exiftool.ExifToolHelper() as et:
                    exif_list = et.get_metadata([str(file_path)])
                    exif_data = exif_list[0] if exif_list else {}

                # Process raw file for noise analysis
                import rawpy
                import numpy as np

                raw = rawpy.imread(str(file_path))
                image = raw.raw_image.copy()

                # Apply camera-specific crop if needed
                camera_model = exif_data.get('EXIF:Model', 'Unknown')
                if camera_model in Sensor.CAMERA_CROPS:
                    crop = Sensor.CAMERA_CROPS[camera_model]
                    image = image[crop]

                # Calculate noise statistics
                noise_std = float(np.std(image))
                noise_mean = float(np.mean(image))

                # Get black and white levels
                black_level = exif_data.get('SubIFD:BlackLevel')
                if black_level is None:
                    black_level = exif_data.get('EXIF:BlackLevel')
                if black_level is None:
                    black_level = raw.black_level_per_channel[0]
                elif isinstance(black_level, str):
                    black_level = int(black_level.split()[0])

                white_level = exif_data.get('SubIFD:WhiteLevel')
                if white_level is None:
                    white_level = 65535  # Default for 16-bit

                # Calculate EV: log2((white_level - black_level) / std)
                ev = np.log((white_level - black_level) / noise_std) / np.log(2)

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

                # Insert analysis results with calculated values
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

                if progress_callback and images_added % 10 == 0:
                    progress_callback(f"[{current:>{num_width}}/{total_files}] ✓ Added {images_added}, skipped {images_skipped}")

            except Exception as e:
                if progress_callback:
                    progress_callback(f"⚠ Error processing {file_path.name}: {e}")
                images_skipped += 1
                continue

        if progress_callback:
            progress_callback(
                f"✓ Load complete! Added {images_added} new images with analysis, skipped {images_skipped} existing"
            )

        return {'added': images_added, 'skipped': images_skipped}

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
