import pytest
from pathlib import Path
from ereader.config import load_config, save_config, Config

def test_config_default(tmp_path):
    # Test loading when file doesn't exist
    config_file = tmp_path / "config.yaml"
    cfg = load_config(config_file)
    
    assert cfg.reading.font_size == 12 # Default value
    assert config_file.exists()

def test_config_save_reload(tmp_path):
    config_file = tmp_path / "config.yaml"
    cfg = load_config(config_file)
    
    cfg.reading.font_size = 24
    cfg.reading.theme = "dark"
    save_config(cfg, config_file)
    
    new_cfg = load_config(config_file)
    assert new_cfg.reading.font_size == 24
    assert new_cfg.reading.theme == "dark"

def test_config_invalid_file(tmp_path):
    config_file = tmp_path / "broken.yaml"
    config_file.write_text("invalid: [unclosed bracket", encoding='utf-8')
    
    # Should fallback to defaults on parse error
    cfg = load_config(config_file)
    assert cfg.reading.font_size == 12
