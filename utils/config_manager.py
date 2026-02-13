"""
Configuration manager for Camera Sensor Analyzer.
Manages working directory and source directory settings.
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional


class ConfigManager:
    """Manages application configuration stored in JSON"""

    DEFAULT_WORKING_DIR = Path.home() / '.camera-char'
    DEFAULT_SOURCE_DIR = '/Users/steve/Library/CloudStorage/SynologyDrive-SF/camera-char/noise_images'
    CONFIG_FILENAME = 'config.json'

    def __init__(self):
        """Initialize configuration manager"""
        self.working_dir: Path = self.DEFAULT_WORKING_DIR
        self.source_dir: Optional[Path] = None
        self.config_path: Path = self.working_dir / self.CONFIG_FILENAME

        # Ensure working directory exists
        self._ensure_working_dir()

        # Load configuration
        self.load_config()

    def _ensure_working_dir(self) -> None:
        """Ensure working directory exists"""
        self.working_dir.mkdir(parents=True, exist_ok=True)

    def load_config(self) -> None:
        """Load configuration from JSON file"""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r') as f:
                    config = json.load(f)

                # Load working directory
                if 'working_dir' in config:
                    self.working_dir = Path(config['working_dir'])
                    self._ensure_working_dir()
                    # Update config path to new working directory
                    self.config_path = self.working_dir / self.CONFIG_FILENAME

                # Load source directory
                if 'source_dir' in config:
                    self.source_dir = Path(config['source_dir'])
                else:
                    # Set default source directory
                    self.source_dir = Path(self.DEFAULT_SOURCE_DIR)

            except Exception as e:
                print(f"Warning: Failed to load config: {e}")
                self._set_defaults()
        else:
            # First run - create default config
            self._set_defaults()
            self.save_config()

    def _set_defaults(self) -> None:
        """Set default configuration values"""
        self.working_dir = self.DEFAULT_WORKING_DIR
        self.source_dir = Path(self.DEFAULT_SOURCE_DIR)
        self._ensure_working_dir()
        self.config_path = self.working_dir / self.CONFIG_FILENAME

    def save_config(self) -> None:
        """Save configuration to JSON file"""
        config = {
            'working_dir': str(self.working_dir),
            'source_dir': str(self.source_dir) if self.source_dir else None
        }

        try:
            with open(self.config_path, 'w') as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            print(f"Error: Failed to save config: {e}")

    def set_working_dir(self, path: str) -> None:
        """
        Set working directory.

        Args:
            path: New working directory path
        """
        new_path = Path(path)
        new_path.mkdir(parents=True, exist_ok=True)

        self.working_dir = new_path
        self.config_path = self.working_dir / self.CONFIG_FILENAME
        self.save_config()

    def set_source_dir(self, path: str) -> None:
        """
        Set source directory.

        Args:
            path: New source directory path
        """
        self.source_dir = Path(path)
        self.save_config()

    def get_working_dir(self) -> Path:
        """Get current working directory"""
        return self.working_dir

    def get_source_dir(self) -> Optional[Path]:
        """Get current source directory"""
        return self.source_dir

    def get_aggregate_csv_path(self) -> Path:
        """Get path to aggregate_analysis.csv in working directory"""
        return self.working_dir / 'aggregate_analysis.csv'

    def get_config_dict(self) -> Dict[str, Any]:
        """Get configuration as dictionary"""
        return {
            'working_dir': str(self.working_dir),
            'source_dir': str(self.source_dir) if self.source_dir else None,
            'config_path': str(self.config_path),
            'aggregate_csv': str(self.get_aggregate_csv_path())
        }


# Global configuration instance
_global_config: Optional[ConfigManager] = None


def get_config() -> ConfigManager:
    """
    Get or create global configuration instance.

    Returns:
        ConfigManager instance
    """
    global _global_config
    if _global_config is None:
        _global_config = ConfigManager()
    return _global_config
