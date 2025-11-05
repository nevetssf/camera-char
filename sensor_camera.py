# Standard modules
import os

# Common 3rd party
import numpy as np
import plotly.express as px
import pandas as pd
from tqdm import tqdm

# Raw-specific modules
import exiftool
import rawpy

# GPU acceleration (optional)
try:
    import cupy as cp
    GPU_AVAILABLE = True
    print("GPU acceleration enabled (CuPy detected)")
except ImportError:
    cp = None
    GPU_AVAILABLE = False
    print("GPU acceleration not available (CuPy not installed)")


class Sensor(object):
    """Analyzes noise characteristics of camera sensors from raw image files."""
    
    # Camera-specific crop regions to remove artifacts
    CAMERA_CROPS = {
        "LEICA Q (Typ 116)": (slice(None), slice(0, 6011)),
        "RICOH GR III": (slice(28, 4052), slice(56, 6088)),
        "LEICA CL": (slice(None), slice(0, 6048)),
        "LEICA Q3": (slice(None), slice(0, 7412)),
        "LEICA SL2-S": (slice(0, 4000), slice(0, 6000)),
    }
    
    def __init__(self, path='.', use_gpu=True):
        """Initialize Sensor with a base path for scanning.
        
        Args:
            path: Base directory path containing camera raw files
            use_gpu: Use GPU acceleration if available (default: True)
        """
        self.path = path
        self.data = None
        self.use_gpu = use_gpu and GPU_AVAILABLE
        
        if use_gpu and not GPU_AVAILABLE:
            print("Warning: GPU requested but not available, falling back to CPU")
    
    def _get_scan_path(self, path):
        """Construct the full scan path from base path and relative path.
        
        Args:
            path: Relative path or None to use base path
            
        Returns:
            Full absolute path for scanning
        """
        if path is None:
            return self.path
        return os.path.join(self.path, path)
    
    def _get_file_list(self, directory, suffix):
        """Get sorted list of raw files with given suffix.
        
        Args:
            directory: Directory to scan
            suffix: File extension to filter by
            
        Returns:
            Sorted list of filenames
        """
        return sorted([
            filename for filename in os.listdir(directory) 
            if filename.upper().endswith(suffix.upper())
        ])
    
    def _extract_black_level(self, metadata, raw):
        """Extract black level from metadata or raw file.
        
        Args:
            metadata: EXIF metadata dictionary
            raw: rawpy RawImage object
            
        Returns:
            Black level value as integer
        """
        black_level = metadata.get('EXIF:BlackLevel')
        if black_level is None:
            black_level = metadata.get('MakerNotes:BlackLevel')
        
        if isinstance(black_level, str):
            return int(black_level.split()[0])
        elif black_level is None:
            return raw.black_level_per_channel[0]
        
        return black_level
    
    def _extract_white_level(self, metadata):
        """Extract white level from metadata.
        
        Args:
            metadata: EXIF metadata dictionary
            
        Returns:
            White level value as integer
        """
        white_level = metadata.get('EXIF:WhiteLevel')
        
        if white_level is None:
            # Assume white level is based on bit depth
            bits = metadata.get('EXIF:BitsPerSample')
            if bits is not None:
                white_level = 2**bits
        
        if isinstance(white_level, str):
            return int(white_level.split()[0])
        
        return white_level
    
    def _extract_camera_name(self, metadata):
        """Extract camera name from metadata.
        
        Args:
            metadata: EXIF metadata dictionary
            
        Returns:
            Camera name string
        """
        camera = metadata.get('EXIF:UniqueCameraModel')
        if camera is None:
            camera = metadata.get('EXIF:Model')
        return camera
    
    def _apply_camera_crop(self, image, camera):
        """Apply camera-specific crop to remove artifacts.
        
        Args:
            image: numpy array of raw image data
            camera: Camera name string
            
        Returns:
            Cropped image array
        """
        if camera in self.CAMERA_CROPS:
            crop = self.CAMERA_CROPS[camera]
            return image[crop[0], crop[1]]
        return image
    
    def _extract_dimensions(self, metadata):
        """Extract image dimensions from metadata.
        
        Args:
            metadata: EXIF metadata dictionary
            
        Returns:
            Tuple of (width, height)
        """
        width = metadata.get('EXIF:ExifImageWidth')
        if width is None:
            width = metadata.get('EXIF:ImageWidth')
        
        height = metadata.get('EXIF:ExifImageHeight')
        if height is None:
            height = metadata.get('EXIF:ImageHeight')
        
        return width, height
    
    def _calculate_image_stats(self, image):
        """Calculate statistical measures of image data.
        
        Uses GPU acceleration if enabled and available.
        
        Args:
            image: numpy array of raw image data
            
        Returns:
            Dictionary with std, mean, min, max values
        """
        if self.use_gpu:
            # Transfer to GPU, compute, and transfer back
            gpu_image = cp.asarray(image)
            stats = {
                'std': float(cp.std(gpu_image)),
                'mean': float(cp.mean(gpu_image)),
                'min': float(cp.min(gpu_image)),
                'max': float(cp.max(gpu_image)),
            }
            # Explicitly free GPU memory
            del gpu_image
        else:
            # CPU computation
            stats = {
                'std': np.std(image),
                'mean': np.mean(image),
                'min': np.min(image),
                'max': np.max(image),
            }
        
        return stats
    
    def _process_raw_file(self, filepath, metadata):
        """Process a single raw file and extract noise characteristics.
        
        Args:
            filepath: Path to raw file
            metadata: EXIF metadata dictionary
            
        Returns:
            Dictionary with processed data for this file
        """
        raw = rawpy.imread(filepath)
        
        # Extract metadata
        black_level = self._extract_black_level(metadata, raw)
        white_level = self._extract_white_level(metadata)
        camera = self._extract_camera_name(metadata)
        width, height = self._extract_dimensions(metadata)
        
        # Process image
        image = raw.raw_image
        image = self._apply_camera_crop(image, camera)
        stats = self._calculate_image_stats(image)
        
        raw.close()
        
        # Build result dictionary
        return {
            'camera': camera,
            'source': metadata.get('SourceFile'),
            'black_level': black_level,
            'white_level': white_level,
            'width': width,
            'height': height,
            'iso': metadata.get('EXIF:ISO'),
            'time': metadata.get('EXIF:ExposureTime'),
            **stats
        }
    
    def _calculate_exposure_value(self, data):
        """Calculate exposure value (EV) from noise data.
        
        EV = log2((white_level - black_level) / std_dev)
        
        Args:
            data: DataFrame with noise measurements
            
        Returns:
            DataFrame with EV column added
        """
        data['EV'] = data.apply(
            lambda x: np.log((x['white_level'] - x['black_level']) / x['std']) / np.log(2),
            axis='columns'
        )
        return data
    
    def _save_results(self, data, directory):
        """Save scan results to CSV file in the scanned directory.
        
        Args:
            data: DataFrame with scan results
            directory: Directory to save results in
        """
        output_file = os.path.join(directory, 'noise_results.csv')
        data.to_csv(output_file, index=False)
        print(f'Results saved to: {output_file}')
    
    def scan(self, path=None, suffix='DNG', force_rescan=False):
        """Scan a directory for raw files and analyze noise characteristics.
        
        Args:
            path: Relative path from base directory (None to use base path)
            suffix: File extension to scan for (default: 'DNG')
            force_rescan: If True, rescan even if results exist (default: False)
            
        Returns:
            DataFrame with noise analysis results for all scanned files
        """
        full_path = self._get_scan_path(path)
        results_file = os.path.join(full_path, 'noise_results.csv')
        
        # Check if results already exist
        if not force_rescan and os.path.exists(results_file):
            print(f'Loading existing results from: {results_file}')
            data = pd.read_csv(results_file)
            self.data = data
            return data
        
        file_list = self._get_file_list(full_path, suffix)
        
        results = []
        
        with exiftool.ExifToolHelper() as et:
            # Create progress bar
            with tqdm(total=len(file_list), desc='Scanning files', unit='file') as pbar:
                for filename in file_list:
                    # Update progress bar with current filename
                    pbar.set_postfix_str(f'Processing: {filename}')
                    
                    filepath = os.path.join(full_path, filename)
                    metadata = et.get_metadata(filepath)[0]
                    
                    file_data = self._process_raw_file(filepath, metadata)
                    results.append(file_data)
                    
                    # Update progress bar
                    pbar.update(1)
        
        # Create DataFrame and calculate derived metrics
        data = pd.DataFrame(results)
        data = self._calculate_exposure_value(data)
        
        # Store and save results
        self.data = data
        self._save_results(data, full_path)
        
        return data


