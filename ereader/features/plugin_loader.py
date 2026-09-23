import importlib.util
import logging
import sys
from pathlib import Path

class PluginLoader:
    """
    Handles dynamic loading of Python plugins for the E-Reader.
    Each plugin should expose a 'register(app)' function.
    """

    @staticmethod
    def load_all(plugins_dir: Path, main_window):
        """
        Scans a directory for .py files and attempts to load them as plugins.
        """
        if not plugins_dir.exists():
            plugins_dir.mkdir(parents=True, exist_ok=True)
            return

        logging.info(f"Scanning for plugins in {plugins_dir}...")
        
        for file in plugins_dir.glob("*.py"):
            if file.name == "__init__.py":
                continue

            plugin_name = file.stem
            try:
                spec = importlib.util.spec_from_file_location(plugin_name, file)
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    sys.modules[plugin_name] = module
                    spec.loader.exec_module(module)

                    if hasattr(module, "register"):
                        module.register(main_window)
                        logging.info(f"Plugin '{plugin_name}' registered successfully.")
                    else:
                        logging.warning(f"Plugin '{plugin_name}' missing 'register' function.")
            except Exception as e:
                logging.error(f"Failed to load plugin '{plugin_name}': {e}")

__all__ = ["PluginLoader"]
