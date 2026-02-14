"""
Plot generator wrapper for sensor_camera.Analysis class.
Provides filtered plotting capabilities for the GUI application.
"""

import pandas as pd
import plotly.graph_objects as go
from typing import List, Optional
from pathlib import Path

# Import existing Analysis class
from sensor_camera import Analysis


class PlotGenerator:
    """Wrapper around Analysis class for generating filtered plots"""

    def __init__(self, base_path: Optional[str] = None):
        """
        Initialize plot generator.

        Args:
            base_path: Base directory path (uses config working dir if None)
        """
        # Get base path from config if not provided
        if base_path is None:
            from utils.config_manager import get_config
            config = get_config()
            base_path = str(config.get_working_dir())

        self.base_path = Path(base_path)
        self.analysis: Optional[Analysis] = None
        self.aggregate_data: Optional[pd.DataFrame] = None
        self._load_data()

    def _load_data(self) -> None:
        """Load aggregate data from database and initialize Analysis"""
        from utils.db_manager import get_db_manager

        db = get_db_manager()
        data_list = db.get_all_analysis_data(include_archived=False)

        # Load aggregate data from database
        if data_list:
            self.aggregate_data = pd.DataFrame(data_list)
        else:
            # Create empty DataFrame with expected columns
            self.aggregate_data = pd.DataFrame(columns=[
                'camera', 'iso', 'exposure_time', 'ev', 'source', 'filename',
                'xdim', 'ydim', 'megapixels', 'bits_per_sample',
                'black_level', 'white_level'
            ])

        # Add 'time' alias for backward compatibility with sensor_camera.Analysis
        if 'exposure_time' in self.aggregate_data.columns and 'time' not in self.aggregate_data.columns:
            self.aggregate_data['time'] = self.aggregate_data['exposure_time']

        # Add 'EV' alias for backward compatibility with sensor_camera.Analysis (expects uppercase)
        if 'ev' in self.aggregate_data.columns and 'EV' not in self.aggregate_data.columns:
            self.aggregate_data['EV'] = self.aggregate_data['ev']

        # Initialize Analysis with base path
        self.analysis = Analysis(base_path=str(self.base_path))

        # Set aggregate data directly
        self.analysis.aggregate_data = self.aggregate_data

    def get_unique_exposure_times(self) -> List[float]:
        """Get list of unique exposure times from data"""
        if self.aggregate_data is None:
            return []
        # Use 'time' column from CSV (exposure_time is an alias)
        time_col = 'time' if 'time' in self.aggregate_data.columns else 'exposure_time'
        return sorted(self.aggregate_data[time_col].unique().tolist())

    def get_unique_isos(self) -> List[int]:
        """Get list of unique ISO values from data"""
        if self.aggregate_data is None:
            return []
        return sorted(self.aggregate_data['iso'].unique().tolist())

    def get_unique_cameras(self) -> List[str]:
        """Get list of unique camera models from data"""
        if self.aggregate_data is None:
            return []
        return sorted(self.aggregate_data['camera'].unique().tolist())

    def generate_ev_vs_iso_plot(self, exposure_time: float,
                               camera_filter: Optional[List[str]] = None) -> go.Figure:
        """
        Generate EV vs ISO plot for a specific exposure time.

        Args:
            exposure_time: Exposure time to plot (seconds)
            camera_filter: List of camera models to include (None = all)

        Returns:
            Plotly Figure object
        """
        if self.analysis is None or self.aggregate_data is None:
            raise RuntimeError("Analysis not initialized")

        # Filter data by camera if specified
        if camera_filter:
            filtered_data = self.aggregate_data[
                self.aggregate_data['camera'].isin(camera_filter)
            ].copy()

            # Ensure aliases are present in filtered data
            if 'exposure_time' in filtered_data.columns and 'time' not in filtered_data.columns:
                filtered_data['time'] = filtered_data['exposure_time']
            if 'ev' in filtered_data.columns and 'EV' not in filtered_data.columns:
                filtered_data['EV'] = filtered_data['ev']

            # Temporarily replace aggregate data
            original_data = self.analysis.aggregate_data
            self.analysis.aggregate_data = filtered_data
        else:
            original_data = None

        # Generate plot using existing Analysis method
        try:
            fig = self.analysis.plot_ev_vs_iso(exposure_time=exposure_time)
        finally:
            # Restore original data if we filtered
            if original_data is not None:
                self.analysis.aggregate_data = original_data

        return fig

    def generate_ev_vs_time_plot(self, iso: int,
                                 camera_filter: Optional[List[str]] = None) -> go.Figure:
        """
        Generate EV vs Time plot for a specific ISO.

        Args:
            iso: ISO value to plot
            camera_filter: List of camera models to include (None = all)

        Returns:
            Plotly Figure object
        """
        if self.analysis is None or self.aggregate_data is None:
            raise RuntimeError("Analysis not initialized")

        # Filter data by camera if specified
        if camera_filter:
            filtered_data = self.aggregate_data[
                self.aggregate_data['camera'].isin(camera_filter)
            ].copy()

            # Ensure aliases are present in filtered data
            if 'exposure_time' in filtered_data.columns and 'time' not in filtered_data.columns:
                filtered_data['time'] = filtered_data['exposure_time']
            if 'ev' in filtered_data.columns and 'EV' not in filtered_data.columns:
                filtered_data['EV'] = filtered_data['ev']

            # Temporarily replace aggregate data
            original_data = self.analysis.aggregate_data
            self.analysis.aggregate_data = filtered_data
        else:
            original_data = None

        # Generate plot using existing Analysis method
        try:
            fig = self.analysis.plot_ev_vs_time(iso=iso)
        finally:
            # Restore original data if we filtered
            if original_data is not None:
                self.analysis.aggregate_data = original_data

        return fig

    def generate_multi_plot(self, exposure_times: Optional[List[float]] = None,
                           isos: Optional[List[int]] = None,
                           camera_filter: Optional[List[str]] = None) -> go.Figure:
        """
        Generate multi-plot with multiple exposure times or ISOs.

        Args:
            exposure_times: List of exposure times for EV vs ISO plots
            isos: List of ISOs for EV vs Time plots
            camera_filter: List of camera models to include

        Returns:
            Plotly Figure object with subplots
        """
        if self.analysis is None or self.aggregate_data is None:
            raise RuntimeError("Analysis not initialized")

        # Filter data by camera if specified
        if camera_filter:
            filtered_data = self.aggregate_data[
                self.aggregate_data['camera'].isin(camera_filter)
            ].copy()

            # Ensure aliases are present in filtered data
            if 'exposure_time' in filtered_data.columns and 'time' not in filtered_data.columns:
                filtered_data['time'] = filtered_data['exposure_time']
            if 'ev' in filtered_data.columns and 'EV' not in filtered_data.columns:
                filtered_data['EV'] = filtered_data['ev']

            original_data = self.analysis.aggregate_data
            self.analysis.aggregate_data = filtered_data
        else:
            original_data = None

        try:
            if exposure_times:
                # Generate multi-plot for different exposure times
                fig = self.analysis.plot_ev_vs_iso(exposure_time=exposure_times)
            elif isos:
                # Generate multi-plot for different ISOs
                fig = self.analysis.plot_ev_vs_time(iso=isos)
            else:
                raise ValueError("Must specify either exposure_times or isos")
        finally:
            # Restore original data if we filtered
            if original_data is not None:
                self.analysis.aggregate_data = original_data

        return fig

    def reload_data(self) -> None:
        """Reload aggregate data from database"""
        self._load_data()

    def get_data_for_exposure_time(self, exposure_time: float,
                                   camera_filter: Optional[List[str]] = None) -> pd.DataFrame:
        """
        Get filtered data for a specific exposure time.

        Args:
            exposure_time: Exposure time (seconds)
            camera_filter: List of cameras to include

        Returns:
            Filtered DataFrame
        """
        if self.aggregate_data is None:
            return pd.DataFrame()

        # Use 'time' column from CSV
        time_col = 'time' if 'time' in self.aggregate_data.columns else 'exposure_time'
        data = self.aggregate_data[
            self.aggregate_data[time_col] == exposure_time
        ].copy()

        if camera_filter:
            data = data[data['camera'].isin(camera_filter)]

        return data

    def get_data_for_iso(self, iso: int,
                        camera_filter: Optional[List[str]] = None) -> pd.DataFrame:
        """
        Get filtered data for a specific ISO.

        Args:
            iso: ISO value
            camera_filter: List of cameras to include

        Returns:
            Filtered DataFrame
        """
        if self.aggregate_data is None:
            return pd.DataFrame()

        data = self.aggregate_data[
            self.aggregate_data['iso'] == iso
        ].copy()

        if camera_filter:
            data = data[data['camera'].isin(camera_filter)]

        return data

    def export_plot_html(self, fig: go.Figure, output_path: str,
                        include_plotlyjs: str = 'cdn') -> None:
        """
        Export plot to HTML file.

        Args:
            fig: Plotly Figure object
            output_path: Path for output HTML file
            include_plotlyjs: How to include Plotly.js ('cdn', True, False)
        """
        fig.write_html(output_path, include_plotlyjs=include_plotlyjs)

    def export_plot_image(self, fig: go.Figure, output_path: str,
                         width: int = 1200, height: int = 800) -> None:
        """
        Export plot to static image (PNG, JPG, SVG, PDF).

        Args:
            fig: Plotly Figure object
            output_path: Path for output image file
            width: Image width in pixels
            height: Image height in pixels
        """
        # Note: Requires kaleido package
        try:
            fig.write_image(output_path, width=width, height=height)
        except Exception as e:
            raise RuntimeError(f"Failed to export image. Is kaleido installed? Error: {e}")


# Global plot generator instance
_global_generator: Optional[PlotGenerator] = None


def get_plot_generator(base_path: Optional[str] = None) -> PlotGenerator:
    """
    Get or create global plot generator instance.

    Args:
        base_path: Base directory path (uses config if None)

    Returns:
        PlotGenerator instance
    """
    global _global_generator
    if _global_generator is None:
        _global_generator = PlotGenerator(base_path=base_path)
    return _global_generator
