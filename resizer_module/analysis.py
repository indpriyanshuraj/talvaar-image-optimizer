import logging
from PIL import Image
from .utils import is_ui_texture
from typing import Literal, Tuple

# Setup logger
logger = logging.getLogger(__name__)

class ImageAnalysis:
    def __init__(self, mode: str, alpha_type: Literal['none', 'binary', 'partial'], is_ui: bool, has_transparency: bool, suggested_algorithm: str = "NEAREST"):
        self.mode = mode
        self.alpha_type = alpha_type # 'none', 'binary', 'partial'
        self.is_ui = is_ui
        self.has_transparency = has_transparency
        self.suggested_algorithm = suggested_algorithm

def analyze_image(img: Image.Image, file_path: str) -> ImageAnalysis:
    """
    Analyzes pixel details to determine how to optimize.
    """
    logger.debug(f"Analyzing image: {file_path}")
    
    # Check UI context
    is_ui = is_ui_texture(file_path)

    # Analyze Alpha
    if img.mode != 'RGBA':
        temp_img = img.convert('RGBA')
    else:
        temp_img = img

    alpha = temp_img.getchannel('A')
    # Use explicit type for unpacking
    extrema: Tuple[int, int] = alpha.getextrema() # type: ignore
    min_a, max_a = extrema
    
    alpha_type: Literal['none', 'binary', 'partial'] = "none"
    has_transparency = False

    if min_a < 255:
        has_transparency = True
        vals = alpha.getcolors(257)
        if vals and len(vals) <= 2:
             if all(v[1] in (0, 255) for v in vals):
                 alpha_type = "binary"
             else:
                 alpha_type = "partial" 
        else:
             alpha_type = "partial"
    else:
        alpha_type = "none"
        has_transparency = False
    
    logger.debug(f"Alpha analysis result: type={alpha_type}, min_a={min_a}")

    if is_ui:
        suggested_algorithm = "NEAREST"
    elif alpha_type == "binary":
        suggested_algorithm = "NEAREST"
    else:
        colors = img.getcolors(257)
        if colors and len(colors) <= 256:
             suggested_algorithm = "NEAREST"
        else:
             suggested_algorithm = "LANCZOS"
             
    logger.debug(f"Suggested Algorithm: {suggested_algorithm}")

    return ImageAnalysis(
        mode=img.mode,
        alpha_type=alpha_type,
        is_ui=is_ui,
        has_transparency=has_transparency,
        suggested_algorithm=suggested_algorithm
    )