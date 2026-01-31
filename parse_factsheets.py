#!/usr/bin/env python3
"""
NSE Factsheet PDF Parser

This script parses PDF factsheets from the Factsheets directory and extracts
index information to populate the Indices-Table 1.csv file.
"""

import re
from pathlib import Path
from typing import Dict, List, Optional

import pdfplumber
import pandas as pd

from pdf_utils import extract_index_name_from_pdf


# CSV column names
CSV_COLUMNS = [
    "Indices Name",
    "Filename",
    "Methodology",
    "No. of Constituents",
    "Launch Date",
    "Base Date",
    "Base Value",
    "Calculation Frequency",
    "Index Rebalancing",
    "Price Returns QTD",
    "Price Returns YTD",
    "Price Returns 1 year",
    "Price Returns 5 years",
    "Price Returns Since Inception",
    "Total Returns QTD",
    "Total Returns YTD",
    "Total Returns 1 year",
    "Total Returns 5 years",
    "Total Returns Since Inception",
    "Standard Deviation 1 year",
    "Standard Deviation 5 year",
    "Standard Deviation Since Inception",
    "Beta (Nifty 50) 1 year",
    "Beta (Nifty 50) 5 years",
    "Beta (Nifty 50) Since Inception",
    "P/E",
    "P/B",
    "Dividend Yield"
]


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


def extract_tables_from_pdf(pdf_path: Path) -> List[List[List[str]]]:
    """
    Extract all tables from a PDF file.
    
    Args:
        pdf_path: Path to the PDF file
        
    Returns:
        List of tables, where each table is a list of rows
    """
    try:
        all_tables = []
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                tables = page.extract_tables()
                if tables:
                    all_tables.extend(tables)
        return all_tables
    except Exception as e:
        print(f"  Error extracting tables: {e}")
        return []


def normalize_value(value: str) -> str:
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


def find_value_in_tables(tables: List[List[List[str]]], search_key: str) -> Optional[str]:
    """
    Search for a value in tables by looking for a key in any column.
    
    Args:
        tables: List of tables
        search_key: Key to search for (case-insensitive partial match)
        
    Returns:
        Found value or None
    """
    search_key_lower = search_key.lower()
    
    for table in tables:
        if not table:
            continue
        for row in table:
            if not row:
                continue
            # Search all cells in the row
            for i, cell in enumerate(row):
                cell_value = normalize_value(cell)
                if search_key_lower in cell_value.lower():
                    # Try to get value from next cell (most common case: key in first column, value in second)
                    if i + 1 < len(row):
                        next_value = normalize_value(row[i + 1])
                        if next_value and next_value.lower() not in search_key_lower:
                            return next_value
                    # If key is in second column, value might be in first or third
                    if i == 1 and len(row) > 0:
                        first_value = normalize_value(row[0])
                        if first_value and first_value.lower() not in search_key_lower:
                            return first_value
                    if i + 2 < len(row):
                        third_value = normalize_value(row[i + 2])
                        if third_value and third_value.lower() not in search_key_lower:
                            return third_value
    return None


