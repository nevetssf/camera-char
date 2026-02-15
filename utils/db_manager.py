"""
Database manager for camera sensor analysis.
Uses SQLite to store image metadata, analysis results, and EXIF data.
"""

import sqlite3
import json
import hashlib
from pathlib import Path
from typing import Optional, Dict, List, Any, Tuple
from datetime import datetime
from contextlib import contextmanager

from utils.config_manager import get_config
from utils.app_logger import get_logger


class DatabaseManager:
    """Manages SQLite database for image analysis"""

    def __init__(self, db_path: Optional[Path] = None):
        """
        Initialize database manager.

        Args:
            db_path: Path to database file (uses config default if None)
        """
        self.logger = get_logger()

        if db_path is None:
            config = get_config()
            db_dir = config.get_working_dir() / "db"
            db_dir.mkdir(exist_ok=True)
            db_path = db_dir / "analysis.db"

        self.db_path = Path(db_path)
        self.logger.info(f"Database path: {self.db_path}")

        # Initialize database schema if needed
        self._initialize_database()

    @contextmanager
    def get_connection(self):
        """Context manager for database connection"""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row  # Enable column access by name
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            self.logger.error(f"Database error: {e}", exc_info=True)
            raise
        finally:
            conn.close()

    def _initialize_database(self) -> None:
        """Create database schema if it doesn't exist"""
        schema_sql = """
        -- Core image registry
        CREATE TABLE IF NOT EXISTS images (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_path TEXT UNIQUE NOT NULL,
            filename TEXT NOT NULL,
            file_type TEXT,
            file_hash TEXT UNIQUE,
            file_size INTEGER,
            file_modified TIMESTAMP,
            xdim INTEGER NOT NULL,
            ydim INTEGER NOT NULL,
            camera_id INTEGER,
            last_analyzed TIMESTAMP,
            archived BOOLEAN DEFAULT 0,

            FOREIGN KEY (camera_id) REFERENCES cameras(id)
        );

        -- Camera information
        CREATE TABLE IF NOT EXISTS cameras (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            make TEXT NOT NULL,
            model TEXT NOT NULL,
            serial_number TEXT,

            UNIQUE(make, model, serial_number)
        );

        -- Analysis results (noise analysis data)
        CREATE TABLE IF NOT EXISTS analysis_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            image_id INTEGER UNIQUE NOT NULL,
            ev REAL,
            noise_std REAL,
            noise_mean REAL,

            FOREIGN KEY (image_id) REFERENCES images(id) ON DELETE CASCADE
        );

        -- EXIF metadata
        CREATE TABLE IF NOT EXISTS exif_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            image_id INTEGER UNIQUE NOT NULL,
            exif_json TEXT NOT NULL,
            iso INTEGER,
            exposure_time REAL,
            exposure_setting INTEGER,
            black_level TEXT,
            white_level TEXT,
            bits_per_sample INTEGER,
            megapixels REAL,
            date_taken TIMESTAMP,
            orientation INTEGER,
            color_space TEXT,
            white_balance TEXT,

            FOREIGN KEY (image_id) REFERENCES images(id) ON DELETE CASCADE
        );

        -- Camera attributes (histogram settings and bit depth overrides)
        CREATE TABLE IF NOT EXISTS camera_attributes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            camera_id INTEGER UNIQUE NOT NULL,
            x_min INTEGER,
            x_max INTEGER,
            y_min INTEGER,
            y_max INTEGER,
            bits_per_pixel_actual INTEGER,

            FOREIGN KEY (camera_id) REFERENCES cameras(id) ON DELETE CASCADE
        );

        -- Indexes
        CREATE INDEX IF NOT EXISTS idx_images_file_hash ON images(file_hash);
        CREATE INDEX IF NOT EXISTS idx_images_file_type ON images(file_type);
        CREATE INDEX IF NOT EXISTS idx_images_camera ON images(camera_id);
        CREATE INDEX IF NOT EXISTS idx_images_analyzed ON images(last_analyzed);
        CREATE INDEX IF NOT EXISTS idx_images_archived ON images(archived);
        CREATE INDEX IF NOT EXISTS idx_images_dimensions ON images(xdim, ydim);
        CREATE INDEX IF NOT EXISTS idx_analysis_ev ON analysis_results(ev);
        CREATE INDEX IF NOT EXISTS idx_exif_date ON exif_data(date_taken);
        CREATE INDEX IF NOT EXISTS idx_exif_iso ON exif_data(iso);
        CREATE INDEX IF NOT EXISTS idx_exif_exposure ON exif_data(exposure_time);
        CREATE INDEX IF NOT EXISTS idx_exif_megapixels ON exif_data(megapixels);
        CREATE INDEX IF NOT EXISTS idx_exif_bits ON exif_data(bits_per_sample);
        """

        try:
            with self.get_connection() as conn:
                conn.executescript(schema_sql)
            self.logger.info("Database schema initialized")
        except Exception as e:
            self.logger.error(f"Failed to initialize database: {e}", exc_info=True)
            raise

    def calculate_file_hash(self, file_path: Path) -> str:
        """
        Calculate SHA256 hash of file.

        Args:
            file_path: Path to file

        Returns:
            Hex digest of file hash
        """
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            # Read in chunks to handle large files
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    def get_or_create_camera(self, make: str, model: str,
                            serial_number: Optional[str] = None) -> int:
        """
        Get or create camera record.

        Args:
            make: Camera manufacturer
            model: Camera model
            serial_number: Camera serial number

        Returns:
            Camera ID
        """
        with self.get_connection() as conn:
            # Try to find existing camera
            cursor = conn.execute(
                """SELECT id FROM cameras
                   WHERE make = ? AND model = ? AND
                   (serial_number = ? OR (serial_number IS NULL AND ? IS NULL))""",
                (make, model, serial_number, serial_number)
            )
            row = cursor.fetchone()

            if row:
                return row['id']

            # Create new camera
            cursor = conn.execute(
                "INSERT INTO cameras (make, model, serial_number) VALUES (?, ?, ?)",
                (make, model, serial_number)
            )
            camera_id = cursor.lastrowid
            self.logger.info(f"Created camera: {make} {model} (ID: {camera_id})")
            return camera_id

    def insert_image(self, file_path: Path, xdim: int, ydim: int,
                    camera_make: str, camera_model: str,
                    file_type: Optional[str] = None,
                    camera_serial: Optional[str] = None) -> int:
        """
        Insert image record.

        Args:
            file_path: Path to image file
            xdim: Image width
            ydim: Image height
            camera_make: Camera manufacturer
            camera_model: Camera model
            file_type: File format (DNG, ERF, etc.)
            camera_serial: Camera serial number

        Returns:
            Image ID
        """
        # Calculate derived values
        file_stat = file_path.stat()
        file_hash = self.calculate_file_hash(file_path)

        # Get or create camera
        camera_id = self.get_or_create_camera(camera_make, camera_model, camera_serial)

        with self.get_connection() as conn:
            cursor = conn.execute(
                """INSERT INTO images
                   (file_path, filename, file_type, file_hash, file_size, file_modified,
                    xdim, ydim, camera_id, last_analyzed)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    str(file_path),
                    file_path.name,
                    file_type or file_path.suffix.upper().lstrip('.'),
                    file_hash,
                    file_stat.st_size,
                    datetime.fromtimestamp(file_stat.st_mtime),
                    xdim,
                    ydim,
                    camera_id,
                    datetime.now()
                )
            )
            image_id = cursor.lastrowid
            self.logger.info(f"Inserted image: {file_path.name} (ID: {image_id})")
            return image_id

    def insert_analysis_results(self, image_id: int, ev: Optional[float] = None,
                                noise_std: Optional[float] = None,
                                noise_mean: Optional[float] = None) -> int:
        """
        Insert noise analysis results.

        Args:
            image_id: Image ID
            ev: Calculated EV
            noise_std: Noise standard deviation
            noise_mean: Noise mean

        Returns:
            Analysis result ID
        """
        with self.get_connection() as conn:
            cursor = conn.execute(
                """INSERT INTO analysis_results
                   (image_id, ev, noise_std, noise_mean)
                   VALUES (?, ?, ?, ?)""",
                (image_id, ev, noise_std, noise_mean)
            )
            result_id = cursor.lastrowid
            self.logger.debug(f"Inserted analysis results for image {image_id}")
            return result_id

    def insert_exif_data(self, image_id: int, exif_dict: Dict[str, Any],
                        iso: Optional[int] = None,
                        exposure_time: Optional[float] = None,
                        black_level: Optional[Any] = None,
                        white_level: Optional[Any] = None,
                        bits_per_sample: Optional[int] = None,
                        megapixels: Optional[float] = None) -> int:
        """
        Insert EXIF data.

        Args:
            image_id: Image ID
            exif_dict: Dictionary of EXIF data
            iso: ISO value (if not provided, extracted from exif_dict)
            exposure_time: Exposure time (if not provided, extracted from exif_dict)
            black_level: Black level (if not provided, extracted from exif_dict)
            white_level: White level (if not provided, extracted from exif_dict)
            bits_per_sample: Bit depth (if not provided, extracted from exif_dict)
            megapixels: Megapixels (if not provided, calculated from image dimensions)

        Returns:
            EXIF data ID
        """
        # Extract commonly queried fields
        date_taken = exif_dict.get('EXIF:DateTimeOriginal')
        orientation = exif_dict.get('EXIF:Orientation')
        color_space = exif_dict.get('EXIF:ColorSpace')
        white_balance = exif_dict.get('EXIF:WhiteBalance')

        # Extract exposure settings if not provided
        if iso is None:
            iso = exif_dict.get('EXIF:ISO')
        if exposure_time is None:
            exposure_time = exif_dict.get('EXIF:ExposureTime')

        # Calculate exposure setting (1/exposure_time, rounded)
        exposure_setting = None
        if exposure_time and exposure_time > 0:
            exposure_setting = round(1.0 / exposure_time)

        # Extract black and white levels if not provided
        if black_level is None:
            black_level = exif_dict.get('SubIFD:BlackLevel')
        if white_level is None:
            white_level = exif_dict.get('SubIFD:WhiteLevel')

        # Extract bits per sample if not provided
        if bits_per_sample is None:
            bits = exif_dict.get('EXIF:BitsPerSample')
            if isinstance(bits, (list, tuple)):
                bits_per_sample = bits[0]
            else:
                bits_per_sample = bits

        # Calculate megapixels from image dimensions if not provided
        if megapixels is None:
            with self.get_connection() as conn:
                cursor = conn.execute(
                    "SELECT xdim, ydim FROM images WHERE id = ?",
                    (image_id,)
                )
                row = cursor.fetchone()
                if row:
                    xdim, ydim = row['xdim'], row['ydim']
                    megapixels = (xdim * ydim) / 1_000_000.0

        # Convert arrays to JSON
        black_level_json = json.dumps(black_level) if isinstance(black_level, (list, tuple)) else black_level
        white_level_json = json.dumps(white_level) if isinstance(white_level, (list, tuple)) else white_level

        with self.get_connection() as conn:
            cursor = conn.execute(
                """INSERT INTO exif_data
                   (image_id, exif_json, iso, exposure_time, exposure_setting,
                    black_level, white_level, bits_per_sample, megapixels,
                    date_taken, orientation, color_space, white_balance)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (image_id, json.dumps(exif_dict), iso, exposure_time, exposure_setting,
                 black_level_json, white_level_json, bits_per_sample, megapixels,
                 date_taken, orientation, color_space, white_balance)
            )
            exif_id = cursor.lastrowid
            self.logger.debug(f"Inserted EXIF data for image {image_id}")
            return exif_id

    def get_image_by_path(self, file_path: Path) -> Optional[Dict]:
        """Get image record by file path"""
        with self.get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM images WHERE file_path = ?",
                (str(file_path),)
            )
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_image_by_hash(self, file_hash: str) -> Optional[Dict]:
        """Get image record by file hash"""
        with self.get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM images WHERE file_hash = ?",
                (file_hash,)
            )
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_all_analysis_data(self, include_archived: bool = False) -> List[Dict]:
        """
        Get all analysis data (similar to CSV format).

        Args:
            include_archived: Include archived images

        Returns:
            List of dictionaries with analysis data
        """
        archived_filter = "" if include_archived else "AND i.archived = 0"

        with self.get_connection() as conn:
            cursor = conn.execute(f"""
                SELECT
                    c.model as camera,
                    e.iso,
                    e.exposure_time,
                    e.exposure_setting,
                    a.ev,
                    a.noise_std,
                    a.noise_mean,
                    i.file_path as source,
                    i.filename,
                    i.xdim,
                    i.ydim,
                    e.megapixels,
                    e.bits_per_sample,
                    e.black_level,
                    e.white_level
                FROM images i
                LEFT JOIN exif_data e ON e.image_id = i.id
                LEFT JOIN analysis_results a ON a.image_id = i.id
                JOIN cameras c ON i.camera_id = c.id
                WHERE 1=1 {archived_filter}
                ORDER BY c.model, e.iso, e.exposure_time
            """)
            return [dict(row) for row in cursor.fetchall()]

    def get_unique_exposure_settings(self) -> List[int]:
        """
        Get list of unique exposure settings from database.

        Returns:
            Sorted list of unique exposure settings
        """
        with self.get_connection() as conn:
            cursor = conn.execute("""
                SELECT DISTINCT exposure_setting
                FROM exif_data
                WHERE exposure_setting IS NOT NULL
                ORDER BY exposure_setting
            """)
            return [row[0] for row in cursor.fetchall()]

    def mark_archived(self, image_id: int, archived: bool = True) -> None:
        """Mark image as archived"""
        with self.get_connection() as conn:
            conn.execute(
                "UPDATE images SET archived = ? WHERE id = ?",
                (1 if archived else 0, image_id)
            )
            self.logger.info(f"Marked image {image_id} as archived={archived}")

    def get_stats(self) -> Dict[str, int]:
        """Get database statistics"""
        with self.get_connection() as conn:
            stats = {}

            cursor = conn.execute("SELECT COUNT(*) as count FROM images")
            stats['total_images'] = cursor.fetchone()['count']

            cursor = conn.execute("SELECT COUNT(*) as count FROM images WHERE archived = 1")
            stats['archived_images'] = cursor.fetchone()['count']

            cursor = conn.execute("SELECT COUNT(*) as count FROM cameras")
            stats['cameras'] = cursor.fetchone()['count']

            cursor = conn.execute("SELECT COUNT(*) as count FROM analysis_results")
            stats['analyzed_images'] = cursor.fetchone()['count']

            return stats

    def get_camera_attributes(self, camera_id: int) -> Optional[Dict]:
        """
        Get camera attributes (histogram settings and bit depth).

        Args:
            camera_id: Camera ID

        Returns:
            Dictionary with x_min, x_max, y_min, y_max, bits_per_pixel_actual
            or None if no attributes saved
        """
        with self.get_connection() as conn:
            cursor = conn.execute(
                """SELECT x_min, x_max, y_min, y_max, bits_per_pixel_actual
                   FROM camera_attributes WHERE camera_id = ?""",
                (camera_id,)
            )
            row = cursor.fetchone()
            return dict(row) if row else None

    def update_camera_attributes(self, camera_id: int,
                                 x_min: Optional[int] = None,
                                 x_max: Optional[int] = None,
                                 y_min: Optional[int] = None,
                                 y_max: Optional[int] = None,
                                 bits_per_pixel_actual: Optional[int] = None) -> None:
        """
        Update camera attributes. Creates record if doesn't exist.

        Args:
            camera_id: Camera ID
            x_min: Histogram X minimum
            x_max: Histogram X maximum
            y_min: Histogram Y minimum
            y_max: Histogram Y maximum
            bits_per_pixel_actual: Actual bits per pixel (override)
        """
        with self.get_connection() as conn:
            # Check if record exists
            cursor = conn.execute(
                "SELECT id FROM camera_attributes WHERE camera_id = ?",
                (camera_id,)
            )
            exists = cursor.fetchone() is not None

            if exists:
                # Update existing record
                conn.execute(
                    """UPDATE camera_attributes
                       SET x_min = ?, x_max = ?, y_min = ?, y_max = ?, bits_per_pixel_actual = ?
                       WHERE camera_id = ?""",
                    (x_min, x_max, y_min, y_max, bits_per_pixel_actual, camera_id)
                )
                self.logger.info(f"Updated attributes for camera {camera_id}")
            else:
                # Insert new record
                conn.execute(
                    """INSERT INTO camera_attributes
                       (camera_id, x_min, x_max, y_min, y_max, bits_per_pixel_actual)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (camera_id, x_min, x_max, y_min, y_max, bits_per_pixel_actual)
                )
                self.logger.info(f"Created attributes for camera {camera_id}")

    def get_camera_id_by_file_hash(self, file_hash: str) -> Optional[int]:
        """
        Get camera ID from image file hash.

        Args:
            file_hash: SHA256 hash of image file

        Returns:
            Camera ID or None if not found
        """
        with self.get_connection() as conn:
            cursor = conn.execute(
                "SELECT camera_id FROM images WHERE file_hash = ?",
                (file_hash,)
            )
            row = cursor.fetchone()
            return row['camera_id'] if row else None


def get_db_manager() -> DatabaseManager:
    """Get singleton database manager instance"""
    if not hasattr(get_db_manager, '_instance'):
        get_db_manager._instance = DatabaseManager()
    return get_db_manager._instance
