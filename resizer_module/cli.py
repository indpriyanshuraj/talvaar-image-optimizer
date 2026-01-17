import os
import sys
import glob
import argparse
import logging
from concurrent.futures import ProcessPoolExecutor, as_completed
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeRemainingColumn
from rich.prompt import Prompt, Confirm, IntPrompt, FloatPrompt
from PIL import Image
from typing import List, Dict, Any, Optional
from .worker import process_single_image
from .analysis import analyze_image

# Initialize Console
console = Console()

def setup_logging(verbose: bool = False):
    """Configures the logging system."""
    level = logging.DEBUG if verbose else logging.INFO
    format_str = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    # Configure root logger to write to file
    logging.basicConfig(
        filename='resizer.log',
        level=level,
        format=format_str,
        filemode='w' # Overwrite log each run
    )
    
def run_pre_analysis(files: List[str], max_workers: int = 4) -> bool:
    """
    Scans files to generate a summary report.
    """
    total = len(files)
    stats: Dict[str, Any] = {
        "formats": {},
        "alpha_types": {"none": 0, "binary": 0, "partial": 0},
        "ui_textures": 0,
        "total_size": 0
    }

    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[bold yellow]Running Pre-Analysis...[/bold yellow]"),
            BarColumn(),
            TextColumn("{task.percentage:>3.0f}%"),
        ) as progress:
            task = progress.add_task("Scanning...", total=total)
            
            with ProcessPoolExecutor(max_workers=max_workers) as executor:
                futures = {executor.submit(analyze_single_file, f): f for f in files}
                
                for future in as_completed(futures):
                    res = future.result()
                    if res:
                        stats["total_size"] += res['size']
                        
                        fmt = res['format']
                        stats["formats"][fmt] = stats["formats"].get(fmt, 0) + 1
                        
                        stats["alpha_types"][res['alpha_type']] += 1
                        if res['is_ui']:
                            stats["ui_textures"] += 1
                    
                    progress.advance(task)

        print_analysis_table(stats, total)
        return True

    except KeyboardInterrupt:
        console.print("[red]Analysis aborted.[/red]")
        return False

def analyze_single_file(path: str) -> Optional[Dict[str, Any]]:
    try:
        size = os.path.getsize(path)
        with Image.open(path) as img:
            from .analysis import analyze_image
            analysis = analyze_image(img, path)
            return {
                "size": size,
                "format": img.format,
                "alpha_type": analysis.alpha_type,
                "is_ui": analysis.is_ui
            }
    except Exception:
        return None

def print_analysis_table(stats: Dict[str, Any], count: int):
    table = Table(title=f"Pre-Analysis Report ({count} files)")
    
    table.add_column("Category", style="cyan")
    table.add_column("Count", style="green")
    table.add_column("Notes", style="dim")

    fmt_str = ", ".join([f"{k}: {v}" for k, v in stats['formats'].items()])
    table.add_row("Formats", fmt_str, "Input formats detected")
    
    table.add_row("Opaque", str(stats['alpha_types']['none']), "Safe to convert to RGB")
    table.add_row("Binary Alpha", str(stats['alpha_types']['binary']), "Cutout textures (Leaves, items)")
    table.add_row("Partial Alpha", str(stats['alpha_types']['partial']), "Glass, Ice, Translucent (Requires RGBA)")
    
    table.add_row("UI Textures", str(stats['ui_textures']), "Detected /ui/ path")
    
    mb_size = stats['total_size'] / (1024 * 1024)
    table.add_row("Total Size", f"{mb_size:.2f} MB", "")

    console.print(table)
    console.print("\n")

def run_processing(files_to_process: List[str], input_root: str, output_path: str, res_config: Dict[str, Any], save_config: Dict[str, Any], max_workers: int):
    if save_config.get('show_report', False):
        run_pre_analysis(files_to_process, max_workers)
    
    task_args = [(f, input_root, output_path, res_config, save_config) for f in files_to_process]
    
    total_orig = 0
    total_new = 0
    success = 0
    
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("{task.percentage:>3.0f}%"),
            TimeRemainingColumn()
        ) as progress:
            task = progress.add_task(f"[cyan]Optimizing {len(files_to_process)} images ({max_workers} threads)...", total=len(files_to_process))
            
            with ProcessPoolExecutor(max_workers=max_workers) as executor:
                futures = [executor.submit(process_single_image, arg) for arg in task_args]
                
                try:
                    for future in as_completed(futures):
                        is_ok, msg, orig, new = future.result()
                        if is_ok:
                            success += 1
                            total_orig += orig
                            total_new += new
                        else:
                            progress.console.print(f"[red]Error:[/red] {msg}")
                        progress.advance(task)
                except KeyboardInterrupt:
                    executor.shutdown(wait=False, cancel_futures=True)
                    console.print("\n[bold red]Aborted by user! Stopping workers...[/bold red]")
                    raise
    except KeyboardInterrupt:
        sys.exit(1)

    saved = total_orig - total_new
    saved_mb = saved / (1024 * 1024)
    ratio = (saved / total_orig * 100) if total_orig > 0 else 0

    table = Table(title="Optimization Results")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")
    
    table.add_row("Processed", f"{success}/{len(files_to_process)}")
    table.add_row("Total Before", f"{total_orig / (1024*1024):.2f} MB")
    table.add_row("Total After", f"{total_new / (1024*1024):.2f} MB")
    table.add_row("Total Saved", f"{saved_mb:.2f} MB ({ratio:.1f}%)")

    console.print("\n")
    console.print(table)
    console.print(f"[dim]Output: {os.path.abspath(output_path)}[/dim]")

