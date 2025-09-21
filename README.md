# ai-data-architecture

Patterns, decision records, and reference designs for a well-architected data platform.

## Goals
- **Single source** for architecture patterns, RFCs/ADRs, and system designs.
- **Diagrams-as-code**: all diagrams in PlantUML (C4 model: C1–C4), auto-rendered to SVG.
- **Repeatable templates**: consistent Markdown docs, reviewable via PRs.

## What’s inside
- `patterns/` — reusable patterns (ingestion, governance, quality, lineage, orchestration, MLOps).
- `design-docs/` — system/feature designs (proposal → review → accepted).
- `adrs/` — Architecture Decision Records (lightweight).
- `diagrams/` — PlantUML sources + generated SVGs (C1–C4).
- `templates/` — templates for ADRs, design docs, patterns.
- `docs/` — optional static docs site (MkDocs + Kroki) for pretty browsing.

## Quick start
1. **Install tooling**
   - Java or Docker (for PlantUML CLI), Markdown linter (optional).
   - VS Code extensions (recommended): PlantUML, Markdown All in One, markdownlint.
2. **Render diagrams locally**
   ```bash
   ./scripts/render_diagrams.sh
   ```
   SVGs appear under `diagrams/svg/`.
3. **Create a design**
   - Copy `templates/arch-doc.md` → `design-docs/<topic>/README.md`
   - Add diagrams under `diagrams/c4/<topic>/` as `.puml` (C1–C4)
   - Reference rendered SVGs in your Markdown.
4. **Propose a change**
   - Create a branch `feat/<topic>`; open a PR using the provided template.

## Viewing diagrams
- **GitHub**: PRs and README reference the **generated SVGs**.
- **VS Code**: preview `.puml` files with the PlantUML extension.
- **Docs site (optional)**: `mkdocs serve` to browse diagrams rendered via Kroki.

## C4 Modeling
All systems should include at least:
- **C1**: System Landscape
- **C2**: Container diagram
- **C3**: Component diagram
- **C4**: Code-level (selected hotspots only)

## Well-Architected pillars (data platform)
- Security & Governance
- Reliability
- Cost Efficiency
- Performance
- Operational Excellence
- Sustainability

## License
MIT (adjust as needed).