class Analysis(object):
    """Manages aggregate analysis of multiple camera sensors."""
    
    def __init__(self, base_path='.'):
        """Initialize Analysis with a base path for scanning.
        
        Args:
            base_path: Base directory path containing camera raw files
        """
        self.base_path = base_path
        self.sensor = Sensor(base_path)
        self.scan_results = None
        self.aggregate_data = None
    
    def scan(self, scan_specs, force_rescan=False):
        """Scan multiple cameras according to specifications.
        
        Args:
            scan_specs: OrderedDict with camera names as keys and scan parameters as values
                       Each value should be a dict with 'path' and 'suffix' keys
            force_rescan: If True, rescan even if cached results exist (default: False)
            
        Returns:
            OrderedDict with scan results for each camera
            
        Example:
            >>> from collections import OrderedDict
            >>> specs = OrderedDict([
            ...     ('Leica M11', {'path': 'M11-36MP', 'suffix': 'DNG'}),
            ...     ('Leica Q3', {'path': 'Q3-36MP', 'suffix': 'DNG'}),
            ... ])
            >>> analysis = Analysis('/path/to/data')
            >>> results = analysis.scan(specs)
        """
        from collections import OrderedDict
        
        scan_results = OrderedDict()
        
        for name, params in scan_specs.items():
            print(f"Scanning {name}...")
            # Add force_rescan to params if specified
            scan_params = params.copy()
            scan_params['force_rescan'] = force_rescan
            
            # Scan and store results
            scan_results[name] = self.sensor.scan(**scan_params)
        
        self.scan_results = scan_results
        return scan_results
    
    def create_aggregate(self, camera_list=None):
        """Create aggregate DataFrame from scan results.
        
        Args:
            camera_list: List of camera names to include (default: all scanned cameras)
            
        Returns:
            Combined DataFrame with data from selected cameras
        """
        if self.scan_results is None:
            raise ValueError("No scan results available. Run scan() first.")
        
        # Use all cameras if not specified
        if camera_list is None:
            camera_list = list(self.scan_results.keys())
        
        # Concatenate selected camera data
        data_frames = [self.scan_results[name] for name in camera_list if name in self.scan_results]
        
        if not data_frames:
            raise ValueError("No valid cameras found in scan results")
        
        self.aggregate_data = pd.concat(data_frames, ignore_index=True)
        return self.aggregate_data
    
    def save_aggregate(self, filename='aggregate_analysis.csv'):
        """Save aggregate data to CSV file.
        
        Args:
            filename: Output filename (default: 'aggregate_analysis.csv')
        """
        if self.aggregate_data is None:
            raise ValueError("No aggregate data available. Run create_aggregate() first.")
        
        self.aggregate_data.to_csv(filename, index=False)
        print(f"Aggregate analysis saved to: {filename}")
    
    def get_aliases(self, short_names=None):
        """Create convenient variable aliases for scan results.
        
        Args:
            short_names: Dict mapping camera names to short variable names
                        If None, uses simple numbered aliases
        
        Returns:
            Dictionary of aliases pointing to scan results
        """
        if self.scan_results is None:
            raise ValueError("No scan results available. Run scan() first.")
        
        aliases = {}
        
        if short_names is None:
            # Auto-generate simple aliases
            for i, name in enumerate(self.scan_results.keys()):
                aliases[f'camera_{i}'] = self.scan_results[name]
        else:
            # Use provided mapping
            for full_name, short_name in short_names.items():
                if full_name in self.scan_results:
                    aliases[short_name] = self.scan_results[full_name]
        
        return aliases
    
    def plot_ev_vs_iso(self, data=None, exposure_time=0.004, title=None, height=700, ev_range=None):
        """Create a professional plot of Exposure Value vs ISO for camera comparison.
        
        Args:
            data: DataFrame with camera noise data (default: uses self.aggregate_data)
            exposure_time: Filter data to this exposure time (default: 0.004 = 1/250s)
            title: Custom title for the plot (default: auto-generated)
            height: Plot height in pixels (default: 700)
            ev_range: Tuple of (min, max) for Y-axis range (default: auto-calculated with padding)
            
        Returns:
            Plotly figure object
        """
        # Use aggregate data if not provided
        if data is None:
            if self.aggregate_data is None:
                raise ValueError("No data available. Run create_aggregate() first or provide data.")
            data = self.aggregate_data
        
        # Filter data by exposure time
        filtered_data = data[data['time'] == exposure_time]
        
        # Generate title if not provided
        if title is None:
            shutter_speed = f"1/{int(1/exposure_time)}s" if exposure_time > 0 else "N/A"
            title = f'Camera Sensor Dynamic Range vs ISO Sensitivity<br><sub>Measured at {shutter_speed} shutter speed</sub>'
        
        # Calculate EV range if not provided - add 10% padding
        if ev_range is None:
            ev_min = filtered_data['EV'].min()
            ev_max = filtered_data['EV'].max()
            ev_padding = (ev_max - ev_min) * 0.1
            ev_range = [ev_min - ev_padding, ev_max + ev_padding]
        
        # Create the plot
        fig = px.line(
            filtered_data, 
            x='iso', y='EV', color='camera', 
            markers=True, log_x=True,
            height=height,
            labels={
                'iso': 'ISO Sensitivity',
                'EV': 'Exposure Value (EV)',
                'camera': 'Camera Model'
            },
            title=title
        )
        
        # Update traces for better visibility
        fig.update_traces(
            mode="markers+lines", 
            marker=dict(size=8, line=dict(width=1, color='white')),
            line=dict(width=2.5),
            hovertemplate='%{fullData.name}: %{y:.2f} EV<extra></extra>'
        )
        
        # Update layout for professional appearance
        fig.update_layout(
            hovermode="x unified",
            hoverlabel=dict(bgcolor="white", font_size=12),
            font=dict(family="Arial, sans-serif", size=12),
            title=dict(font=dict(size=18, color='#2c3e50'), x=0.5, xanchor='center'),
            xaxis=dict(
                showgrid=True,
                gridwidth=1,
                gridcolor='rgba(128,128,128,0.2)',
                title_font=dict(size=14, color='#2c3e50'),
                tickfont=dict(size=11),
                hoverformat=',d'  # Format ISO as integer with thousands separator
            ),
            yaxis=dict(
                showgrid=True,
                gridwidth=1,
                gridcolor='rgba(128,128,128,0.2)',
                title_font=dict(size=14, color='#2c3e50'),
                tickfont=dict(size=11),
                range=ev_range
            ),
            legend=dict(
                title=dict(text='Camera Model', font=dict(size=13, color='#2c3e50')),
                font=dict(size=11),
                bgcolor='rgba(255,255,255,0.9)',
                bordercolor='rgba(128,128,128,0.3)',
                borderwidth=1,
                x=1.02,
                y=1,
                xanchor='left',
                yanchor='top'
            ),
            plot_bgcolor='white',
            paper_bgcolor='white',
            margin=dict(l=80, r=200, t=100, b=80)
        )
        
        return fig