def interactive_mode():
    console.print(Panel.fit("[bold magenta]🔬 Talvaar Optimizer V5.3 (Logging & Typed)[/bold magenta]", border_style="cyan"))
    
    SHORTCUTS = {
        "save_mode": {"1": "auto", "2": "rgba", "3": "palette", "4": "rgb"},
        "conflict": {"1": "overwrite", "2": "keep_both"},
        "format": {"1": "PNG", "2": "JPEG", "3": "WEBP"}
    }

    # Setup Logging immediately for interactive
    setup_logging(verbose=False)

    default_input = "input" if os.path.exists("input") else "."
    input_path = Prompt.ask("[bold cyan]Input file or folder[/bold cyan]", default=default_input)
    
    files_to_process = []
    if os.path.isdir(input_path):
        types = ('**/*.png', '**/*.jpg', '**/*.jpeg', '**/*.tga', '**/*.webp')
        for t in types:
            files_to_process.extend(glob.glob(os.path.join(input_path, t), recursive=True))
        console.print(f"[green]Found {len(files_to_process)} images.[/green]")
    elif os.path.isfile(input_path):
        files_to_process.append(input_path)
    else:
        console.print("[red]Invalid path[/red]")
        return

    if not files_to_process:
        return

    show_report = Confirm.ask("[bold yellow]Run Pre-Analysis Report?[/bold yellow]", default=True)
    if show_report:
        run_pre_analysis(files_to_process)
        if not Confirm.ask("Proceed with configuration?"):
            return

    default_out = "output"
    output_path = Prompt.ask("[bold cyan]Output directory[/bold cyan]", default=default_out)

    res_choice = Prompt.ask(
        "[bold cyan]Resize Mode[/bold cyan] [dim][1: Pixel, 2: Percentage][/dim]", 
        choices=["1", "2"], default="1"
    )
    res_mode = "pixel" if res_choice == "1" else "percentage"
    
    res_config = {'mode': res_mode}
    if res_mode == 'percentage':
        res_config['val'] = FloatPrompt.ask("Percentage", default=100.0)
    else:
        res_config['width'] = IntPrompt.ask("Width")
        res_config['height'] = IntPrompt.ask("Height (0 for auto)", default=0)

    needs_resize = False
    if res_mode == 'percentage' and res_config['val'] != 100.0: needs_resize = True
    
    algo_choice = "auto"
    if res_mode == 'pixel' or needs_resize:
        console.print("[dim]Resizing Algorithm (Default: Auto - selects Nearest for pixel art, Lanczos for photos)[/dim]")
        algo_options = ["auto", "nearest", "lanczos", "bilinear", "bicubic"]
        algo_choice = Prompt.ask("Algorithm", choices=algo_options, default="auto")

    prefix = Prompt.ask("[dim]Filename Prefix (optional)[/dim]", default="")
    suffix = Prompt.ask("[dim]Filename Suffix (optional)[/dim]", default="")

    ignore_transparency = Confirm.ask(
        "[bold yellow]Ignore Transparency?[/bold yellow] [dim](Convert all to Opaque RGB)[/dim]",
        default=False
    )

    fmt_choice = Prompt.ask(
        "[bold cyan]Output Format[/bold cyan] [dim][1: PNG, 2: JPEG, 3: WEBP][/dim]",
        choices=["1", "2", "3"], default="1"
    )
    target_fmt = SHORTCUTS['format'][fmt_choice]

    save_config = {
        'format': target_fmt,
        'ignore_transparency': ignore_transparency,
        'prefix': prefix,
        'suffix': suffix,
        'algorithm': algo_choice,
        'show_report': False
    }

    if target_fmt == "PNG":
         mode_choice = Prompt.ask(
            "Save Mode [dim][1: Auto (Smart Analysis), 2: RGBA, 3: Palette, 4: RGB][/dim]",
            choices=["1", "2", "3", "4"], default="1"
        )
         save_config['mode'] = SHORTCUTS['save_mode'][mode_choice]
         save_config['compression'] = 9
    else:
         save_config['mode'] = 'auto' 
         save_config['compression'] = IntPrompt.ask("Compression/Quality (0-9)", default=9 if target_fmt=="PNG" else 0)

    conflict_choice = Prompt.ask(
        "[bold white]Conflict Resolution:[/bold white] [dim][1: Overwrite, 2: Keep Both][/dim]",
        choices=["1", "2"], default="1"
    )
    save_config['conflict'] = SHORTCUTS['conflict'][conflict_choice]

    cpu_cores = os.cpu_count() or 4
    max_workers = min(cpu_cores, 6)
    
    run_processing(files_to_process, input_path, output_path, res_config, save_config, max_workers)

