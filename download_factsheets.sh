#!/usr/bin/env bash
set -e

BASE_DIR="$(cd "$(dirname "$0")" && pwd)"

INDICES_FILE="$BASE_DIR/indices.txt"
OUT_DIR="$BASE_DIR/Factsheets"
WORKING_FILE="$BASE_DIR/working.txt"
ERROR_FILE="$BASE_DIR/error.txt"

BASE_URL="https://www.niftyindices.com/Factsheet"

USER_AGENT="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"
REFERER="https://www.niftyindices.com/"

mkdir -p "$OUT_DIR"
# Don't clear existing files, we'll append to them

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

# Generate URL variants based on observed patterns
generate_url_variants() {
  local index_name="$1"
  local variants=()
  
  # Keep full name for patterns that include "Nifty"
  local full_name="${index_name}"
  
  # Remove "Nifty " prefix if present, keeping the rest (for patterns without Nifty)
  local base="${index_name#Nifty }"
  base="${base#Nifty}"
  base="$(echo "$base" | xargs)"
  
  # ===== PATTERNS WITH "Nifty" (Full name) =====
  
  # Pattern 1: Remove all spaces (Factsheet_Nifty500Momentum50.pdf, Factsheet_NiftyIndiaDefence.pdf)
  local full_no_space="${full_name// /}"
  variants+=("Factsheet_${full_no_space}.pdf")
  
  # Pattern 1b: NO underscore after Factsheet (FactsheetNifty500Momentum50.pdf)
  variants+=("Factsheet${full_no_space}.pdf")
  
  # Pattern 2: Underscore before trailing numbers (Factsheet_Nifty_Alpha50.pdf)
  # "Nifty Alpha 50" -> "Nifty Alpha_50" -> "Nifty_Alpha50"
  # Handle underscore before number at end: word space number -> word_number
  local full_before_num="$(echo "$full_name" | sed 's/ \([0-9]\+\)$/_\1/g')"
  # Also handle any number with space before it
  full_before_num="$(echo "$full_before_num" | sed 's/ \([0-9]\+\)/_\1/g')"
  full_before_num="${full_before_num// /}"
  variants+=("Factsheet_${full_before_num}.pdf")
  
  # Pattern 2b: Underscore before number, NO underscore after Factsheet
  variants+=("Factsheet${full_before_num}.pdf")
  
  # Pattern 2c: Underscore between words, number attached directly (Factsheet_Nifty_Alpha50.pdf)
  # "Nifty Alpha 50" -> "Nifty_Alpha50" (underscore between words, number directly attached)
  # Remove space before trailing number using parameter expansion, then replace remaining spaces
  local word_underscore_num="${full_name% [0-9]*}"  # Get part before space+number at end
  local trailing_num="${full_name##* }"  # Get the trailing number
  if [[ "$trailing_num" =~ ^[0-9]+$ ]]; then
    # Valid trailing number, attach directly
    word_underscore_num="${word_underscore_num// /_}"  # Replace spaces with underscores
    word_underscore_num="${word_underscore_num}${trailing_num}"  # Attach number
    variants+=("Factsheet_${word_underscore_num}.pdf")
    variants+=("Factsheet${word_underscore_num}.pdf")
  fi
  
  # Pattern 2c2: Same but with underscore before number at end (Factsheet_Nifty_Alpha_50.pdf)
  local letter_before_num="$(echo "$full_name" | sed 's/\([A-Za-z]\+\) \([0-9]\+\)$/\1_\2/g')"
  letter_before_num="${letter_before_num// /_}"
  variants+=("Factsheet_${letter_before_num}.pdf")
  variants+=("Factsheet${letter_before_num}.pdf")
  
  # Pattern 2d: Alternative - underscore before single digit at end
  local alt_before="$(echo "$full_name" | sed 's/\([A-Za-z]\) \([0-9]\)/\1_\2/g')"
  alt_before="${alt_before// /}"
  variants+=("Factsheet_${alt_before}.pdf")
  variants+=("Factsheet${alt_before}.pdf")
  
  # Pattern 3: Underscore after numbers (Factsheet_Nifty200_Momentum30.pdf, Factsheet_Nifty100_Quality30.pdf)
  # "Nifty 200 Momentum 30" -> "Nifty200_Momentum30"
  # Process: replace "number space" with "number_", but preserve underscores
  local full_after_num="$full_name"
  # Use parameter expansion and sed together: replace patterns like "200 " -> "200_" and "30 " -> "30_"
  # Then replace "word space number" patterns like "Momentum 30" -> "Momentum_30"
  full_after_num="$(echo "$full_after_num" | sed 's/ \([0-9]\+\) /_\1_/g')"  # Replace " 200 " with "_200_"
  full_after_num="$(echo "$full_after_num" | sed 's/ \([0-9]\+\)$/_\1/g')"  # Replace trailing " 30" with "_30"
  full_after_num="$(echo "$full_after_num" | sed 's/^\([0-9]\+\) /\1_/g')"  # Replace leading number space
  full_after_num="${full_after_num// /}"  # Remove remaining spaces
  # Clean up double underscores
  full_after_num="${full_after_num//__/_}"
  variants+=("Factsheet_${full_after_num}.pdf")
  
  # Pattern 3b: Simpler approach - use perl-style regex via sed
  # Match and replace: number followed by space then letter -> number_letter
  local after_num_simple="$(echo "$full_name" | perl -pe 's/(\d+)\s+([A-Za-z])/\1_\2/g')"
  # Match: letter followed by space then number -> letter_number  
  after_num_simple="$(echo "$after_num_simple" | perl -pe 's/([A-Za-z]+)\s+(\d+)/\1_\2/g')"
  after_num_simple="${after_num_simple// /}"  # Remove remaining spaces
  variants+=("Factsheet_${after_num_simple}.pdf")
  variants+=("Factsheet${after_num_alt}.pdf")
  
  # Pattern 4: Underscore before AND after numbers (Factsheet_Nifty100_Quality30.pdf variant)
  local full_both_num="$(echo "$full_name" | sed 's/ \([0-9]\+\) /\1_/g')"
  full_both_num="${full_both_num// /}"
  variants+=("Factsheet_${full_both_num}.pdf")
  
  # Pattern 5: Lowercase "nifty" with underscores (Factsheet_nifty_High_Beta50.pdf)
  local full_lower="$(echo "$full_name" | sed 's/^Nifty/nifty/' | tr ' ' '_')"
  variants+=("Factsheet_${full_lower}.pdf")
  
  # Pattern 6: No Factsheet_ prefix, underscore after numbers (Nifty100_Quality30.pdf)
  variants+=("${full_after_num}.pdf")
  
  # ===== PATTERNS WITHOUT "Nifty" (Base only) =====
  
  # Pattern 7: Base - Remove all spaces
  local no_space="${base// /}"
  variants+=("Factsheet_${no_space}.pdf")
  
  # Pattern 8: Base - Replace all spaces with underscores
  local with_underscore="${base// /_}"
  variants+=("Factsheet_${with_underscore}.pdf")
  
  # Pattern 9: Base - No Factsheet_ prefix, with underscores
  variants+=("${with_underscore}.pdf")
  
  # Pattern 10: Lowercase with underscores (for ind_ pattern: ind_nifty_midcap_150.pdf)
  # Ensure base name is lowercase and all spaces are replaced with underscores
  local base_lower="$(echo "$base" | tr '[:upper:]' '[:lower:]')"
  base_lower="${base_lower// /_}"  # Replace all spaces with underscores
  variants+=("ind_nifty_${base_lower}.pdf")
  
  # Pattern 11: Base - Underscore before numbers
  local before_num="$(echo "$base" | sed 's/ \([0-9]\+\)/_\1/g')"
  before_num="${before_num// /}"
  variants+=("Factsheet_${before_num}.pdf")
  
  # Pattern 12: Base - Underscore after numbers
  local after_num="$(echo "$base" | sed 's/\([0-9]\+\) /\1_/g')"
  after_num="${after_num// /}"
  variants+=("Factsheet_${after_num}.pdf")
  variants+=("${after_num}.pdf")
  
  # Pattern 13: Base - Handle numbers adjacent to words (remove spaces around numbers)
  local compact="$(echo "$base" | sed 's/ \([0-9]\+\)/\1/g' | sed 's/\([0-9]\+\) /\1/g' | tr -d ' ')"
  variants+=("Factsheet_${compact}.pdf")
  
  # Filter out any variants that contain spaces (safety check)
  local filtered_variants=()
  for variant in "${variants[@]}"; do
    # Remove any variant that contains spaces
    if [[ ! "$variant" =~ [[:space:]] ]]; then
      filtered_variants+=("$variant")
    fi
  done
  
  # Print unique variants (no spaces allowed)
  printf '%s\n' "${filtered_variants[@]}" | sort -u
}

