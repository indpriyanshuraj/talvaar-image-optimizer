import os
import shutil
import logging
from PIL import Image, UnidentifiedImageError
from typing import Tuple, Dict, Any, List
from .optimizer import smart_optimize, save_candidate_buffer
from .analysis import analyze_image
from .utils import get_unique_path

logger = logging.getLogger(__name__)

def process_single_image(args: Tuple[str, str, str, Dict[str, Any], Dict[str, Any]]) -> Tuple[bool, str, int, int]:
    file_path, input_root, output_root, res_config, save_config = args
    original_size = 0
    new_size = 0
    target_fmt = str(save_config.get('format', 'PNG'))
    ignore_transparency = bool(save_config.get('ignore_transparency', False))
    prefix = str(save_config.get('prefix', ''))
    suffix = str(save_config.get('suffix', ''))
    requested_algo = str(save_config.get('algorithm', 'auto'))
    
    logger.info(f"Processing: {file_path}")

    try:
        with Image.open(file_path) as img:
            original_size = os.path.getsize(file_path)
            
            # 1. Filename Construction
            filename = os.path.basename(file_path)
            base_name, _ = os.path.splitext(filename)
            new_base_name = f"{prefix}{base_name}{suffix}"
            new_filename = f"{new_base_name}.{target_fmt.lower()}"
            
            # Output Path Logic
            if os.path.isdir(input_root):
                rel_path = os.path.relpath(file_path, input_root)
                rel_dir = os.path.dirname(rel_path)
                final_out_path = os.path.join(output_root, rel_dir, new_filename)
            else:
                final_out_path = os.path.join(output_root, new_filename)

            os.makedirs(os.path.dirname(final_out_path), exist_ok=True)

            if os.path.exists(final_out_path):
                if save_config['conflict'] == 'keep_both':
                    final_out_path = get_unique_path(final_out_path)
                    logger.debug(f"Conflict resolved: {final_out_path}")

            # 2. Resize Logic
            target_w, target_h = 0, 0
            if res_config['mode'] == 'percentage':
                factor = float(res_config['val']) / 100.0
                target_w = max(1, int(img.width * factor))
                target_h = max(1, int(img.height * factor))
            else:
                target_w = max(1, int(res_config.get('width', 0)))
                if res_config.get('height', 0) == 0:
                    ratio = target_w / float(img.width)
                    target_h = max(1, int(img.height * ratio))
                else:
                    target_h = max(1, int(res_config.get('height', 0)))

            needs_resize = (target_w != img.width) or (target_h != img.height)
            
            # Use Resampling enum if available (Pillow 10+), else fallback
            try:
                # Type ignore because mypy might not see Resampling on older stubs
                algo_map = {
                    'nearest': Image.Resampling.NEAREST, # type: ignore
                    'lanczos': Image.Resampling.LANCZOS, # type: ignore
                    'bilinear': Image.Resampling.BILINEAR, # type: ignore
                    'bicubic': Image.Resampling.BICUBIC, # type: ignore
                    'box': Image.Resampling.BOX, # type: ignore
                    'hamming': Image.Resampling.HAMMING # type: ignore
                }
            except AttributeError:
                # Fallback for older Pillow
                algo_map = {
                    'nearest': Image.NEAREST, # type: ignore
                    'lanczos': Image.LANCZOS, # type: ignore
                    'bilinear': Image.BILINEAR, # type: ignore
                    'bicubic': Image.BICUBIC, # type: ignore
                    'box': Image.BOX, # type: ignore
                    'hamming': Image.HAMMING # type: ignore
                }

            if needs_resize:
                active_algo = algo_map['nearest']
                
                if requested_algo == 'auto':
                    analysis = analyze_image(img, file_path)
                    active_algo = algo_map.get(analysis.suggested_algorithm.lower(), algo_map['nearest'])
                    logger.debug(f"Auto-selected algorithm: {active_algo}")
                else:
                    active_algo = algo_map.get(requested_algo.lower(), algo_map['nearest'])

                resized_img = img.resize((target_w, target_h), active_algo)
            else:
                resized_img = img

            # 3. Optimization Strategy
            final_mode = "Unknown"
            
            if ignore_transparency and resized_img.mode == 'RGBA':
                resized_img = resized_img.convert('RGB')

            if save_config['mode'] == 'auto':
                is_same_dimensions = not needs_resize
                benchmark_size = float(original_size) if (is_same_dimensions and target_fmt.upper() == 'PNG') else float('inf')

                best_buffer, mode_name, best_size_f = smart_optimize(
                    resized_img, 
                    file_path, 
                    benchmark_size, 
                    int(save_config['compression']),
                    fmt=target_fmt,
                    ignore_transparency=ignore_transparency
                )
                best_size = int(best_size_f)

                if best_buffer and best_size < benchmark_size:
                    with open(final_out_path, 'wb') as f:
                        f.write(best_buffer.getvalue())
                    best_buffer.close()
                    final_mode = mode_name
                    new_size = best_size
                elif is_same_dimensions and target_fmt.upper() == 'PNG':
                    shutil.copy2(file_path, final_out_path)
                    final_mode = "Original (Skipped)"
                    new_size = original_size
                    logger.debug("Original file preserved (Optimization yielded larger file)")
                else:
                    if best_buffer:
                        with open(final_out_path, 'wb') as f:
                            f.write(best_buffer.getvalue())
                        best_buffer.close()
                        final_mode = mode_name
                        new_size = best_size
                    else:
                        final_mode = "Error"
                        logger.error("Failed to generate optimized buffer")

            else:
                # Manual Modes
                target_mode = 'RGBA'
                if save_config['mode'] == 'palette': target_mode = 'P'
                elif save_config['mode'] == 'rgb': target_mode = 'RGB'
                
                if ignore_transparency: target_mode = 'RGB'

                buffer, size_int = save_candidate_buffer(
                    resized_img, 
                    target_mode, 
                    256 if target_mode=='P' else None, 
                    int(save_config['compression']), 
                    fmt=target_fmt
                )
                
                if buffer and size_int is not None:
                    with open(final_out_path, 'wb') as f:
                        f.write(buffer.getvalue())
                    buffer.close()
                    final_mode = target_mode
                    new_size = size_int
                else:
                    final_mode = "Error"
                    logger.error("Failed to generate manual buffer")

            return True, final_mode, original_size, new_size

    except Exception as e:
        logger.error(f"Error processing {file_path}: {e}", exc_info=True)
        return False, f"Error processing {os.path.basename(file_path)}: {str(e)}", 0, 0
