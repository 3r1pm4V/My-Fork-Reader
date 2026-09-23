import os
import yaml
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional


@dataclass
class ReadingConfig:
    font_family: str = "Arial"
    font_size: int = 12
    line_height: float = 1.5
    theme: str = "light"  # light, dark, sepia


@dataclass
class LibraryConfig:
    path: str = str(Path.home() / "Documents" / "E-Reader")
    auto_scan: bool = True


@dataclass
class TTSConfig:
    enabled: bool = False
    rate: int = 150
    volume: float = 1.0


@dataclass
class SyncConfig:
    enabled: bool = False
    provider: str = "none"  # google_drive, dropbox


@dataclass
class WindowConfig:
    width: int = 1024
    height: int = 768
    maximized: bool = False


@dataclass
class LoggingConfig:
    level: str = "INFO"
    file_log: bool = True


@dataclass
class Config:
    reading: ReadingConfig = field(default_factory=ReadingConfig)
    library: LibraryConfig = field(default_factory=LibraryConfig)
    tts: TTSConfig = field(default_factory=TTSConfig)
    sync: SyncConfig = field(default_factory=SyncConfig)
    window: WindowConfig = field(default_factory=WindowConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)


def get_default_config_path() -> Path:
    """Returns the default config path based on OS standards (APPDATA on Windows)."""
    if os.name == 'nt':
        base_path = Path(os.environ.get('APPDATA', Path.home() / 'AppData' / 'Roaming'))
    else:
        base_path = Path.home() / ".config"
    
    return base_path / "ereader" / "config.yaml"


def load_config(path: Optional[Path] = None) -> Config:
    """
    Loads config from a YAML file. Creates a default one if it doesn't exist.
    
    Args:
        path: Optional Path to the config file.
        
    Returns:
        Config: The loaded or default configuration.
    """
    if path is None:
        path = get_default_config_path()

    if not path.exists():
        cfg = Config()
        save_config(cfg, path)
        return cfg

    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f) or {}
            
            # Simple manual mapping to handle dataclass nesting
            return Config(
                reading=ReadingConfig(**data.get('reading', {})),
                library=LibraryConfig(**data.get('library', {})),
                tts=TTSConfig(**data.get('tts', {})),
                sync=SyncConfig(**data.get('sync', {})),
                window=WindowConfig(**data.get('window', {})),
                logging=LoggingConfig(**data.get('logging', {}))
            )
    except Exception as e:
        print(f"Error loading config: {e}. Using defaults.")
        return Config()


def save_config(cfg: Config, path: Optional[Path] = None):
    """
    Saves the config object to a YAML file.
    
    Args:
        cfg: The Config object to save.
        path: Optional Path to the config file.
    """
    if path is None:
        path = get_default_config_path()

    path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(path, 'w', encoding='utf-8') as f:
        yaml.dump(asdict(cfg), f, default_flow_style=False, allow_unicode=True)


# TODO / EXTENSION POINTS:
# 1. Add schema validation using Cerberus or Pydantic.
# 2. Implement config migration logic for future version updates.
# 3. Add support for environment variable overrides.
# 4. Implement a dynamic 'watch' feature to reload config on file change.
