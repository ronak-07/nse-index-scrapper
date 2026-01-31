#!/usr/bin/env bash
set -e

BASE_DIR="$(cd "$(dirname "$0")" && pwd)"

URLS_FILE="${1:-$BASE_DIR/google_found_urls.txt}"
OUT_DIR="$BASE_DIR/Factsheets"
WORKING_FILE="$BASE_DIR/working.txt"
ERROR_FILE="$BASE_DIR/error.txt"

USER_AGENT="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"
REFERER="https://www.niftyindices.com/"

mkdir -p "$OUT_DIR"

# Check if file is a valid PDF (not HTML error page)
is_valid_pdf() {
  local file="$1"
  # Check file size
  [ "$(stat -f%z "$file" 2>/dev/null || echo 0)" -gt 5000 ] || return 1
  # Check if it's actually a PDF (starts with %PDF)
  [ "$(head -c 4 "$file" 2>/dev/null)" = "%PDF" ] || return 1
  # Make sure it's not HTML (404 error page)
  if head -c 100 "$file" 2>/dev/null | grep -qi "<!DOCTYPE html\|<html\|Error 404\|page not found"; then
    return 1
  fi
  # Additional check: file command should say PDF
  file "$file" 2>/dev/null | grep -qi "PDF" || return 1
  return 0
}

if [ ! -f "$URLS_FILE" ]; then
  echo "Error: URLs file '$URLS_FILE' not found."
  exit 1
fi

echo "Reading URLs from: $URLS_FILE"
echo ""

success_count=0
error_count=0

while IFS= read -r line || [ -n "$line" ]; do
  # Skip empty lines
  [ -z "$line" ] && continue
  
  # Split on " : " (space-colon-space) pattern to handle colons in index names
  # Extract index name (everything before " : http") and URL (everything after " : ")
  if [[ "$line" =~ ^(.+)[[:space:]]+:[[:space:]]+(https?://.+)$ ]]; then
    index_name="${BASH_REMATCH[1]}"
    url="${BASH_REMATCH[2]}"
  else
    # Fallback: try splitting on last " : "
    index_name="${line% : *}"
    url="${line##* : }"
  fi
  
  # Clean up the index name and URL (remove extra spaces)
  index_name="$(echo "$index_name" | xargs)"
  url="$(echo "$url" | xargs)"
  
  [ -z "$index_name" ] || [ -z "$url" ] && continue
  
  # Normalize URL - ensure www. prefix if missing
  if [[ "$url" =~ ^https?://niftyindices\.com ]] && [[ ! "$url" =~ ^https?://www\.niftyindices\.com ]]; then
    url="${url/niftyindices.com/www.niftyindices.com}"
  fi
  
  echo "Processing: $index_name"
  
  # Extract filename from URL
  filename="$(basename "$url")"
  output_file="$OUT_DIR/${filename}"
  
  # Skip if file already exists and is valid
  if [ -f "$output_file" ]; then
    if is_valid_pdf "$output_file"; then
      echo "  ⏭ Already exists: $filename"
      echo "$index_name : $url" >> "$WORKING_FILE"
      ((success_count++)) || true
      continue
    else
      # Remove invalid file
      rm -f "$output_file"
    fi
  fi
  
  tmp="$(mktemp)"
  
  # Try to download
  if curl -fsL \
    -A "$USER_AGENT" \
    -H "Accept: application/pdf" \
    -e "$REFERER" \
    --connect-timeout 10 \
    --max-time 30 \
    "$url" -o "$tmp" 2>/dev/null
  then
    # Check if it's a valid PDF
    if is_valid_pdf "$tmp"; then
      mv "$tmp" "$output_file"
      echo "$index_name : $url" >> "$WORKING_FILE"
      echo "  ✓ Downloaded: $filename"
      ((success_count++)) || true
    else
      # Invalid PDF (likely HTML error page)
      rm -f "$tmp"
      echo "$index_name" >> "$ERROR_FILE"
      echo "  ✗ Invalid PDF"
      ((error_count++)) || true
    fi
  else
    # Download failed
    rm -f "$tmp"
    echo "$index_name" >> "$ERROR_FILE"
    echo "  ✗ Download failed"
    ((error_count++)) || true
  fi
  
  sleep 0.4
done < "$URLS_FILE"

echo
echo "=============================="
echo "Download complete!"
echo "  Successfully downloaded: $success_count"
echo "  Failed downloads: $error_count"
echo "Working → $WORKING_FILE"
echo "Errors  → $ERROR_FILE"

