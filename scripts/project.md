# Layout

 **domain-first** layout with clear ownership, consistent templates, and zero “random folders.” Here’s a **scalable, collaboration-friendly** structure you can adopt right away.

# Design principles

* **Domain-first**: organize by business/data domains → products → projects.
* **Single source of truth**: patterns live in `/library`; domain docs live in `/domains`; pods/workstreams are **time-boxed** and reference domains, not the other way around.
* **Consistent metadata**: every Markdown doc has front matter; every folder has a `README.md` index.
* **Diagrams as code**: all C4 diagrams are PlantUML (`.puml`), rendered to SVG.
* **Clear ownership**: `CODEOWNERS` governs reviews per domain/product.

---

# Top-level layout (monorepo for architecture)

```
ai-data-architecture/
├─ README.md
├─ CONTRIBUTING.md
├─ CODE_OF_CONDUCT.md
├─ CODEOWNERS
├─ .github/
│  ├─ ISSUE_TEMPLATE/
│  │  ├─ 01-architecture-proposal.md
│  │  ├─ 02-bug-doc.md
│  │  └─ config.yml
│  ├─ pull_request_template.md
│  └─ workflows/
│     └─ diagrams.yml
├─ governance/
│  ├─ repo-conventions.md
│  ├─ decision-process.md          # RFC/ADR workflow
│  ├─ review-checklists.md         # C4, data, security, cost checklists
│  └─ taxonomy.md                  # domains/products naming rules
├─ library/                        # shared, reusable assets
│  ├─ patterns/                    # cross-domain patterns
│  │  ├─ ingestion/
│  │  ├─ governance/
│  │  ├─ quality/
│  │  ├─ lineage/
│  │  ├─ serving/
│  │  └─ mlops/
│  ├─ adrs/                        # global ADRs
│  ├─ diagrams/
│  │  ├─ includes/                 # shared PUML includes + themes
│  │  │  ├─ c4_includes.puml
│  │  │  └─ theme.puml
│  │  └─ svg/                      # generated artifacts (CI fills)
│  └─ templates/
│     ├─ arch-doc.md
│     ├─ adr.md
│     ├─ pattern.md
│     └─ folder-readme.md
├─ domains/                        # primary home for architecture
│  ├─ <domain-name>/               # e.g., customer, billing, marketing
│  │  ├─ README.md                 # index, scope, owners, glossary
│  │  ├─ products/                 # domain products/capabilities
│  │  │  ├─ <product-name>/
│  │  │  │  ├─ README.md
│  │  │  │  ├─ adrs/
│  │  │  │  ├─ design-docs/
│  │  │  │  │  ├─ <project-or-feature>/
│  │  │  │  │  │  ├─ README.md     # arch-doc.md template
│  │  │  │  │  │  └─ index.md      # optional landing page
│  │  │  │  └─ diagrams/
│  │  │  │     ├─ c4/
│  │  │  │     │  └─ <project-or-feature>/
│  │  │  │     │     ├─ C1-SystemLandscape.puml
│  │  │  │     │     ├─ C2-Container.puml
│  │  │  │     │     ├─ C3-Component.puml
│  │  │  │     │     └─ C4-Code.puml
│  │  │  │     └─ svg/              # CI-generated
│  │  └─ adrs/                      # domain-level ADRs
│  └─ ...
├─ workstreams/                    # time-boxed coordination space
│  ├─ <ws-yyyymm-<short-name>>/    # e.g., ws-202509-feature-store-hardening
│  │  ├─ README.md                 # scope, timeline, leads
│  │  ├─ plan.md                   # milestones, risks
│  │  └─ links.md                  # links to /domains and /library docs
├─ pods/                           # team-centric notes, ephemeral
│  ├─ <pod-name>/                  # e.g., pod-orchestration
│  │  ├─ README.md                 # roster, ceremonies, backlog links
│  │  └─ handover.md               # when pod dissolves, point to domains/*
├─ teams/                          # onboarding & ops docs per team
│  ├─ platform/
│  ├─ data-eng/
│  └─ ml-platform/
├─ docs/                           # optional MkDocs site
│  └─ index.md
├─ scripts/
│  └─ render_diagrams.sh
└─ tools/                          # optional helpers (linters, linkcheck)
   └─ linkcheck.config.json
```

### Why this scales

* **Domains** are stable and grow linearly; **workstreams/pods** are ephemeral and point to the canonical domain docs.
* **Patterns** stay centralized in `/library/patterns`, preventing duplication.
* **Ownership** and review pathways mirror the folder layout (backed by `CODEOWNERS`).

---

# Placement rules (“what goes where?”)

