"""
Utility functions for PDF processing, specifically for NSE index factsheets.
"""

import re


def extract_index_name_from_pdf(text: str, filename: str) -> str:
    """
    Extract index name from PDF text or filename as fallback.
    
    Looks for "Index Variant:" pattern first, then falls back to other patterns.
    
    Args:
        text: PDF text content
        filename: PDF filename (e.g., "ind_next50.pdf")
        
    Returns:
        Index name (e.g., "Nifty500 Multicap Momentum Quality 50")
    """
    # First, try to find "Index Variant:" pattern
    # Pattern: "Index Variant: Nifty500 Multicap Momentum Quality 50 Total Returns Index."
    index_variant_patterns = [
        r'Index\s+Variant:\s*([Nn]ifty[^\n]{0,100}?)(?:\s+Total\s+Returns\s+Index|Total\s+Returns|Index)',
        r'Index\s+Variant:\s*([Nn]ifty[^\n]{0,100}?)(?:\.|$)',
    ]
    
    for pattern in index_variant_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            name = match.group(1).strip()
            # Clean up: remove trailing "Total Returns Index", "Index", etc.
            name = re.sub(r'\s+Total\s+Returns\s+Index\.?\s*$', '', name, flags=re.IGNORECASE)
            name = re.sub(r'\s+Total\s+Returns\.?\s*$', '', name, flags=re.IGNORECASE)
            name = re.sub(r'\s+Index\.?\s*$', '', name, flags=re.IGNORECASE)
            name = name.strip()
            if name:
                return name
    
    # Fallback: Try other patterns (existing logic)
    # Order matters - more specific patterns first
    index_patterns = [
        # Pattern: "'[Name]' Index" (with curly quotes) - check first for quoted names
        r'[\u2018\u2019\u201C\u201D"\x27]([Nn]ifty[^\u2018\u2019\u201C\u201D"\x27]{0,60}?)[\u2018\u2019\u201C\u201D"\x27]\s+Index',
        # Pattern: "The [Name] index includes/which/is" - extract name before "index"
        r'The\s+([Nn]ifty[^\s]+(?:\s+[A-Za-z0-9\-]+){0,10})\s+index\s+(?:includes|which|is|aims|represents)',
        # Pattern: "[Name] Index is/which/aims" - for Low-Volatility variants
        r'([Nn]ifty\s+(?:Alpha\s+)?(?:Quality\s+)?(?:Value\s+)?Low-Volatility\s+30)\s+Index\s+(?:is|which|aims)',
        # Pattern: "[Name] index aims" 
        r'([Nn]ifty[^\s]+(?:\s+[A-Za-z0-9\-]+){0,10})\s+index\s+aims',
        # Pattern: "The [Name] Index" (capital I) - more specific patterns first
        r'The\s+([Nn]ifty\s+(?:LargeMidcap|Midcap|Microcap|Smallcap|Alpha|Healthcare|High\s+Beta|Low\s+Volatility|Quality|50\s+Arbitrage)[^\n]{0,50}?)(?:\s+Index|\s+Total\s+Returns|\s+reflects)',
        r'The\s+([Nn]ifty[^\n]{0,80}?)(?:\s+Index|\s+Total\s+Returns|\s+reflects)',
        r'([Nn]ifty\s+[A-Za-z0-9\s\-]{0,50}?)\s+Index',
        r'([Nn]ifty\s+Next\s+50)',
        r'([Nn]ifty\s+50)',
    ]
    
    for pattern in index_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            name = match.group(1).strip()
            # Clean up common suffixes
            name = re.sub(r'\s+Index\s*$', '', name, flags=re.IGNORECASE)
            # Avoid matching incorrect phrases like "Nifty 100 and the Nifty Midcap 150"
            if name and 'and the' not in name.lower() and len(name) > 5:
                return name
    
    # Fallback: extract from filename
    name = filename.replace(".pdf", "")
    # Handle common patterns
    name = re.sub(r'^ind_', 'Nifty ', name, flags=re.IGNORECASE)
    name = re.sub(r'^factsheet_', '', name, flags=re.IGNORECASE)
    name = re.sub(r'_', ' ', name)
    # Add space before numbers
    name = re.sub(r'(\d+)', r' \1', name)
    # Clean up multiple spaces
    name = re.sub(r'\s+', ' ', name).strip()
    return name

