# Contributing

## Branching & commits
- Branch names: `feat/<topic>`, `fix/<topic>`, `docs/<topic>`.
- Conventional Commits examples:
  - `feat: add streaming ingestion pattern`
  - `docs: C2 diagram for feature store`
  - `chore: update PlantUML theme`

## PR checklist
- [ ] Docs use provided templates.
- [ ] Diagrams include `.puml` **and** generated `.svg`.
- [ ] Markdown links reference `diagrams/svg/...` (not `.puml`).
- [ ] `./scripts/render_diagrams.sh` run locally—no missing SVGs.
- [ ] Decisions recorded/updated in `adrs/` and linked from docs.

## Reviews
- Min 1 reviewer with domain context.
- Architectural decisions must reference an ADR.

## Linting
- Markdown: `markdownlint` with rules in `.markdownlint.json`.
- CI fails if SVGs are out-of-date.

## Git conventions
- Keep PRs focused.
- Squash-merge with a clean summary.
