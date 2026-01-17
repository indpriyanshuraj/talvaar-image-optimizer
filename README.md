# Talvaar Image Optimizer

A powerful, analysis-driven command-line tool for resizing and optimizing images, specifically tailored for game textures and assets.

This tool is designed to be both a simple interactive utility and a powerful CLI tool for batch processing. It analyzes images to make smart decisions about optimization, ensuring that transparent textures (like glass) are preserved while opaque textures (like wood or stone) are made as small as possible.

## Features

- **Interactive & CLI Modes**: Run with `python main.py` for a fully interactive experience, or use flags for automation.
- **Smart Auto-Optimization**: Automatically analyzes image properties (transparency, color count) to choose the best optimization strategy (RGB, RGBA, or Palette).
- **Advanced Resizing**: Supports multiple resizing algorithms, with automatic selection (`NEAREST` for pixel art, `LANCZOS` for detailed textures).
- **File Naming**: Add a `--prefix` or `--suffix` to output files for easy organization.
- **Pre-Analysis Report**: Use the `--report` flag to see a summary of all images before you process them.
- **Logging**: Use the `--log` flag to generate a `resizer.log` file with detailed information about every step of the process.
- **Type-Safe & Tested**: The codebase includes a full suite of unit tests and uses static type checking for improved reliability.

## Usage

### Interactive Mode

For the simplest usage, just run the script without any arguments. It will ask you a series of questions to guide you through the process.

```bash
python main.py
```

It will prompt for:
- Input and output directories.
- Whether to run a pre-analysis report.
- Resizing mode and dimensions.
- Resizing algorithm (if resizing).
- Prefix/suffix for filenames.
- Whether to ignore transparency.
- And more.

### Command-Line Interface (CLI) Mode

Use flags to automate your workflow.

**Basic Optimization (No Resizing):**
```bash
# Optimize all images in the 'input' folder and save to 'output'
python main.py -i input -o output
```

**Resize by Percentage:**
```bash
# Resize all images in 'input' to 50% and save to 'output_resized'
python main.py -i input -o output_resized --percent 50
```

**Resize to Fixed Width (Auto Height):**
```bash
# Resize all images to a width of 128px, maintaining aspect ratio
python main.py -i input -o output_128 --width 128
```

**Advanced Example (All Features):**
```bash
python main.py "assets/minecraft/textures/" \
    -o "optimized_textures/" \
    --percent 50 \
    --algorithm lanczos \
    --suffix "_half" \
    --report \
    --log \
    --ignore-transparency
```

## All CLI Options

| Flag                      | Description                                                               | Default      |
| ------------------------- | ------------------------------------------------------------------------- | ------------ |
| `input_pos` or `--i`      | Input file or directory.                                                  | -            |
| `-o`, `--output`          | Output directory.                                                         | `output`     |
| `--width`                 | Target width in pixels.                                                   | -            |
| `--percent`               | Resize percentage (e.g., 50.0).                                           | -            |
| `--height`                | Target height. Set to 0 for auto aspect ratio.                            | `0`          |
| `--algorithm`             | Resizing algorithm (`auto`, `nearest`, `lanczos`, etc.).                  | `auto`       |
| `--prefix` / `--suffix`   | Add a prefix or suffix to output filenames.                               | ""           |
| `--report`                | Show a pre-analysis report before processing.                             | `False`      |
| `--log`                   | Enable verbose file logging to `resizer.log`.                             | `False`      |
| `--mode`                  | Save mode (`auto`, `rgba`, `palette`, `rgb`).                             | `auto`       |
| `--format`                | Output format (`PNG`, `JPG`, `WEBP`).                                     | `PNG`        |
| `--compression`           | Compression level (0-9). For JPG, 0 is best quality.                      | `9`          |
| `--ignore-transparency`   | Discard alpha channel (Force RGB).                                        | `False`      |
| `--conflict`              | What to do on filename conflict (`overwrite`, `keep_both`).               | `overwrite`  |
| `--threads`               | Number of threads to use.                                                 | `auto`       |

## Project Files & Documentation

- **User Guide & Internals**: [docs/](docs/)
- **Dependencies**: [requirements.txt](requirements.txt)
- **Contributors**: [CONTRIBUTORS.md](CONTRIBUTORS.md)
- **License**: [LICENSE](LICENSE)
- **Third-party Notices**: [NOTICE](NOTICE)

## License

This project is licensed under the Apache 2.0 License. See the [LICENSE](LICENSE) file for details.

## Contributing

- **Creator / Contributor**: Talvaar@indpriyanshuraj
- **Co-Pilot / Refactoring**: Gemini
- **Consultant / Prototyping**: ChatGPT (Feedback, Base/Proto code, Suggestions)

See the [NOTICE](NOTICE) file for information on third-party libraries and other acknowledgments.
