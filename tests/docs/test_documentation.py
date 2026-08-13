import os
import yaml
import json

def test_mkdocs_valid():
    with open("docs/mkdocs.yml", "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    assert "site_name" in config
    assert config["theme"]["name"] == "material"

def test_referenced_pages_exist():
    with open("docs/mkdocs.yml", "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    
    def extract_paths(nav_items):
        paths = []
        for item in nav_items:
            if isinstance(item, dict):
                for key, val in item.items():
                    if isinstance(val, str):
                        paths.append(val)
                    elif isinstance(val, list):
                        paths.extend(extract_paths(val))
            elif isinstance(item, str):
                paths.append(item)
        return paths

    paths = extract_paths(config.get("nav", []))
    for path in paths:
        full_path = os.path.join("docs/site", path)
        assert os.path.exists(full_path), f"Missing referenced page: {path}"

def test_bg_en_parity():
    # Simple check for parity of filenames
    bg_files = set()
    for root, _, files in os.walk("docs/site/bg"):
        for file in files:
            bg_files.add(os.path.relpath(os.path.join(root, file), "docs/site/bg"))
    
    en_files = set()
    for root, _, files in os.walk("docs/site/en"):
        for file in files:
            en_files.add(os.path.relpath(os.path.join(root, file), "docs/site/en"))
            
    assert bg_files == en_files, f"Parity mismatch: BG: {bg_files}, EN: {en_files}"

def test_postman_collection_valid_json():
    with open("docs/postman_collection.json", "r", encoding="utf-8") as f:
        collection = json.load(f)
    assert "info" in collection
    assert "item" in collection