while IFS= read -r index || [ -n "$index" ]; do
  index="$(echo "$index" | xargs)"
  [ -z "$index" ] && continue

  echo "Processing: $index"
  found=false

  # Generate all URL variants and try each one
  # Use a temporary file to avoid subshell issues
  variants_file="$(mktemp)"
  generate_url_variants "$index" > "$variants_file"
  
  while IFS= read -r filename && [ "$found" = false ]; do
    url="${BASE_URL}/${filename}"
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
        output_file="$OUT_DIR/${filename}"
        mv "$tmp" "$output_file"
        echo "$index : $url" >> "$WORKING_FILE"
        echo "✓ Found → $url"
        found=true
        # Break immediately when valid PDF is found to move to next index
        break
      else
        # Invalid PDF (likely HTML error page)
        rm -f "$tmp"
      fi
    else
      # Download failed
      rm -f "$tmp"
    fi
  done < "$variants_file"
  
  rm -f "$variants_file"

  if [ "$found" = false ]; then
    echo "$index" >> "$ERROR_FILE"
    echo "✗ No valid PDF found"
  fi

  sleep 0.4
done < "$INDICES_FILE"

echo
echo "=============================="
echo "Completed"
echo "Successfully downloaded: $(wc -l < "$WORKING_FILE" | xargs)"
echo "Failed downloads: $(wc -l < "$ERROR_FILE" | xargs)"
echo "Working → $WORKING_FILE"
echo "Errors  → $ERROR_FILE"