#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

command -v plantuml >/dev/null 2>&1 || { echo "plantuml CLI not found. Please install plantuml."; exit 1; }

# Find all .puml files
# We use a while loop to read files into an array for Bash 3 compatibility
FILES=()
while IFS= read -r -d $'\0'; do
    FILES+=("$REPLY")
done < <(find "$ROOT/diagrams" -name '*.puml' -print0)

if [ ${#FILES[@]} -eq 0 ]; then
  echo "No .puml files found."
  exit 0
fi

# Render SVGs
mkdir -p "$ROOT/diagrams/svg"
plantuml -tsvg -o "$ROOT/diagrams/svg" "${FILES[@]}"
echo "Rendered SVGs to diagrams/svg/"

# Find .puml files for PNG rendering, excluding any in 'png' folders
PNG_FILES=()
while IFS= read -r -d $'\0'; do
    PNG_FILES+=("$REPLY")
done < <(find "$ROOT/diagrams" -name '*.puml' -not -path '*/png/*' -print0)

# Render PNGs
if [ ${#PNG_FILES[@]} -gt 0 ]; then
  mkdir -p "$ROOT/diagrams/png"
  plantuml -tpng -o "$ROOT/diagrams/png" "${PNG_FILES[@]}"
  echo "Rendered PNGs to diagrams/png/"
fi