def extract_returns_from_table(tables: List[List[List[str]]]) -> Dict[str, str]:
    """
    Extract returns data from the returns table (Table 2 format).
    
    Args:
        tables: List of tables
        
    Returns:
        Dictionary with returns fields
    """
    returns = {}
    
    for table in tables:
        if not table or len(table) < 2:
            continue
        
        # Look for returns table pattern: headers with QTD, YTD, 1 Year, 5 Years, Since Inception
        first_row = [normalize_value(cell) for cell in table[0]]
        headers_text = ' '.join(first_row).lower()
        
        if any(keyword in headers_text for keyword in ['qtd', 'ytd', '1 year', '5 years', 'since']):
            # Find header column indices
            header_cols = {}
            for idx, header in enumerate(first_row):
                header_lower = header.lower()
                if 'qtd' in header_lower:
                    header_cols['qtd'] = idx
                elif 'ytd' in header_lower:
                    header_cols['ytd'] = idx
                elif ('1 year' in header_lower or '1year' in header_lower) and '5' not in header_lower:
                    header_cols['1year'] = idx
                elif ('5 years' in header_lower or '5year' in header_lower):
                    header_cols['5years'] = idx
                elif 'since' in header_lower and 'inception' in header_lower:
                    header_cols['since'] = idx
            
            # Find Price Return row
            for row in table[1:]:
                row_values = [normalize_value(cell) for cell in row]
                if len(row_values) > 1 and 'price return' in row_values[0].lower():
                    if 'qtd' in header_cols and header_cols['qtd'] < len(row_values):
                        returns['Price Returns QTD'] = row_values[header_cols['qtd']]
                    if 'ytd' in header_cols and header_cols['ytd'] < len(row_values):
                        returns['Price Returns YTD'] = row_values[header_cols['ytd']]
                    if '1year' in header_cols and header_cols['1year'] < len(row_values):
                        returns['Price Returns 1 year'] = row_values[header_cols['1year']]
                    if '5years' in header_cols and header_cols['5years'] < len(row_values):
                        returns['Price Returns 5 years'] = row_values[header_cols['5years']]
                    if 'since' in header_cols and header_cols['since'] < len(row_values):
                        value = row_values[header_cols['since']]
                        if value:  # Only set if value exists
                            returns['Price Returns Since Inception'] = value
                    break
            
            # Find Total Return row
            for row in table[1:]:
                row_values = [normalize_value(cell) for cell in row]
                if len(row_values) > 1 and 'total return' in row_values[0].lower():
                    if 'qtd' in header_cols and header_cols['qtd'] < len(row_values):
                        returns['Total Returns QTD'] = row_values[header_cols['qtd']]
                    if 'ytd' in header_cols and header_cols['ytd'] < len(row_values):
                        returns['Total Returns YTD'] = row_values[header_cols['ytd']]
                    if '1year' in header_cols and header_cols['1year'] < len(row_values):
                        returns['Total Returns 1 year'] = row_values[header_cols['1year']]
                    if '5years' in header_cols and header_cols['5years'] < len(row_values):
                        value = row_values[header_cols['5years']]
                        if value:  # Only set if value exists
                            returns['Total Returns 5 years'] = value
                    if 'since' in header_cols and header_cols['since'] < len(row_values):
                        value = row_values[header_cols['since']]
                        if value:  # Only set if value exists
                            returns['Total Returns Since Inception'] = value
                    break
    
    return returns


def extract_statistics_from_table(tables: List[List[List[str]]]) -> Dict[str, str]:
    """
    Extract statistics data from the statistics table (Table 3 format).
    
    Args:
        tables: List of tables
        
    Returns:
        Dictionary with statistics fields
    """
    stats = {}
    
    for table in tables:
        if not table or len(table) < 2:
            continue
        
        # Look for statistics table pattern
        first_row = [normalize_value(cell) for cell in table[0]]
        headers_text = ' '.join(first_row).lower()
        
        if any(keyword in headers_text for keyword in ['statistics', '1 year', '5 years', 'since']):
            # Find header column indices
            header_cols = {}
            for idx, header in enumerate(first_row):
                header_lower = header.lower()
                if ('1 year' in header_lower or '1year' in header_lower) and '5' not in header_lower:
                    header_cols['1year'] = idx
                elif ('5 years' in header_lower or '5year' in header_lower):
                    header_cols['5years'] = idx
                elif 'since' in header_lower and 'inception' in header_lower:
                    header_cols['since'] = idx
            
            # Find Std. Deviation row
            for row in table[1:]:
                row_values = [normalize_value(cell) for cell in row]
                if len(row_values) > 0 and ('std' in row_values[0].lower() and 'deviation' in row_values[0].lower()):
                    if '1year' in header_cols and header_cols['1year'] < len(row_values):
                        stats['Standard Deviation 1 year'] = row_values[header_cols['1year']]
                    if '5years' in header_cols and header_cols['5years'] < len(row_values):
                        stats['Standard Deviation 5 year'] = row_values[header_cols['5years']]
                    if 'since' in header_cols and header_cols['since'] < len(row_values):
                        stats['Standard Deviation Since Inception'] = row_values[header_cols['since']]
                    continue
                
                # Find Beta row
                if len(row_values) > 0 and 'beta' in row_values[0].lower() and 'nifty' in ' '.join(row_values[:3]).lower():
                    if '1year' in header_cols and header_cols['1year'] < len(row_values):
                        stats['Beta (Nifty 50) 1 year'] = row_values[header_cols['1year']]
                    if '5years' in header_cols and header_cols['5years'] < len(row_values):
                        stats['Beta (Nifty 50) 5 years'] = row_values[header_cols['5years']]
                    if 'since' in header_cols and header_cols['since'] < len(row_values):
                        stats['Beta (Nifty 50) Since Inception'] = row_values[header_cols['since']]
    
    return stats


