#!/usr/bin/env python3
"""
NSE Factsheet Sector Representation Parser

This script parses PDF factsheets and extracts sector representation data,
populating a CSV with indices as rows and sectors as columns.
"""

import re
from pathlib import Path
from typing import Dict, List, Set, Optional

import pdfplumber
import pandas as pd

from pdf_utils import extract_index_name_from_pdf


def normalize_value(value: any) -> str:
    """
    Normalize extracted values by cleaning whitespace and handling None.
    
    Args:
        value: Raw value string
        
    Returns:
        Cleaned value string
    """
    if value is None:
        return ""
    if isinstance(value, (int, float)):
        return str(value)
    value_str = str(value).strip()
    # Remove extra whitespace and newlines
    value_str = re.sub(r'\s+', ' ', value_str)
    return value_str


def extract_text_from_pdf(pdf_path: Path) -> str:
    """
    Extract all text from a PDF file.
    
    Args:
        pdf_path: Path to the PDF file
        
    Returns:
        Combined text from all pages
    """
    try:
        text = ""
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        return text
    except Exception as e:
        print(f"  Error reading PDF: {e}")
        return ""


def extract_sectors_from_pdf(pdf_path: Path) -> Optional[Dict[str, str]]:
    """
    Extract sector representation data from a PDF.
    
    Args:
        pdf_path: Path to the PDF file
        
    Returns:
        Dictionary mapping sector names to weights, or None if not found
    """
    try:
        sectors = {}
        
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                tables = page.extract_tables()
                
                # Look for sector representation table
                for table in tables:
                    if not table or len(table) < 2:
                        continue
                    
                    # Check if this is the sector table (has "Sector" and "Weight" in header)
                    first_row = [normalize_value(cell) for cell in table[0]]
                    first_row_text = ' '.join(first_row).lower()
                    
                    if 'sector' in first_row_text and ('weight' in first_row_text or '%' in first_row_text):
                        # Find which column is sector name and which is weight
                        sector_col = None
                        weight_col = None
                        
                        for idx, header in enumerate(first_row):
                            header_lower = header.lower()
                            if 'sector' in header_lower:
                                sector_col = idx
                            elif 'weight' in header_lower or '%' in header_lower:
                                weight_col = idx
                        
                        # Default: assume first column is sector, second is weight
                        if sector_col is None:
                            sector_col = 0
                        if weight_col is None:
                            weight_col = 1
                        
                        # Extract sector data
                        for row in table[1:]:
                            if len(row) > max(sector_col, weight_col):
                                sector_name = normalize_value(row[sector_col])
                                weight = normalize_value(row[weight_col])
                                
                                # Clean weight (remove % sign, keep numeric value)
                                weight = re.sub(r'%', '', weight).strip()
                                
                                # Normalize sector name
                                sector_name = normalize_sector_name(sector_name)
                                
                                if sector_name and weight and sector_name.lower() not in ['', 'total', 'others']:
                                    sectors[sector_name] = weight
                        
                        # Found sector table, no need to check other tables
                        if sectors:
                            return sectors
        
        return None
        
    except Exception as e:
        print(f"  Error extracting sectors: {e}")
        return None


def normalize_sector_name(sector: str) -> str:
    """
    Normalize sector name by removing trailing spaces and cleaning up.
    
    Args:
        sector: Raw sector name
        
    Returns:
        Normalized sector name
    """
    return sector.strip()


def load_existing_sector_csv(csv_path: Path) -> tuple[pd.DataFrame, Set[str]]:
    """
    Load existing sector CSV or create new one.
    
    Args:
        csv_path: Path to the CSV file
        
    Returns:
        Tuple of (DataFrame, set of existing sector names)
    """
    if csv_path.exists():
        try:
            df = pd.read_csv(csv_path)
            
            # Remove unnamed columns
            df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
            
            # Normalize column names (remove trailing spaces)
            df.columns = [normalize_sector_name(col) if col != 'Indices' else col for col in df.columns]
            
            # Get existing sector columns (all columns except "Indices")
            existing_sectors = set()
            if 'Indices' in df.columns:
                existing_sectors = {normalize_sector_name(col) for col in df.columns if col != 'Indices'}
            
            # Remove rows that are empty or just headers
            if len(df) > 0:
                # Remove rows where Indices column is empty or NaN
                df = df[df['Indices'].notna() & (df['Indices'] != '')].copy()
            
            return df, existing_sectors
        except Exception as e:
            print(f"Warning: Could not read existing CSV: {e}. Creating new CSV.")
    
    # Create new DataFrame with just "Indices" column
    df = pd.DataFrame(columns=['Indices'])
    return df, set()


