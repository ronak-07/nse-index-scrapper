#!/usr/bin/env python3
"""
Find and Move Corrupted PDF Files

This script scans a directory for PDF files, identifies corrupted ones
(HTML error pages masquerading as PDFs), and moves them to a separate directory.
"""

import pdfplumber
from pathlib import Path
from typing import List, Tuple


def check_pdf_validity(pdf_file: Path) -> Tuple[bool, str]:
    """
    Check if a file is a valid PDF.
    
    Args:
        pdf_file: Path to the PDF file to check
        
    Returns:
        Tuple of (is_valid: bool, error_message: str)
    """
    try:
        # Try to open with pdfplumber
        with pdfplumber.open(pdf_file) as pdf:
            if len(pdf.pages) > 0:
                # Quick check: read first few bytes to see if it's actually a PDF
                with open(pdf_file, 'rb') as f:
                    header = f.read(4)
                    if header == b'%PDF':
                        return True, "Valid PDF"
                    else:
                        return False, f"Not a PDF (header: {header})"
            else:
                return False, "Empty PDF"
    except Exception as e:
        return False, f"Error - {str(e)[:50]}"


def find_and_move_corrupt_pdfs(
    source_dir: Path,
    corrupt_dir: Path,
    valid_dir: Path = None,
    dry_run: bool = False
) -> Tuple[List[Path], List[Path]]:
    """
    Find corrupted PDF files and move them to a separate directory.
    Optionally move valid files to another directory.
    
    Args:
        source_dir: Directory containing PDF files to check
        corrupt_dir: Directory to move corrupted files to
        valid_dir: Optional directory to move valid files to
        dry_run: If True, don't actually move files, just report
        
    Returns:
        Tuple of (valid_files: List[Path], corrupted_files: List[Path])
    """
    # Create directories if they don't exist
    corrupt_dir.mkdir(parents=True, exist_ok=True)
    if valid_dir:
        valid_dir.mkdir(parents=True, exist_ok=True)
    
    # Find all PDF files
    pdf_files = sorted(source_dir.glob('*.pdf'))
    
    if not pdf_files:
        print(f"No PDF files found in {source_dir}")
        return [], []
    
    print(f"Found {len(pdf_files)} PDF files to check\n")
    
    valid_files = []
    corrupted_files = []
    
    # Check each PDF file
    for pdf_file in pdf_files:
        is_valid, error_msg = check_pdf_validity(pdf_file)
        
        if is_valid:
            valid_files.append(pdf_file)
            print(f"✓ {pdf_file.name}: Valid PDF")
        else:
            corrupted_files.append(pdf_file)
            print(f"✗ {pdf_file.name}: {error_msg}")
    
    # Print summary
    print(f"\nSummary: {len(valid_files)} valid, {len(corrupted_files)} corrupted")
    
    # Move valid files if valid_dir is specified
    if valid_files and valid_dir:
        if dry_run:
            print(f"\n[DRY RUN] Would move {len(valid_files)} valid files to {valid_dir}/")
            for pdf_file in valid_files:
                print(f"  Would move: {pdf_file.name}")
        else:
            print(f"\nMoving {len(valid_files)} valid files to {valid_dir}/ directory...")
            for pdf_file in valid_files:
                dest = valid_dir / pdf_file.name
                pdf_file.rename(dest)
                print(f"  Moved: {pdf_file.name} → Factsheets-Final/")
    
    # Move corrupted files
    if corrupted_files:
        if dry_run:
            print(f"\n[DRY RUN] Would move {len(corrupted_files)} corrupted files to {corrupt_dir}/")
            for pdf_file in corrupted_files:
                print(f"  Would move: {pdf_file.name}")
        else:
            print(f"\nMoving {len(corrupted_files)} corrupted files to {corrupt_dir}/ directory...")
            for pdf_file in corrupted_files:
                dest = corrupt_dir / pdf_file.name
                pdf_file.rename(dest)
                print(f"  Moved: {pdf_file.name} → corrupt/")
    else:
        print("\nNo corrupted files found!")
    
    return valid_files, corrupted_files


def main():
    """
    Main entry point for the script.
    """
    import sys
    
    # Default directories
    BASE_DIR = Path(__file__).parent
    SOURCE_DIR = BASE_DIR / "Factsheets"
    CORRUPT_DIR = BASE_DIR / "corrupt"
    VALID_DIR = BASE_DIR / "Factsheets-Final"
    
    # Check for command line arguments
    if len(sys.argv) > 1:
        SOURCE_DIR = Path(sys.argv[1])
    
    if len(sys.argv) > 2:
        CORRUPT_DIR = Path(sys.argv[2])
    
    if len(sys.argv) > 3:
        VALID_DIR = Path(sys.argv[3])
    
    # Check for flags
    dry_run = "--dry-run" in sys.argv or "-n" in sys.argv
    no_valid_move = "--no-valid" in sys.argv  # Don't move valid files
    
    # Validate source directory exists
    if not SOURCE_DIR.exists():
        print(f"Error: Source directory '{SOURCE_DIR}' does not exist.")
        sys.exit(1)
    
    if not SOURCE_DIR.is_dir():
        print(f"Error: '{SOURCE_DIR}' is not a directory.")
        sys.exit(1)
    
    print(f"Scanning: {SOURCE_DIR}")
    if not no_valid_move:
        print(f"Moving valid files to: {VALID_DIR}")
    print(f"Moving corrupted files to: {CORRUPT_DIR}\n")
    
    if dry_run:
        print("[DRY RUN MODE - No files will be moved]\n")
    
    # Find and move corrupted PDFs
    valid_dir = VALID_DIR if not no_valid_move else None
    valid_files, corrupted_files = find_and_move_corrupt_pdfs(
        SOURCE_DIR,
        CORRUPT_DIR,
        valid_dir=valid_dir,
        dry_run=dry_run
    )
    
    # Final summary
    print(f"\n{'='*60}")
    print(f"Final Results:")
    if valid_dir:
        print(f"  Valid PDFs moved to {VALID_DIR}: {len(valid_files)}")
    else:
        print(f"  Valid PDFs remaining in source: {len(valid_files)}")
    print(f"  Corrupted files moved to {CORRUPT_DIR}: {len(corrupted_files)}")


if __name__ == "__main__":
    main()

