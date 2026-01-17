import io
import logging
from PIL import Image
from typing import List, Tuple, Optional, Any, Union
from .analysis import analyze_image, ImageAnalysis

logger = logging.getLogger(__name__)

def generate_candidates(analysis: ImageAnalysis, ignore_transparency: bool = False) -> List[Tuple[str, Optional[int]]]:
    """
    Decides which formats/modes to test based on analysis.
    """
    candidates: List[Tuple[str, Optional[int]]] = []
    effective_alpha = "none" if ignore_transparency else analysis.alpha_type

    if effective_alpha == "none":
        # Opaque: Test RGB and Palette
        candidates.append(("RGB", None)) 
        if not analysis.is_ui:
             candidates.append(("P", 256)) 
             candidates.append(("P", 128)) 
    
    elif effective_alpha == "binary":
        # Cutout: RGBA is safe. Palette (P) can handle binary alpha.
        candidates.append(("RGBA", None))
        if not analysis.is_ui:
            candidates.append(("P", 256))
            candidates.append(("P", 128))

    elif effective_alpha == "partial":
        # Glass: RGBA only
        candidates.append(("RGBA", None))
        
    logger.debug(f"Generated candidates for alpha={effective_alpha}, ui={analysis.is_ui}: {candidates}")
    return candidates

def save_candidate_buffer(img: Image.Image, mode: str, colors: Optional[int], compression: int, fmt: str = "PNG") -> Tuple[Optional[io.BytesIO], Optional[int]]:
    """
    Helper to save a variant to a memory buffer.
    """
    try:
        buffer = io.BytesIO()
        save_kwargs = {}
        
        # Setup Save Args
        if fmt.upper() == "PNG":
            save_kwargs = {"format": "PNG", "optimize": True, "compress_level": compression}
        elif fmt.upper() in ["JPG", "JPEG"]:
             save_kwargs = {"format": "JPEG", "quality": 85 if compression == 0 else max(10, 100 - (compression*10)), "optimize": True}
        elif fmt.upper() == "WEBP":
             save_kwargs = {"format": "WEBP", "quality": 85 if compression == 0 else max(10, 100 - (compression*10))}
        else:
             save_kwargs = {"format": fmt}

        # Setup Image Mode
        out: Image.Image
        if mode == "RGB":
            out = img.convert("RGB")
        elif mode == "RGBA":
            out = img.convert("RGBA")
        elif mode == "P":
            if img.mode != 'RGBA': img = img.convert('RGBA')
            # Ensure colors is int
            c = colors if colors is not None else 256
            out = img.quantize(colors=c, method=2, dither=Image.Dither.NONE)
        else:
            return None, None

        # Handle JPEG alpha drop
        if fmt.upper() in ["JPG", "JPEG"] and out.mode == 'RGBA':
            out = out.convert("RGB")

        # Mypy workaround for save **kwargs
        out.save(buffer, **save_kwargs) # type: ignore
        size = buffer.tell()
        buffer.seek(0)
        return buffer, size
    except Exception as e:
        logger.warning(f"Failed to save candidate {mode}-{colors}: {e}")
        return None, None

def smart_optimize(img: Image.Image, file_path: str, original_size: float, compression: int = 9, fmt: str = "PNG", ignore_transparency: bool = False) -> Tuple[Optional[io.BytesIO], str, float]:
    """
    The main Auto-Optimizer entry point.
    """
    logger.debug(f"Starting Smart Opt for {file_path}. Benchmark: {original_size}")
    
    # 1. Analyze
    analysis = analyze_image(img, file_path)
    
    # 2. Select Candidates
    candidates = generate_candidates(analysis, ignore_transparency)
    
    best_buffer: Optional[io.BytesIO] = None
    best_size: float = original_size
    best_mode = "Original"
    
    # 3. Race
    for mode, colors in candidates:
        buffer, size = save_candidate_buffer(img, mode, colors, compression, fmt)
        
        if buffer and size is not None:
            if size < best_size:
                if best_buffer: best_buffer.close()
                best_size = size
                best_buffer = buffer
                best_mode = f"{mode}-{colors}" if colors else mode
                logger.debug(f"New Champion: {best_mode} ({size} bytes)")
            else:
                buffer.close()
                
    if best_buffer is None:
        safe_mode = "RGB" if (ignore_transparency or analysis.alpha_type == "none") else "RGBA"
        best_buffer, best_size_int = save_candidate_buffer(img, safe_mode, None, compression, fmt)
        best_size = float(best_size_int) if best_size_int is not None else float('inf')
        best_mode = f"{safe_mode} (Fallback)"
        logger.debug(f"No improvement found. Using Fallback: {best_mode}")

    return best_buffer, best_mode, best_size