* **Architecture for a business capability** → `domains/<domain>/products/<product>/…`
* **Reusable pattern or standard** → `library/patterns/…`
* **A short-term initiative** spanning multiple domains → `workstreams/<ws-yyyymm-…>`, linking back to domain docs.
* **Team onboarding/process** → `teams/<team>/…`
* **Decisions**:

  * If **global** (affects many domains): `library/adrs/`
  * If **domain**-specific: `domains/<domain>/adrs/`
  * If **product**-specific: `domains/<domain>/products/<product>/adrs/`

---

# Naming conventions

* **Folders/files**: `kebab-case`
* **Workstreams**: `ws-YYYYMM-<short-name>`
* **Docs**: `README.md` in every folder; additional pages as `<topic>.md`
* **C4 diagrams**:
  `C1-SystemLandscape.puml`, `C2-Container.puml`, `C3-Component.puml`, `C4-Code.puml`
* **Projects/features**: nest under `design-docs/<project-or-feature>/`

---

# Required metadata (front matter for every `.md`)

```yaml
---
title: "<clear title>"
status: "draft|proposed|accepted|rejected|deprecated"
owners: ["@team-handle", "@maintainer"]
authors: ["Name <email>"]
domain: "<domain-name>"          # for domain/product docs
product: "<product-name>"        # if applicable
created: "YYYY-MM-DD"
last_updated: "YYYY-MM-DD"
tags: ["ingestion","governance","mlops"]
related_adrs: ["ADR-0007-feature-store-read-paths"]
---
```

---

# C4 + PlantUML rules (recap)

* All diagrams are `.puml` and live beside their doc under the product:

  * `domains/<domain>/products/<product>/diagrams/c4/<project>/C1…C4.puml`
* `library/diagrams/includes/` holds shared `c4_includes.puml` and `theme.puml`
* CI renders `.puml → .svg` into the sibling `svg/` folder; Markdown links use SVGs.

---

# CODEOWNERS (example)

```txt
# Global library reviewed by platform architects
/library/*            @platform-architecture

# Domains own their subtrees
/domains/customer/*   @data-eng-customer
/domains/billing/*    @data-eng-billing
/domains/marketing/*  @growth-data

# Workstreams require cross-team review
/workstreams/*        @program-managers @platform-architecture
```

---

# Folder README templates

## `library/patterns/<area>/README.md`

* Purpose & scope of the pattern area
* Index of included patterns with one-line intents
* Compatibility notes / dependencies
* Owners & how to request a change

## `domains/<domain>/README.md`

* Domain scope & glossary
* Products and links
* Data boundaries & contracts
* Owners & SLAs for review

## `domains/<domain>/products/<product>/README.md`

* Product vision and context
* Index of design docs
* Link to ADRs and diagrams
* Contact/owners

---

# Issue & PR hygiene for scale

* **Issue templates**:

  * Architecture proposal (captures context, alternatives, risks)
  * Doc bug/typo
* **PR template**:

  * Checklists: C4 coverage, data governance, security, cost
  * “Which domain/product?” and “Which ADR(s)?” fields
* **Labels**:

  * `domain:customer`, `product:feature-store`, `type:pattern`, `status:proposal`, `needs:security-review`

---

# Lifecycle: archive & deprecate

* When a project merges or is replaced, update `status` in front matter and add a banner at the top.
* Move orphaned or historical docs to `archive/` **only** if they’re confusing in place; otherwise keep them where they were with `status: deprecated`.

---

# Example: adding a new cross-domain ingestion pattern

```
library/patterns/ingestion/batch-to-lake/
├─ README.md               # from templates/pattern.md
├─ adrs/
│  └─ ADR-0012-input-contracts.md
└─ diagrams/
   ├─ c4/batch-to-lake/
   │  ├─ C1-SystemLandscape.puml
   │  ├─ C2-Container.puml
   │  ├─ C3-Component.puml
   │  └─ C4-Code.puml
   └─ svg/                 # CI will populate
```

# Example: domain product feature doc (feature store hardening)

```
domains/customer/products/feature-store/
├─ README.md
├─ adrs/ADR-0018-read-consistency.md
├─ design-docs/latency-hardening/
│  ├─ README.md            # from templates/arch-doc.md
│  └─ index.md             # optional
└─ diagrams/
   ├─ c4/latency-hardening/
   │  ├─ C1-SystemLandscape.puml
   │  ├─ C2-Container.puml
   │  ├─ C3-Component.puml
   │  └─ C4-Code.puml
   └─ svg/
```

---

# Governance & review lanes (short)

* **Patterns**: reviewed by platform architects + at least one domain owner.
* **Domain/product docs**: reviewed by that domain’s owners (from `CODEOWNERS`).
* **Cross-domain workstreams**: must tag all impacted domain owners.

---

If you want, I can **generate this exact scaffold** (with README stubs, CODEOWNERS, and templates) as a ZIP—just say the initial domain/product names and team handles you want wired in.