def save_sector_csv(df: pd.DataFrame, csv_path: Path):
    """
    Save DataFrame to CSV file.
    
    Args:
        df: DataFrame to save
        csv_path: Path to save the CSV file
    """
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(csv_path, index=False)


def get_manual_index_filename_mapping() -> Dict[str, str]:
    """
    Return a manual mapping of index names to filenames for hard-to-match cases.
    
    Returns:
        Dictionary mapping normalized index names to filenames
    """
    return {
        'nifty 200': 'ind_nifty_200.pdf',
        'nifty500 low volatility 50': 'Factsheet_Nifty500LowVolatility50.pdf',
        'nifty india defence': 'Factsheet_NiftyIndiaDefence.pdf',
        'nifty midsmallcap 400': 'ind_Nifty_MidSmallcap_400.pdf',
        'nifty smallcap 250': 'ind_nifty_smallcap_250.pdf',
        'nifty total market': 'Factsheet_NiftyTotalMarket.pdf',
    }


def backfill_filenames(df: pd.DataFrame, factsheets_dir: Path) -> pd.DataFrame:
    """
    Backfill missing filenames by matching PDF files to existing rows.
    
    Args:
        df: DataFrame with potentially missing filenames
        factsheets_dir: Directory containing PDF factsheets
        
    Returns:
        DataFrame with updated filenames
    """
    if df.empty or 'Filename' not in df.columns:
        return df
    
    missing_filename_mask = df['Filename'].isna() | (df['Filename'] == '')
    if not missing_filename_mask.any():
        return df
    
    # Get all PDF files and extract index names from them
    pdf_files = sorted(factsheets_dir.glob("*.pdf"))
    pdf_index_map = {}  # Map index_name -> filename
    
    print(f"  Extracting index names from {len(pdf_files)} PDF files...")
    for pdf_path in pdf_files:
        try:
            text = extract_text_from_pdf(pdf_path)
            if text:
                index_name = extract_index_name_from_pdf(text, pdf_path.name)
                if index_name:
                    # Normalize index name for matching (lowercase, remove extra spaces)
                    normalized = ' '.join(index_name.lower().split())
                    pdf_index_map[normalized] = pdf_path.name
        except Exception:
            continue
    
    # Get manual mapping for hard-to-match cases
    manual_mapping = get_manual_index_filename_mapping()
    
    # Match existing rows to PDF files
    matched_count = 0
    for idx in df[missing_filename_mask].index:
        index_name = str(df.loc[idx, 'Indices'])
        normalized_index = ' '.join(index_name.lower().split())
        
        # Try manual mapping first
        if normalized_index in manual_mapping:
            filename = manual_mapping[normalized_index]
            # Verify file exists
            if (factsheets_dir / filename).exists():
                df.loc[idx, 'Filename'] = filename
                matched_count += 1
                continue
        
        # Try exact match from PDF extraction
        if normalized_index in pdf_index_map:
            df.loc[idx, 'Filename'] = pdf_index_map[normalized_index]
            matched_count += 1
        else:
            # Try fuzzy matching - check if key words match
            index_words = set(word for word in normalized_index.split() if len(word) > 3)
            best_match = None
            best_score = 0
            
            for pdf_index, filename in pdf_index_map.items():
                pdf_words = set(word for word in pdf_index.split() if len(word) > 3)
                common_words = index_words & pdf_words
                if len(common_words) >= 2:  # At least 2 significant words match
                    score = len(common_words)
                    if score > best_score:
                        best_score = score
                        best_match = filename
            
            if best_match:
                df.loc[idx, 'Filename'] = best_match
                matched_count += 1
    
    if matched_count > 0:
        print(f"  ✓ Matched {matched_count} rows to PDF files")
    
    return df


