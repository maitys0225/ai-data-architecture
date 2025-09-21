#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

command -v plantuml >/dev/null 2>&1 || { echo "plantuml CLI not found. Install plantuml."; exit 1; }

mkdir -p "$ROOT/diagrams/svg"
mapfile -t FILES < <(find "$ROOT/diagrams" -name '*.puml' -not -path '*/svg/*' | sort)
[ ${#FILES[@]} -eq 0 ] && { echo "No .puml files found."; exit 0; }

plantuml -tsvg -o "$ROOT/diagrams/svg" "${FILES[@]}"
echo "Rendered SVGs to diagrams/svg/"
