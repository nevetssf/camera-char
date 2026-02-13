"""
Analysis runner for generating aggregate_analysis.csv from raw images.
Uses the existing sensor_camera.Analysis class to scan and analyze images.
"""

from pathlib import Path
from typing import List, Dict, Optional
from collections import OrderedDict

from sensor_camera import Analysis
from utils.config_manager import get_config


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

    def save_aggregate_csv(self, progress_callback=None) -> Path:
        """
        Save aggregate data to CSV in working directory.

        Args:
            progress_callback: Optional callback for progress updates

        Returns:
            Path to saved CSV file
        """
        if self.analysis is None or self.analysis.aggregate_data is None:
            raise ValueError("Must create aggregate data first")

        # Get output path from config
        output_path = self.config.get_aggregate_csv_path()

        if progress_callback:
            progress_callback(f"Saving to {output_path}...")

        # Save aggregate analysis
        self.analysis.save_aggregate(str(output_path))

        if progress_callback:
            progress_callback(f"Saved: {output_path}")

        return output_path

    def run_full_analysis(self, scan_specs: Optional[OrderedDict] = None,
                         camera_names: Optional[List[str]] = None,
                         progress_callback=None) -> Path:
        """
        Run complete analysis: scan, aggregate, and save.

        Args:
            scan_specs: Camera scan specifications
            camera_names: Camera names to include in aggregate
            progress_callback: Optional callback for progress updates

        Returns:
            Path to generated CSV file
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

            # Step 3: Create aggregate
            if progress_callback:
                progress_callback("Creating aggregate data...")
            self.create_aggregate_data(camera_names, progress_callback)

            # Step 4: Save CSV
            if progress_callback:
                progress_callback("Saving CSV...")
            output_path = self.save_aggregate_csv(progress_callback)

            if progress_callback:
                progress_callback(f"✓ Analysis complete! Saved to: {output_path}")

            return output_path

        except Exception as e:
            if progress_callback:
                progress_callback(f"✗ Error: {str(e)}")
            raise

    def get_status(self) -> Dict[str, any]:
        """Get current analysis status"""
        return {
            'initialized': self.analysis is not None,
            'scanned': self.scan_results is not None,
            'aggregate_ready': (
                self.analysis is not None and
                self.analysis.aggregate_data is not None
            ),
            'num_cameras': len(self.scan_results) if self.scan_results else 0,
            'source_dir': str(self.config.get_source_dir()),
            'working_dir': str(self.config.get_working_dir()),
            'output_csv': str(self.config.get_aggregate_csv_path())
        }


def run_analysis(progress_callback=None) -> Path:
    """
    Convenience function to run full analysis with defaults.

    Args:
        progress_callback: Optional callback for progress updates

    Returns:
        Path to generated CSV file
    """
    runner = AnalysisRunner()
    return runner.run_full_analysis(progress_callback=progress_callback)