def process_sectors_from_factsheets(factsheets_dir: Path, csv_path: Path):
    """
    Process all factsheet PDFs and extract sector representation data.
    
    Args:
        factsheets_dir: Directory containing PDF factsheets
        csv_path: Path to output CSV file
    """
    # Load existing CSV
    df, existing_sectors = load_existing_sector_csv(csv_path)
    
    # First, try to backfill missing filenames for existing rows
    if not df.empty:
        print("Checking for missing filenames in existing rows...")
        df = backfill_filenames(df, factsheets_dir)
    
    # Get list of PDFs to process
    pdf_files = sorted(factsheets_dir.glob("*.pdf"))
    
    if not pdf_files:
        print(f"No PDF files found in {factsheets_dir}")
        return
    
    print(f"Found {len(pdf_files)} PDF file(s) to process.\n")
    
    success_count = 0
    error_count = 0
    skipped_count = 0
    
    # Track all sectors we encounter (for column management)
    all_sectors = existing_sectors.copy()
    
    for pdf_path in pdf_files:
        print(f"Processing: {pdf_path.name}...")
        
        try:
            # Extract text to get index name
            text = extract_text_from_pdf(pdf_path)
            index_name = extract_index_name_from_pdf(text, pdf_path.name)
            
            # Check if already exists in CSV (using filename to avoid duplicates of same file)
            if not df.empty and 'Filename' in df.columns:
                existing = df[df['Filename'] == pdf_path.name]
                if not existing.empty:
                    print(f"  ⏭ Already exists in CSV (filename: {pdf_path.name}), skipping...")
                    skipped_count += 1
                    continue
            
            # Also check by index name if Filename column doesn't exist yet
            if not df.empty and 'Indices' in df.columns and 'Filename' not in df.columns:
                existing = df[df['Indices'].str.contains(index_name, case=False, na=False, regex=False)]
                if not existing.empty:
                    print(f"  ⏭ Already exists in CSV (index: {index_name}), skipping...")
                    skipped_count += 1
                    continue
            
            # Extract sector data
            sectors_data = extract_sectors_from_pdf(pdf_path)
            
            if not sectors_data:
                print(f"  ✗ No sector data found")
                error_count += 1
                continue
            
            # Add new sectors to our set
            all_sectors.update(sectors_data.keys())
            
            # Create new row data
            row_data = {
                'Indices': index_name,
                'Filename': pdf_path.name
            }
            
            # Add all existing sectors (with empty values)
            for sector in existing_sectors:
                row_data[sector] = ""
            
            # Add data for sectors found in this PDF
            for sector, weight in sectors_data.items():
                row_data[sector] = weight
            
            # Create new row DataFrame
            new_row = pd.DataFrame([row_data])
            
            # Append to existing DataFrame (append mode)
            df = pd.concat([df, new_row], ignore_index=True)
            
            print(f"  ✓ Extracted {len(sectors_data)} sectors for {index_name}")
            success_count += 1
            
        except Exception as e:
            print(f"  ✗ Error processing {pdf_path.name}: {e}")
            import traceback
            traceback.print_exc()
            error_count += 1
    
    # Ensure all columns exist in DataFrame (all sectors found across all PDFs)
    if not df.empty:
        # Make sure Filename column exists
        if 'Filename' not in df.columns:
            df['Filename'] = ""
        
        # Make sure all sectors are columns
        for sector in all_sectors:
            if sector not in df.columns:
                df[sector] = ""
        
        # Reorder columns: Indices first, Filename second, then all sectors alphabetically
        sector_cols = sorted([col for col in df.columns if col not in ['Indices', 'Filename']])
        df = df[['Indices', 'Filename'] + sector_cols]
        
        # Fill NaN with empty strings for cleaner CSV output
        df = df.fillna("")
    
    # Save updated CSV
    if success_count > 0:
        save_sector_csv(df, csv_path)
        print(f"\n✓ Saved {success_count} record(s) to {csv_path}")
        print(f"  Total unique sectors: {len(all_sectors)}")
    
    # Summary
    print(f"\n{'='*60}")
    print(f"Processing complete!")
    print(f"  Successfully processed: {success_count}")
    print(f"  Skipped (already exists): {skipped_count}")
    print(f"  Errors: {error_count}")


def main():
    """
    Main entry point for the script.
    """
    BASE_DIR = Path(__file__).parent
    FACTSHEETS_DIR = BASE_DIR / "Factsheets"
    CSV_PATH = BASE_DIR / "parsed_data" / "Sector-Table 1.csv"
    
    # Process all factsheets
    process_sectors_from_factsheets(FACTSHEETS_DIR, CSV_PATH)


if __name__ == "__main__":
    main()

