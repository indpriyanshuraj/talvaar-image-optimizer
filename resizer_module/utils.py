import os

def get_unique_path(path: str) -> str:
    """Generates a unique filename: file.png -> file_1.png"""
    if not os.path.exists(path):
        return path
    base, ext = os.path.splitext(path)
    counter = 1
    new_path = f"{base}_{counter}{ext}"
    while os.path.exists(new_path):
        counter += 1
        new_path = f"{base}_{counter}{ext}"
    return new_path

def is_ui_texture(path: str) -> bool:
    """Detects if file belongs to UI folders to enforce safe encoding."""
    p = path.lower().replace("\\", "/")
    parts = p.split('/')
    # Check if any key folder name appears as a path segment
    keywords = {'ui', 'gui', 'colormap', 'font'}
    return any(k in keywords for k in parts)