def extract_fundamentals_from_table(tables: List[List[List[str]]]) -> Dict[str, str]:
    """
    Extract P/E, P/B, Dividend Yield from fundamentals table.
    
    Args:
        tables: List of tables
        
    Returns:
        Dictionary with fundamentals fields
    """
    fundamentals = {}
    
    for table in tables:
        if not table or len(table) < 2:
            continue
        
        # Look for P/E, P/B, Dividend Yield in headers
        first_row = [normalize_value(cell) for cell in table[0]]
        if any(keyword in ' '.join(first_row).lower() for keyword in ['p/e', 'p/b', 'dividend yield']):
            headers = [h.lower() for h in first_row]
            # Get values from next row
            if len(table) > 1:
                value_row = [normalize_value(cell) for cell in table[1]]
                for idx, header in enumerate(headers):
                    if idx < len(value_row):
                        value = value_row[idx]
                        if 'p/e' in header or 'pe' in header:
                            fundamentals['P/E'] = value
                        elif 'p/b' in header or 'pb' in header:
                            fundamentals['P/B'] = value
                        elif 'dividend yield' in header or 'div yield' in header:
                            fundamentals['Dividend Yield'] = value
    
    return fundamentals


def find_value_in_text(text: str, search_key: str, pattern: Optional[str] = None) -> Optional[str]:
    """
    Search for a value in text using a search key or regex pattern.
    
    Args:
        text: Text to search in
        search_key: Key to search for
        pattern: Optional regex pattern (if provided, search_key is ignored)
        
    Returns:
        Found value or None
    """
    if pattern:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip() if match.groups() else match.group(0).strip()
    
    # Try to find key: value pattern
    search_key_lower = search_key.lower()
    lines = text.split('\n')
    
    for i, line in enumerate(lines):
        if search_key_lower in line.lower():
            # Try to extract value after colon or equals
            match = re.search(r'[:=]\s*(.+)', line, re.IGNORECASE)
            if match:
                return match.group(1).strip()
            # Try next line
            if i + 1 < len(lines):
                next_line = lines[i + 1].strip()
                if next_line and not next_line.lower().startswith(search_key_lower):
                    return next_line
    
    return None


def parse_factsheet_pdf(pdf_path: Path) -> Dict[str, str]:
    """
    Parse a factsheet PDF and extract all required fields.
    
    Args:
        pdf_path: Path to the PDF file
        
    Returns:
        Dictionary with extracted field values
    """
    # Extract text and tables first to get index name from PDF
    text = extract_text_from_pdf(pdf_path)
    tables = extract_tables_from_pdf(pdf_path)
    
    if not text and not tables:
        print(f"  Warning: Could not extract any content from {pdf_path.name}")
        return {col: "" for col in CSV_COLUMNS}
    
    # Extract index name from PDF text
    index_name = extract_index_name_from_pdf(text, pdf_path.name)
    
    # Initialize result with index name and filename
    result = {col: "" for col in CSV_COLUMNS}
    result["Indices Name"] = index_name
    result["Filename"] = pdf_path.name
    
    # Extract basic info (methodology, constituents, dates, etc.)
    basic_field_mappings = {
        "Methodology": ["methodology", "index methodology"],
        "No. of Constituents": ["constituents", "number of constituents", "no. of constituents"],
        "Launch Date": ["launch date", "launched on"],
        "Base Date": ["base date", "base value date"],
        "Base Value": ["base value", "base index value"],
        "Calculation Frequency": ["calculation frequency", "frequency"],
        "Index Rebalancing": ["rebalancing", "index rebalancing", "rebalancing frequency"],
    }
    
    # Extract basic fields using table/text search
    for field, search_keys in basic_field_mappings.items():
        value = None
        for search_key in search_keys:
            value = find_value_in_tables(tables, search_key)
            if value:
                break
        if not value:
            for search_key in search_keys:
                value = find_value_in_text(text, search_key)
                if value:
                    break
        if value:
            result[field] = value
    
    # Extract returns data using specialized function
    returns_data = extract_returns_from_table(tables)
    result.update(returns_data)
    
    # Extract statistics using specialized function
    stats_data = extract_statistics_from_table(tables)
    result.update(stats_data)
    
    # Extract fundamentals using specialized function
    fundamentals_data = extract_fundamentals_from_table(tables)
    result.update(fundamentals_data)
    
    return result


