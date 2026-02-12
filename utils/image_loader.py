"""
Image loader utilities with caching and camera-specific processing.
Provides efficient loading of raw files with thumbnails and crops.
"""

import rawpy
import numpy as np
from PIL import Image
from pathlib import Path
from typing import Dict, Optional, Tuple
from functools import lru_cache
import hashlib

# Import camera crops from sensor_camera module
from sensor_camera import Sensor


class ImageCache:
    """LRU cache for loaded images with memory management"""

    def __init__(self, max_size: int = 10):
        """
        Initialize image cache.

        Args:
            max_size: Maximum number of images to cache
        """
        self.max_size = max_size
        self.cache: Dict[str, np.ndarray] = {}
        self.access_order: list = []

    def get(self, key: str) -> Optional[np.ndarray]:
        """Get image from cache"""
        if key in self.cache:
            # Move to end (most recently used)
            self.access_order.remove(key)
            self.access_order.append(key)
            return self.cache[key]
        return None

    def put(self, key: str, image: np.ndarray) -> None:
        """Add image to cache"""
        if key in self.cache:
            # Update existing
            self.access_order.remove(key)
        elif len(self.cache) >= self.max_size:
            # Remove least recently used
            lru_key = self.access_order.pop(0)
            del self.cache[lru_key]

        self.cache[key] = image
        self.access_order.append(key)

    def clear(self) -> None:
        """Clear all cached images"""
        self.cache.clear()
        self.access_order.clear()

    def get_size(self) -> int:
        """Get number of cached images"""
        return len(self.cache)


