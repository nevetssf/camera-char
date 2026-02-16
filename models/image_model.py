"""
Image model for loading and processing camera raw files and TIFFs.
Handles DNG, ERF, and TIFF formats with metadata extraction.
"""

import rawpy
import numpy as np
from PIL import Image
from pathlib import Path
from typing import Dict, Optional, Tuple, Any

from utils.exiftool_helper import get_exiftool_helper


class ImageModel:
    """Model for loading and processing raw camera files"""

    def __init__(self):
        """Initialize the image model"""
        self.current_image: Optional[np.ndarray] = None
        self.current_metadata: Optional[Dict[str, Any]] = None
        self.current_file_path: Optional[Path] = None

    def load_raw_file(self, file_path: str, fast_preview: bool = False) -> np.ndarray:
        """
        Load a raw DNG or ERF file.

        Args:
            file_path: Path to raw file
            fast_preview: If True, extract embedded JPEG thumbnail for speed

        Returns:
            Image array as numpy ndarray (height, width, channels)
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"Raw file not found: {file_path}")

        with rawpy.imread(str(file_path)) as raw:
            if fast_preview:
                try:
                    # Extract embedded JPEG thumbnail
                    thumb = raw.extract_thumb()
                    if thumb.format == rawpy.ThumbFormat.JPEG:
                        image = Image.open(thumb.data)
                        image_array = np.array(image)
                    else:
                        # Fallback to bitmap thumbnail
                        image_array = thumb.data
                except Exception:
                    # Fallback to postprocessing if thumbnail extraction fails
                    image_array = raw.postprocess(
                        use_camera_wb=True,
                        half_size=True,
                        no_auto_bright=False
                    )
            else:
                # Full quality postprocessing
                image_array = raw.postprocess(
                    use_camera_wb=True,
                    half_size=False,
                    no_auto_bright=False,
                    output_bps=8  # 8-bit output for display
                )

        self.current_image = image_array
        self.current_file_path = file_path
        return image_array

    def load_tiff_file(self, file_path: str) -> np.ndarray:
        """
        Load a TIFF file.

        Args:
            file_path: Path to TIFF file

        Returns:
            Image array as numpy ndarray
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"TIFF file not found: {file_path}")

        image = Image.open(file_path)
        image_array = np.array(image)

        # Convert 16-bit to 8-bit for display
        if image_array.dtype == np.uint16:
            # Normalize to 8-bit
            image_array = (image_array / 256).astype(np.uint8)

        self.current_image = image_array
        self.current_file_path = file_path
        return image_array

    def load_image(self, file_path: str, fast_preview: bool = False) -> np.ndarray:
        """
        Load an image file (auto-detect format).

        Args:
            file_path: Path to image file
            fast_preview: Use fast preview mode for raw files

        Returns:
            Image array as numpy ndarray
        """
        file_path = Path(file_path)
        suffix = file_path.suffix.lower()

        if suffix in ['.dng', '.erf', '.nef', '.cr2', '.arw']:
            return self.load_raw_file(str(file_path), fast_preview)
        elif suffix in ['.tiff', '.tif']:
            return self.load_tiff_file(str(file_path))
        elif suffix in ['.jpg', '.jpeg', '.png']:
            # Standard image formats
            image = Image.open(file_path)
            image_array = np.array(image)
            self.current_image = image_array
            self.current_file_path = file_path
            return image_array
        else:
            raise ValueError(f"Unsupported file format: {suffix}")

    def get_file_metadata(self, file_path: str) -> Dict[str, Any]:
        """
        Extract metadata from image file using exiftool.

        Args:
            file_path: Path to image file

        Returns:
            Dictionary of metadata
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        try:
            with get_exiftool_helper() as et:
                metadata_list = et.get_metadata([str(file_path)])
                if metadata_list:
                    raw_metadata = metadata_list[0]
                else:
                    raw_metadata = {}
        except Exception as e:
            print(f"Warning: Could not extract metadata with exiftool: {e}")
            raw_metadata = {}

        # Extract commonly used fields
        metadata = {
            'camera': raw_metadata.get('EXIF:Model', 'Unknown'),
            'iso': raw_metadata.get('EXIF:ISO', None),
            'exposure_time': raw_metadata.get('EXIF:ExposureTime', None),
            'aperture': raw_metadata.get('EXIF:FNumber', None),
            'width': raw_metadata.get('EXIF:ImageWidth', None),
            'height': raw_metadata.get('EXIF:ImageHeight', None),
            'bit_depth': raw_metadata.get('EXIF:BitsPerSample', None),
            'file_size': file_path.stat().st_size,
            'file_name': file_path.name,
            'file_path': str(file_path),
            'raw_metadata': raw_metadata  # Keep full metadata for reference
        }

        self.current_metadata = metadata
        return metadata

    def get_simple_metadata(self, file_path: str) -> Dict[str, Any]:
        """
        Get basic metadata without exiftool (faster).

        Args:
            file_path: Path to image file

        Returns:
            Dictionary with basic metadata
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        suffix = file_path.suffix.lower()
        metadata = {
            'file_name': file_path.name,
            'file_path': str(file_path),
            'file_size': file_path.stat().st_size,
            'format': suffix
        }

        # Try to get dimensions from loaded image
        if self.current_image is not None and str(file_path) == str(self.current_file_path):
            metadata['width'] = self.current_image.shape[1]
            metadata['height'] = self.current_image.shape[0]
            metadata['channels'] = self.current_image.shape[2] if len(self.current_image.shape) > 2 else 1

        return metadata

    def normalize_image_for_display(self, image_array: np.ndarray) -> np.ndarray:
        """
        Normalize image array for display (convert to 8-bit if needed).

        Args:
            image_array: Input image array

        Returns:
            Normalized 8-bit image array
        """
        if image_array.dtype == np.uint16:
            # Convert 16-bit to 8-bit
            return (image_array / 256).astype(np.uint8)
        elif image_array.dtype == np.float32 or image_array.dtype == np.float64:
            # Assume float values are in [0, 1] range
            return (image_array * 255).astype(np.uint8)
        else:
            # Already 8-bit or compatible
            return image_array

    def get_image_stats(self, image_array: Optional[np.ndarray] = None) -> Dict[str, Any]:
        """
        Calculate statistics for an image.

        Args:
            image_array: Image array (uses current_image if None)

        Returns:
            Dictionary with image statistics
        """
        if image_array is None:
            image_array = self.current_image

        if image_array is None:
            return {}

        stats = {
            'shape': image_array.shape,
            'dtype': str(image_array.dtype),
            'min': float(np.min(image_array)),
            'max': float(np.max(image_array)),
            'mean': float(np.mean(image_array)),
            'std': float(np.std(image_array))
        }

        return stats
