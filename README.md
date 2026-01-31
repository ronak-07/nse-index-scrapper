# NSE Index Factsheet Scraper & Parser

A Python-based tool to download and parse NSE (National Stock Exchange) index factsheets from [niftyindices.com](https://www.niftyindices.com). Automatically extracts index metadata, financial metrics, and sector representations from PDF factsheets into structured CSV files for analysis.

## Features

- 🔍 **Automated URL Discovery**: Uses Google/DuckDuckGo search to find factsheet PDF URLs
- 📥 **PDF Download**: Downloads factsheets with robust validation and error handling
- 📊 **Data Extraction**: Extracts comprehensive index data including:
  - Index metadata (methodology, constituents, launch date, base date)
  - Financial metrics (returns, standard deviation, beta, P/E, P/B, dividend yield)
  - Sector representation breakdown
- 🔧 **Robust Parsing**: Handles various PDF formats and index name patterns
- 📁 **CSV Export**: Exports data to structured CSV files for easy analysis
- ✅ **Error Handling**: Validates PDFs, handles corrupted files, and logs errors

## Project Structure

```
nse_scrapper/
├── parse_factsheets.py          # Main parser for index data extraction
├── parse_sectors.py              # Parser for sector representation data
├── pdf_utils.py                  # Common utilities for PDF processing
├── google_search_factsheets.py  # Google search for factsheet URLs
├── download_from_urls.sh         # Bash script to download PDFs from URLs
├── download_factsheets.sh         # Bash script with URL variant generation
├── find_corrupt_pdf.py           # Utility to identify and move corrupted PDFs
├── indices.txt                   # Input file with index names
├── requirements.txt              # Python dependencies
├── master/                       # Output directory for CSV files
│   ├── Indices-Table 1.csv      # Extracted index data
│   └── Sector-Table 1.csv       # Sector representation data
└── Factsheets/                   # Directory for downloaded PDFs (excluded from git)
```

## Installation

### Prerequisites

- Python 3.7 or higher
- Bash shell (for download scripts)
- `curl` command-line tool

### Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/YOUR_USERNAME/nse-scrapper.git
   cd nse-scrapper
   ```

2. **Install Python dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Optional: Install search libraries** (for better URL discovery):
   ```bash
   pip install duckduckgo-search
   # OR
   pip install googlesearch-python
   ```

## Usage

### Workflow Overview

The typical workflow consists of three main steps:

1. **Search for factsheet URLs**
2. **Download PDF files**
3. **Parse and extract data**

### Step 1: Search for Factsheet URLs

Search Google/DuckDuckGo for factsheet URLs for indices listed in `indices.txt`:

```bash
python3 google_search_factsheets.py
```

This will:
- Read index names from `indices.txt`
- Search for each index's factsheet URL
- Save found URLs to `google_found_urls.txt` in the format: `Index Name : URL`

**Input**: `indices.txt` (one index name per line)
**Output**: `google_found_urls.txt`

### Step 2: Download PDFs

Download factsheets using the URLs found in step 1:

```bash
bash download_from_urls.sh google_found_urls.txt
```

Alternatively, use the variant-based downloader that tries multiple URL patterns:

```bash
bash download_factsheets.sh
```

This will:
- Download PDFs to the `Factsheets/` directory
- Validate PDFs (checks for valid PDF headers, not HTML error pages)
- Log successful downloads to `working.txt`
- Log failed downloads to `error.txt`

**Input**: `google_found_urls.txt` or `indices.txt`
**Output**: PDF files in `Factsheets/` directory

### Step 3: Parse and Extract Data

#### Extract Index Data

Parse all PDFs in the `Factsheets/` directory and extract index information:

```bash
python3 parse_factsheets.py
```

This extracts:
- Index name
- Methodology
- Number of constituents
- Launch date, base date, base value
- Calculation frequency and rebalancing schedule
- Price returns (QTD, YTD, 1 year, 5 years, since inception)
- Total returns (QTD, YTD, 1 year, 5 years, since inception)
- Standard deviation (1 year, 5 years, since inception)
- Beta vs Nifty 50 (1 year, 5 years, since inception)
- P/E, P/B, Dividend Yield

**Output**: `master/Indices-Table 1.csv`

#### Extract Sector Representation

Extract sector breakdown data from factsheets:

```bash
python3 parse_sectors.py
```

This creates a matrix with:
- Rows: Index names
- Columns: Sector names
- Values: Sector weight percentages

**Output**: `master/Sector-Table 1.csv`

### Utility Scripts

#### Find and Move Corrupted PDFs

Identify corrupted PDFs and move them to a separate directory:

```bash
python3 find_corrupt_pdf.py Factsheets Factsheets-Final corrupt
```

**Options**:
- `--dry-run`: Preview changes without moving files
- Arguments: `source_dir` `valid_dir` `corrupt_dir`

## Input Format

### `indices.txt`

One index name per line. Examples:

```
Nifty 500 Momentum 50
Nifty 200 Alpha 30
Nifty 500 Multicap 50:25:25
```

## Output Format

### `master/Indices-Table 1.csv`

Contains one row per index with the following columns:
- `Indices Name`: Name of the index
- `Filename`: Source PDF filename
- `Methodology`: Index calculation methodology
- `No. of Constituents`: Number of stocks in the index
- `Launch Date`: Index launch date
- `Base Date`: Base date for index calculation
- `Base Value`: Base index value
- `Calculation Frequency`: Real-time or end-of-day
- `Index Rebalancing`: Rebalancing frequency
- `Price Returns QTD/YTD/1 year/5 years/Since Inception`
- `Total Returns QTD/YTD/1 year/5 years/Since Inception`
- `Standard Deviation 1 year/5 year/Since Inception`
- `Beta (Nifty 50) 1 year/5 years/Since Inception`
- `P/E`, `P/B`, `Dividend Yield`

### `master/Sector-Table 1.csv`

Contains sector representation data:
- `Indices`: Index name (rows)
- `Filename`: Source PDF filename
- Sector columns: One column per sector with weight percentages

## How It Works

### Index Name Extraction

The parser uses multiple strategies to extract index names from PDFs:

1. **Primary**: Looks for "Index Variant:" pattern in PDF text
2. **Fallback patterns**:
   - Quoted names: `'Nifty200 Momentum 30' Index`
   - Descriptive patterns: `The Nifty100 Quality 30 index includes...`
   - Low-Volatility variants: `Nifty Alpha Low-Volatility 30 Index is...`
   - Filename-based extraction as final fallback

### PDF Validation

The download scripts validate PDFs by:
- Checking file size (> 5KB)
- Verifying PDF header (`%PDF`)
- Detecting HTML error pages (404 pages)
- Using `file` command validation

### Error Handling

- Invalid PDFs are automatically rejected
- Failed downloads are logged to `error.txt`
- Successful downloads are logged to `working.txt`
- Corrupted PDFs can be identified and moved using `find_corrupt_pdf.py`

## Dependencies

- `pdfplumber`: PDF text and table extraction
- `pandas`: CSV data manipulation
- `beautifulsoup4`: HTML parsing for search results
- `requests`: HTTP requests for search
- `duckduckgo-search` or `googlesearch-python`: Optional, for better search results

## Limitations

- Some sector-specific indices (Auto, Bank, IT, FMCG, etc.) don't have sector representation tables
- PDF formats may vary, requiring pattern updates for new formats
- Google search rate limiting may require delays between searches
- Some indices may have duplicate PDFs with different filenames

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

[Add your license here]

## Acknowledgments

- Data source: [NSE Indices](https://www.niftyindices.com)
- PDF parsing: [pdfplumber](https://github.com/jsvine/pdfplumber)
