"""
Data model for managing aggregate camera analysis data.
Handles loading data from database and provides filtering capabilities.
"""

import pandas as pd
from typing import List, Optional
from pathlib import Path


class DataModel:
    """Model for camera sensor analysis data from database"""

    def __init__(self):
        """Initialize the data model."""
        self.full_data: Optional[pd.DataFrame] = None
        self.filtered_data: Optional[pd.DataFrame] = None
        self._load_data()

    def _load_data(self) -> None:
        """Load data from database into a pandas DataFrame"""
        from utils.db_manager import get_db_manager

        db = get_db_manager()
        data_list = db.get_all_analysis_data(include_archived=False)

        if not data_list:
            # Create empty DataFrame with expected columns
            self.full_data = pd.DataFrame(columns=[
                'camera', 'iso', 'exposure_time', 'exposure_setting', 'ev',
                'noise_std', 'noise_mean', 'source', 'filename',
                'xdim', 'ydim', 'megapixels', 'bits_per_sample',
                'black_level', 'white_level'
            ])
            self.filtered_data = self.full_data.copy()
            return

        self.full_data = pd.DataFrame(data_list)
        self.filtered_data = self.full_data.copy()

        # Ensure required columns exist
        required_cols = ['camera', 'iso', 'exposure_time']
        missing = [col for col in required_cols if col not in self.full_data.columns]
        if missing:
            raise ValueError(f"Missing required columns: {missing}")

        # Add 'time' alias for backward compatibility
        if 'exposure_time' in self.full_data.columns and 'time' not in self.full_data.columns:
            self.full_data['time'] = self.full_data['exposure_time']
            self.filtered_data['time'] = self.filtered_data['exposure_time']

        # Add calculated 'exposure_setting' column for human-readable exposure times
        if 'exposure_time' in self.full_data.columns:
            self.full_data['exposure_setting'] = self.full_data['exposure_time']
            self.filtered_data['exposure_setting'] = self.filtered_data['exposure_time']

            # Reorder columns to put exposure_setting before exposure_time
            cols = self.full_data.columns.tolist()
            if 'exposure_setting' in cols and 'exposure_time' in cols:
                # Remove exposure_setting from its current position
                cols.remove('exposure_setting')
                # Insert it right before exposure_time
                exp_time_idx = cols.index('exposure_time')
                cols.insert(exp_time_idx, 'exposure_setting')
                # Reorder both dataframes
                self.full_data = self.full_data[cols]
                self.filtered_data = self.filtered_data[cols]

    def get_data(self) -> pd.DataFrame:
        """Get the currently filtered data"""
        return self.filtered_data.copy() if self.filtered_data is not None else pd.DataFrame()

    def reset_filters(self) -> None:
        """Reset all filters to show full dataset"""
        self.filtered_data = self.full_data.copy()

    def filter_by_camera(self, cameras: List[str]) -> None:
        """
        Filter data by camera models.

        Args:
            cameras: List of camera model names to include
        """
        if not cameras:
            self.filtered_data = self.full_data.copy()
            return

        self.filtered_data = self.full_data[
            self.full_data['camera'].isin(cameras)
        ].copy()

    def filter_by_iso(self, iso_values: List[int]) -> None:
        """
        Filter data by ISO values.

        Args:
            iso_values: List of ISO values to include
        """
        if not iso_values:
            self.filtered_data = self.full_data.copy()
            return

        self.filtered_data = self.full_data[
            self.full_data['iso'].isin(iso_values)
        ].copy()

    def filter_by_exposure_time(self, min_time: Optional[float] = None,
                                 max_time: Optional[float] = None) -> None:
        """
        Filter data by exposure time range.

        Args:
            min_time: Minimum exposure time (seconds)
            max_time: Maximum exposure time (seconds)
        """
        data = self.full_data.copy()

        if min_time is not None:
            data = data[data['exposure_time'] >= min_time]

        if max_time is not None:
            data = data[data['exposure_time'] <= max_time]

        self.filtered_data = data

    def filter_combined(self, cameras: Optional[List[str]] = None,
                       iso_values: Optional[List[int]] = None,
                       min_time: Optional[float] = None,
                       max_time: Optional[float] = None) -> None:
        """
        Apply multiple filters at once.

        Args:
            cameras: List of camera models to include
            iso_values: List of ISO values to include
            min_time: Minimum exposure time
            max_time: Maximum exposure time
        """
        data = self.full_data.copy()

        if cameras:
            data = data[data['camera'].isin(cameras)]

        if iso_values:
            data = data[data['iso'].isin(iso_values)]

        if min_time is not None:
            data = data[data['exposure_time'] >= min_time]

        if max_time is not None:
            data = data[data['exposure_time'] <= max_time]

        self.filtered_data = data

    def search(self, query: str, columns: Optional[List[str]] = None) -> None:
        """
        Search for text in specified columns.

        Args:
            query: Search query string
            columns: Columns to search in (default: all string columns)
        """
        if not query:
            return

        data = self.filtered_data if self.filtered_data is not None else self.full_data

        if columns is None:
            # Search in all string/object columns
            columns = data.select_dtypes(include=['object']).columns.tolist()

        # Create mask for rows matching query in any column
        mask = pd.Series([False] * len(data), index=data.index)
        for col in columns:
            if col in data.columns:
                mask |= data[col].astype(str).str.contains(query, case=False, na=False)

        self.filtered_data = data[mask].copy()

    def get_unique_cameras(self) -> List[str]:
        """Get list of unique camera models in the full dataset"""
        if self.full_data is None:
            return []
        return sorted(self.full_data['camera'].unique().tolist())

    def get_unique_isos(self) -> List[int]:
        """Get list of unique ISO values in the full dataset"""
        if self.full_data is None:
            return []
        return sorted(self.full_data['iso'].unique().tolist())

    def get_unique_exposure_times(self) -> List[float]:
        """Get list of unique exposure times in the full dataset"""
        if self.full_data is None:
            return []
        return sorted([x for x in self.full_data['exposure_time'].unique().tolist() if pd.notna(x)])

    def get_unique_bit_depths(self) -> List[int]:
        """Get list of unique bit depths in the full dataset"""
        if self.full_data is None:
            return []
        return sorted([x for x in self.full_data['bits_per_sample'].unique().tolist() if pd.notna(x)])

    def get_unique_megapixels(self) -> List[float]:
        """Get list of unique megapixel values in the full dataset"""
        if self.full_data is None:
            return []
        return sorted([x for x in self.full_data['megapixels'].unique().tolist() if pd.notna(x)])

    def get_row_count(self) -> int:
        """Get the number of rows in filtered data"""
        return len(self.filtered_data) if self.filtered_data is not None else 0

    def get_total_row_count(self) -> int:
        """Get the total number of rows in full dataset"""
        return len(self.full_data) if self.full_data is not None else 0

    def get_row(self, index: int) -> pd.Series:
        """
        Get a specific row from filtered data.

        Args:
            index: Row index

        Returns:
            Row data as Series
        """
        if self.filtered_data is None or index >= len(self.filtered_data):
            raise IndexError(f"Row index {index} out of range")

        return self.filtered_data.iloc[index]

    def filter_by_multiple_fields(self, filters: dict) -> None:
        """
        Filter data by multiple fields.

        Args:
            filters: Dictionary mapping field names to list of values to include
                    e.g. {'camera': ['Leica M11'], 'iso': [100, 200]}
        """
        data = self.full_data.copy()

        for field, values in filters.items():
            if values:  # Only apply if values are selected
                # Special handling: exposure_setting is calculated from exposure_time
                if field == 'exposure_setting':
                    # The values are exposure_time values, filter on exposure_time column
                    data = data[data['exposure_time'].isin(values)]
                else:
                    data = data[data[field].isin(values)]

        self.filtered_data = data

    def export_filtered_data(self, output_path: str) -> None:
        """
        Export filtered data to CSV.

        Args:
            output_path: Path for output CSV file
        """
        if self.filtered_data is None:
            raise ValueError("No data to export")

        self.filtered_data.to_csv(output_path, index=False)