def load_existing_csv(csv_path: Path) -> pd.DataFrame:
    """
    Load existing CSV file or create new one with headers.
    
    Args:
        csv_path: Path to the CSV file
        
    Returns:
        DataFrame with existing data or empty DataFrame with headers
    """
    if csv_path.exists():
        try:
            # Read CSV, skip rows that are just headers or empty
            df = pd.read_csv(csv_path)
            
            # Remove rows that are duplicates of the header
            # Check if first row is the same as column names
            if len(df) > 0:
                first_row_values = df.iloc[0].values.astype(str)
                col_names = df.columns.values.astype(str)
                if all(fv in col_names or pd.isna(df.iloc[0][idx]) for idx, fv in enumerate(first_row_values)):
                    df = df.iloc[1:].reset_index(drop=True)
            
            # Remove rows where all values in CSV_COLUMNS are NaN/empty
            if len(df) > 0:
                mask = df[CSV_COLUMNS].isna().all(axis=1) | (df[CSV_COLUMNS] == '').all(axis=1)
                df = df[~mask].reset_index(drop=True)
            
            # Ensure all columns exist
            for col in CSV_COLUMNS:
                if col not in df.columns:
                    df[col] = ""
            
            # Reorder columns to match CSV_COLUMNS order
            # Keep any extra columns that might exist (for backwards compatibility)
            all_cols = CSV_COLUMNS + [col for col in df.columns if col not in CSV_COLUMNS]
            df = df[all_cols]
            
            return df
        except Exception as e:
            print(f"Warning: Could not read existing CSV: {e}. Creating new CSV.")
    
    # Create new DataFrame with headers
    df = pd.DataFrame(columns=CSV_COLUMNS)
    return df


def save_to_csv(df: pd.DataFrame, csv_path: Path):
    """
    Save DataFrame to CSV file.
    
    Args:
        df: DataFrame to save
        csv_path: Path to save the CSV file
    """
    # Ensure directory exists
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Save to CSV
    df.to_csv(csv_path, index=False)


def process_factsheets(factsheets_dir: Path, csv_path: Path, index_name: Optional[str] = None):
    """
    Process all factsheet PDFs or a specific one.
    
    Args:
        factsheets_dir: Directory containing PDF factsheets
        csv_path: Path to output CSV file
        index_name: Optional specific index name to process (without .pdf)
    """
    # Load existing CSV
    df = load_existing_csv(csv_path)
    
    # Get list of PDFs to process
    if index_name:
        pdf_files = list(factsheets_dir.glob(f"{index_name}.pdf"))
    else:
        pdf_files = sorted(factsheets_dir.glob("*.pdf"))
    
    if not pdf_files:
        print(f"No PDF files found in {factsheets_dir}")
        return
    
    print(f"Found {len(pdf_files)} PDF file(s) to process.\n")
    
    success_count = 0
    error_count = 0
    skipped_count = 0
    
    for pdf_path in pdf_files:
        print(f"Processing: {pdf_path.name}...")
        
        # Note: We'll check for duplicates after parsing to use the correct index name
        
        try:
            # Parse PDF
            data = parse_factsheet_pdf(pdf_path)
            
            # Check if already exists (using filename to avoid duplicates of same file)
            filename = data.get("Filename", "")
            if not df.empty and filename and "Filename" in df.columns:
                existing = df[df["Filename"] == filename]
                if not existing.empty:
                    print(f"  ⏭ Already exists in CSV (filename: {filename}), skipping...")
                    skipped_count += 1
                    continue
            
            # Add to DataFrame (append mode)
            new_row = pd.DataFrame([data])
            df = pd.concat([df, new_row], ignore_index=True)
            
            print(f"  ✓ Extracted data for {data['Indices Name']}")
            success_count += 1
            
        except Exception as e:
            print(f"  ✗ Error processing {pdf_path.name}: {e}")
            import traceback
            traceback.print_exc()
            error_count += 1
    
    # Save updated CSV
    if success_count > 0:
        save_to_csv(df, csv_path)
        print(f"\n✓ Saved {success_count} record(s) to {csv_path}")
    
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
    CSV_PATH = BASE_DIR / "parsed_data" / "Indices-Table 1.csv"
    
    # Process all factsheets
    process_factsheets(FACTSHEETS_DIR, CSV_PATH)


if __name__ == "__main__":
    main()

