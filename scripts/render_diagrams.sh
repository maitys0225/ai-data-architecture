#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if ! command -v docker &>/dev/null; then
  echo "Docker is required to render diagrams. Install Docker or replace with local PlantUML CLI."
  exit 1
fi

# Render all .puml to SVG into diagrams/svg/ (mirroring relative structure)
mkdir -p "$ROOT/diagrams/svg"
# Find all .puml (excluding svg dir) and render
mapfile -t FILES < <(find "$ROOT/diagrams" -name '*.puml' -not -path '*/svg/*' | sort)

if [ ${#FILES[@]} -eq 0 ]; then
  echo "No .puml files found."
  exit 0
fi

docker run --rm -v "$ROOT":"$ROOT" -w "$ROOT" plantuml/plantuml:latest \
  -tsvg -o ./diagrams/svg "${FILES[@]}"

echo "Rendered SVGs to diagrams/svg/"
