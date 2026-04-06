#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Sh_Sci_Fig — Scientific Figure Extractor
Main CLI entry point for extracting figures and sub-figures from academic PDFs.
"""

import argparse
import sys
import os
import traceback

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils import setup_logger, validate_pdf_path_bool, check_dependencies


def parse_args():
    parser = argparse.ArgumentParser(
        prog="Sh_Sci_Fig",
        description="Extract figures and sub-figures from academic PDF papers.",
    )

    parser.add_argument(
        "input",
        help="Path to the PDF file",
    )
    parser.add_argument(
        "-f",
        "--figure",
        type=int,
        help="Figure number to extract (e.g., 2 for Figure 2)",
    )
    parser.add_argument(
        "-s",
        "--subfigure",
        type=str,
        help="Sub-figure label to extract (e.g., c for sub-figure c)",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        default=".",
        help="Output directory (default: current directory)",
    )
    parser.add_argument(
        "-d",
        "--dpi",
        type=int,
        default=600,
        help="Output resolution in DPI (default: 600)",
    )
    parser.add_argument(
        "-l",
        "--list",
        action="store_true",
        help="List all available figure numbers in the PDF",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        dest="extract_all",
        help="Extract all figures from the PDF",
    )
    parser.add_argument(
        "--format",
        type=str,
        default="png",
        choices=["png", "jpg", "jpeg"],
        help="Output image format (default: png)",
    )
    parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="Suppress info messages, only show warnings/errors",
    )

    return parser.parse_args()


def main():
    args = parse_args()

    import logging

    level = logging.WARNING if args.quiet else logging.INFO
    logger = setup_logger(level=level)

    # --- Pre-flight checks ---

    # Check dependencies
    dep_errors = check_dependencies()
    if dep_errors:
        for err in dep_errors:
            logger.error(err)
        sys.exit(1)

    # Validate input PDF
    if not validate_pdf_path_bool(args.input):
        if not os.path.exists(args.input):
            logger.error(f"File not found: {args.input}")
        elif not args.input.lower().endswith(".pdf"):
            logger.error(f"Not a PDF file: {args.input}")
        else:
            logger.error(f"Invalid PDF file: {args.input}")
        sys.exit(1)

    # Validate DPI range
    if args.dpi < 72 or args.dpi > 2400:
        logger.error(f"DPI must be between 72 and 2400, got {args.dpi}")
        sys.exit(1)

    # Ensure output directory exists
    try:
        os.makedirs(args.output, exist_ok=True)
    except OSError as e:
        logger.error(f"Cannot create output directory '{args.output}': {e}")
        sys.exit(1)

    # --- Import heavy modules after checks pass ---
    from src.pdf_parser import PDFParser
    from src.figure_detector import FigureDetector
    from src.subfigure_splitter import SubfigureSplitter
    from src.image_processor import ImageProcessor

    logger.info(f"Processing: {args.input}")
    logger.info(f"DPI: {args.dpi}")

    # --- Step 1: Parse PDF ---
    try:
        pdf_parser = PDFParser(args.input, dpi=args.dpi)
    except Exception as e:
        logger.error(f"Failed to open PDF: {e}")
        sys.exit(1)

    try:
        # --- Step 2: Detect figures ---
        detector = FigureDetector(pdf_parser)
        figures = detector.detect_all_figures()

        # --list mode
        if args.list:
            if not figures:
                logger.info("No figures detected in this PDF.")
            else:
                logger.info(f"Found {len(figures)} figure(s):")
                for fig in figures:
                    sublabels = fig.get("sublabels", [])
                    sub_str = (
                        f" (sub-figures: {', '.join(sublabels)})" if sublabels else ""
                    )
                    logger.info(
                        f"  Figure {fig['number']} — page {fig['page']}{sub_str}"
                    )
            sys.exit(0)

        # --all mode
        if args.extract_all:
            if not figures:
                logger.warning("No figures detected. Nothing to extract.")
                sys.exit(0)
            processor = ImageProcessor(output_dir=args.output, fmt=args.format)
            count = 0
            for fig in figures:
                try:
                    output_path = processor.save_figure(fig["image"], fig["number"])
                    logger.info(f"Extracted: {output_path}")
                    count += 1
                except Exception as e:
                    logger.warning(f"Failed to save Figure {fig['number']}: {e}")
            logger.info(f"Done. Extracted {count} figure(s).")
            sys.exit(0)

        # Single figure mode: --figure is required
        if args.figure is None:
            logger.error(
                "Please specify a figure number with -f/--figure, or use --list / --all"
            )
            sys.exit(1)

        # Find target figure
        target = detector.get_figure(args.figure)
        if target is None:
            available = [str(f["number"]) for f in figures]
            logger.error(
                f"Figure {args.figure} not found. "
                f"Available figures: "
                f"{', '.join(available) if available else 'none detected'}"
            )
            sys.exit(1)

        # --- Step 3: Extract ---
        processor = ImageProcessor(output_dir=args.output, fmt=args.format)

        if args.subfigure:
            splitter = SubfigureSplitter(pdf_parser)
            subfig_image = splitter.extract_subfigure(target, args.subfigure)

            if subfig_image is None:
                logger.warning(
                    f"Sub-figure '{args.subfigure}' not found in "
                    f"Figure {args.figure}. Returning entire figure instead."
                )
                output_path = processor.save_figure(target["image"], args.figure)
            else:
                output_path = processor.save_subfigure(
                    subfig_image, args.figure, args.subfigure
                )
            logger.info(f"Extracted: {output_path}")
        else:
            output_path = processor.save_figure(target["image"], args.figure)
            logger.info(f"Extracted: {output_path}")

        logger.info("Done.")

    except KeyboardInterrupt:
        logger.warning("Interrupted by user.")
        sys.exit(130)
    except MemoryError:
        logger.error("Out of memory. Try a lower DPI with -d/--dpi (e.g., -d 300)")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        logger.error(traceback.format_exc())
        sys.exit(1)
    finally:
        pdf_parser.close()


if __name__ == "__main__":
    main()
