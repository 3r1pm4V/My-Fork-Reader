import os
import yaml
import logging
from pathlib import Path
from dataclasses import dataclass, field, asdict

def get_app_dir() -> Path:
    """Returns the platform-specific application data directory."""
    if os.name == 'nt':
        # On Windows: %APPDATA%/ereader
        app_dir = Path(os.getenv('APPDATA', os.path.expanduser('~'))) / "ereader"
    else:
        app_dir = Path.home() / ".config" / "ereader"
    
    app_dir.mkdir(parents=True, exist_ok=True)
    return app_dir

@dataclass
class ReadingConfig:
    font_size: int = 18
    line_height: float = 1.6
    theme: str = "light"
    font_family: str = "Literata"

@dataclass
class LibraryConfig:
    path: str = str(get_app_dir() / "library")
    folders: list[str] = field(default_factory=list)
    view_mode: str = "grid"
    sort_by: str = "added_at"
    auto_scan: bool = True

@dataclass
class CacheConfig:
    enabled: bool = True
    max_size_mb: int = 500
    clear_on_startup: bool = False

@dataclass
class TTSConfig:
    rate: int = 200
    volume: float = 1.0
    voice_id: str | None = None

@dataclass
class SyncConfig:
    enabled: bool = False
    url: str = "https://sync.koreader.rocks"
    username: str = ""
    password: str = ""
    device_id: str = "default_device"

@dataclass
class UIConfig:
    skeleton_enabled: bool = True
    skeleton_animation: bool = True
    fade_duration_ms: int = 300

@dataclass
class LoggingConfig:
    level: str = "INFO"
    file_log: bool = True

@dataclass
class WindowConfig:
    width: int = 1200
    height: int = 800
    maximized: bool = False

@dataclass
class Config:
    reading: ReadingConfig = field(default_factory=ReadingConfig)
    library: LibraryConfig = field(default_factory=LibraryConfig)
    window: WindowConfig = field(default_factory=WindowConfig)
    cache: CacheConfig = field(default_factory=CacheConfig)
    tts: TTSConfig = field(default_factory=TTSConfig)
    sync: SyncConfig = field(default_factory=SyncConfig)
    ui: UIConfig = field(default_factory=UIConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)

    def save(self):
        """Instance method for convenience, calls global save_config."""
        save_config(self)

    @classmethod
    def load(cls) -> 'Config':
        """Class method for convenience, calls global load_config."""
        return load_config()

def load_config(path: Path | str | None = None) -> Config:
    """Loads configuration from a YAML file."""
    if path is None:
        path = get_app_dir() / "config.yaml"
    else:
        path = Path(path)
        
    if not path.exists():
        return Config()
        
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
            
            def from_dict(cls, d):
                if not d: return cls()
                return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})

            return Config(
                reading=from_dict(ReadingConfig, data.get('reading')),
                library=from_dict(LibraryConfig, data.get('library')),
                window=from_dict(WindowConfig, data.get('window')),
                cache=from_dict(CacheConfig, data.get('cache')),
                tts=from_dict(TTSConfig, data.get('tts')),
                sync=from_dict(SyncConfig, data.get('sync')),
                ui=from_dict(UIConfig, data.get('ui')),
                logging=from_dict(LoggingConfig, data.get('logging'))
            )
    except Exception as e:
        logging.error(f"Failed to load config from {path}: {e}")
        return Config()

def save_config(config: Config, path: Path | str | None = None):
    """Saves configuration to a YAML file."""
    if path is None:
        path = get_app_dir() / "config.yaml"
    else:
        path = Path(path)
        
    try:
        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(asdict(config), f, default_flow_style=False)
    except Exception as e:
        logging.error(f"Failed to save config to {path}: {e}")

CONFIG_PATH = get_app_dir() / "config.yaml"

__all__ = [
    "Config", "load_config", "save_config", "get_app_dir", "CONFIG_PATH",
    "ReadingConfig", "LibraryConfig", "WindowConfig", "CacheConfig", 
    "TTSConfig", "SyncConfig", "UIConfig", "LoggingConfig"
]