def cli_mode():
    parser = argparse.ArgumentParser(description="Talvaar Image Optimizer & Resizer (Bedrock Optimized)")
    parser.add_argument("input_pos", nargs="?", help="Input file or directory")
    parser.add_argument("--i", "--input", dest="input_flag", help="Input file or directory")
    parser.add_argument("-o", "--output", help="Output directory")
    
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--width", type=int, help="Target width (pixels)")
    group.add_argument("--percent", type=float, help="Resize percentage (e.g., 50.0)")
    
    parser.add_argument("--height", type=int, default=0, help="Target height")
    
    parser.add_argument("--algorithm", choices=['auto', 'nearest', 'lanczos', 'bilinear', 'bicubic', 'box', 'hamming'], default='auto', help="Resizing algorithm")

    parser.add_argument("--prefix", default="", help="Prefix for output filenames")
    parser.add_argument("--suffix", default="", help="Suffix for output filenames")

    parser.add_argument("--report", action="store_true", help="Show pre-analysis report before processing")
    
    # Logging Flag
    parser.add_argument("--log", action="store_true", help="Enable verbose file logging (resizer.log)")

    parser.add_argument("--mode", choices=['auto', 'rgba', 'palette', 'rgb'], default='auto', help="Save mode")
    parser.add_argument("--format", choices=['PNG', 'JPG', 'JPEG', 'WEBP'], default='PNG', help="Output format")
    parser.add_argument("--compression", type=int, default=9, help="Compression level (0-9)")
    
    parser.add_argument("--ignore-transparency", action="store_true", help="Discard alpha channel (Force RGB)")
    
    parser.add_argument("--conflict", choices=['overwrite', 'keep_both'], default='overwrite', help="Conflict resolution")
    parser.add_argument("--threads", type=int, default=0, help="Number of threads (0 = auto)")

    args = parser.parse_args()

    # Configure Logging
    setup_logging(verbose=args.log)

    # Determine input path from flags/positional args
    input_path = args.input_flag or args.input_pos
    
    # If no input path is specified by any flag, enter interactive mode.
    if not input_path:
        interactive_mode()
        return

    files_to_process = []
    if os.path.isdir(input_path):
        types = ('**/*.png', '**/*.jpg', '**/*.jpeg', '**/*.tga', '**/*.webp')
        for t in types:
            files_to_process.extend(glob.glob(os.path.join(input_path, t), recursive=True))
        console.print(f"[green]Found {len(files_to_process)} images in '{input_path}'.[/green]")
    elif os.path.isfile(input_path):
        files_to_process.append(input_path)
    else:
        console.print(f"[red]Error: Invalid input path '{input_path}'[/red]")
        sys.exit(1)

    if not files_to_process:
        console.print("[yellow]No images found.[/yellow]")
        sys.exit(0)

    output_path = args.output if args.output else "output"
    
    if not os.path.exists(output_path):
        try:
            os.makedirs(output_path, exist_ok=True)
            console.print(f"[dim]Created output directory: {output_path}[/dim]")
        except OSError as e:
            console.print(f"[red]Error creating output directory: {e}[/red]")
            sys.exit(1)

    res_config = {}
    if args.percent:
        res_config['mode'] = 'percentage'
        res_config['val'] = args.percent
    elif args.width:
        res_config['mode'] = 'pixel'
        res_config['width'] = args.width
        res_config['height'] = args.height
    else:
        res_config['mode'] = 'percentage'
        res_config['val'] = 100.0

    save_config = {
        'mode': args.mode,
        'compression': args.compression,
        'conflict': args.conflict,
        'format': args.format,
        'ignore_transparency': args.ignore_transparency,
        'prefix': args.prefix,
        'suffix': args.suffix,
        'algorithm': args.algorithm,
        'show_report': args.report
    }

    cpu_cores = os.cpu_count() or 4
    max_workers = args.threads if args.threads > 0 else min(cpu_cores, 6)

    run_processing(files_to_process, input_path, output_path, res_config, save_config, max_workers)