class ImageLoader:
    """Efficient image loader with caching and camera-specific processing"""

    def __init__(self, cache_size: int = 10):
        """
        Initialize image loader.

        Args:
            cache_size: Maximum number of images to cache
        """
        self.cache = ImageCache(max_size=cache_size)
        self.thumbnail_cache = ImageCache(max_size=cache_size * 2)

    def _get_cache_key(self, file_path: str, fast_preview: bool = False) -> str:
        """Generate cache key for file"""
        return f"{file_path}:{'thumb' if fast_preview else 'full'}"

    def load_raw_file(self, file_path: str, fast_preview: bool = False,
                     apply_crop: bool = True, camera_model: Optional[str] = None) -> np.ndarray:
        """
        Load a raw DNG or ERF file with caching.

        Args:
            file_path: Path to raw file
            fast_preview: If True, extract embedded JPEG thumbnail for speed
            apply_crop: Apply camera-specific crop
            camera_model: Camera model name (for crop lookup)

        Returns:
            Image array as numpy ndarray
        """
        # Check cache first
        cache_key = self._get_cache_key(file_path, fast_preview)
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached

        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"Raw file not found: {file_path}")

        with rawpy.imread(str(file_path)) as raw:
            if fast_preview:
                # Extract embedded JPEG thumbnail
                try:
                    thumb = raw.extract_thumb()
                    if thumb.format == rawpy.ThumbFormat.JPEG:
                        from io import BytesIO
                        image = Image.open(BytesIO(thumb.data))
                        image_array = np.array(image)
                    else:
                        # Fallback to bitmap thumbnail
                        image_array = thumb.data
                except Exception:
                    # Fallback to half-size postprocessing
                    image_array = raw.postprocess(
                        use_camera_wb=True,
                        half_size=True,
                        no_auto_bright=False,
                        output_bps=8
                    )
            else:
                # Load raw data for full quality
                raw_data = raw.raw_image.copy()

                # Apply camera-specific crop if requested
                if apply_crop and camera_model:
                    crop = Sensor.CAMERA_CROPS.get(camera_model)
                    if crop is not None:
                        raw_data = raw_data[crop]

                # Postprocess to RGB
                image_array = raw.postprocess(
                    use_camera_wb=True,
                    half_size=False,
                    no_auto_bright=False,
                    output_bps=8
                )

        # Cache the result
        self.cache.put(cache_key, image_array)

        return image_array

    def load_tiff_file(self, file_path: str, normalize_to_8bit: bool = True) -> np.ndarray:
        """
        Load a TIFF file with caching.

        Args:
            file_path: Path to TIFF file
            normalize_to_8bit: Convert 16-bit to 8-bit for display

        Returns:
            Image array as numpy ndarray
        """
        cache_key = self._get_cache_key(file_path)
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached

        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"TIFF file not found: {file_path}")

        image = Image.open(file_path)
        image_array = np.array(image)

        # Convert 16-bit to 8-bit for display
        if normalize_to_8bit and image_array.dtype == np.uint16:
            image_array = (image_array / 256).astype(np.uint8)

        self.cache.put(cache_key, image_array)
        return image_array

    def load_image(self, file_path: str, fast_preview: bool = False,
                  camera_model: Optional[str] = None) -> np.ndarray:
        """
        Load an image file (auto-detect format).

        Args:
            file_path: Path to image file
            fast_preview: Use fast preview mode for raw files
            camera_model: Camera model for crop lookup

        Returns:
            Image array as numpy ndarray
        """
        file_path = Path(file_path)
        suffix = file_path.suffix.lower()

        if suffix in ['.dng', '.erf', '.nef', '.cr2', '.arw']:
            return self.load_raw_file(str(file_path), fast_preview, camera_model=camera_model)
        elif suffix in ['.tiff', '.tif']:
            return self.load_tiff_file(str(file_path))
        elif suffix in ['.jpg', '.jpeg', '.png']:
            # Standard image formats
            cache_key = self._get_cache_key(str(file_path))
            cached = self.cache.get(cache_key)
            if cached is not None:
                return cached

            image = Image.open(file_path)
            image_array = np.array(image)
            self.cache.put(cache_key, image_array)
            return image_array
        else:
            raise ValueError(f"Unsupported file format: {suffix}")

    def generate_thumbnail(self, file_path: str, size: Tuple[int, int] = (200, 200)) -> np.ndarray:
        """
        Generate a thumbnail for an image file.

        Args:
            file_path: Path to image file
            size: Thumbnail size (width, height)

        Returns:
            Thumbnail as numpy array
        """
        # Check thumbnail cache
        thumb_key = f"{file_path}:thumb_{size[0]}x{size[1]}"
        cached = self.thumbnail_cache.get(thumb_key)
        if cached is not None:
            return cached

        # Load image with fast preview
        image_array = self.load_image(file_path, fast_preview=True)

        # Resize to thumbnail size
        image = Image.fromarray(image_array)
        image.thumbnail(size, Image.Resampling.LANCZOS)
        thumbnail = np.array(image)

        # Cache thumbnail
        self.thumbnail_cache.put(thumb_key, thumbnail)

        return thumbnail

    def clear_cache(self) -> None:
        """Clear all caches"""
        self.cache.clear()
        self.thumbnail_cache.clear()

    def get_cache_stats(self) -> Dict[str, int]:
        """Get cache statistics"""
        return {
            'image_cache_size': self.cache.get_size(),
            'thumbnail_cache_size': self.thumbnail_cache.get_size(),
            'image_cache_max': self.cache.max_size,
            'thumbnail_cache_max': self.thumbnail_cache.max_size
        }


def normalize_for_display(image_array: np.ndarray) -> np.ndarray:
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


def apply_auto_contrast(image_array: np.ndarray, percentile: float = 2.0) -> np.ndarray:
    """
    Apply auto-contrast adjustment to image.

    Args:
        image_array: Input image array
        percentile: Percentile for clipping (default: 2%)

    Returns:
        Contrast-adjusted image
    """
    # Calculate percentiles for clipping
    low = np.percentile(image_array, percentile)
    high = np.percentile(image_array, 100 - percentile)

    # Clip and rescale
    clipped = np.clip(image_array, low, high)
    normalized = ((clipped - low) / (high - low) * 255).astype(np.uint8)

    return normalized


# Global image loader instance
_global_loader: Optional[ImageLoader] = None


def get_image_loader(cache_size: int = 10) -> ImageLoader:
    """
    Get or create global image loader instance.

    Args:
        cache_size: Cache size for new loader

    Returns:
        ImageLoader instance
    """
    global _global_loader
    if _global_loader is None:
        _global_loader = ImageLoader(cache_size=cache_size)
    return _global_loader
