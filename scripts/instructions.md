# Instructions

Open `bash` terminal then execute

```bash

chmod +x scripts/render_diagrams.sh
./scripts/render_diagrams.sh
git add diagrams/svg
git commit -m "chore(diagrams): render initial SVGs"

```

No worries — that message just means Docker isn’t on your machine (the render script prefers Docker). You’ve got **three** good options:

---

# Option A — Install Docker (recommended, zero config)

## macOS

```bash
# Install Docker Desktop
brew install --cask docker
# then launch Docker.app once so the daemon starts
```

## Windows 10/11

1. Install **Docker Desktop** (WSL2 backend).
2. Ensure **“Use the WSL 2 based engine”** is enabled in Docker Desktop → Settings → General.

## Linux (Ubuntu/Debian)

```bash
sudo apt-get update
sudo apt-get install -y docker.io
sudo usermod -aG docker $USER
# log out/in or run: newgrp docker
```

Then try:

```bash
docker run --rm hello-world
./scripts/render_diagrams.sh
git add diagrams/svg
git commit -m "chore(diagrams): render svg"
```

---

# Option B — Local PlantUML CLI (no Docker)

Install **PlantUML** + **Graphviz**, then use a Docker-free render script.

## macOS

```bash
brew install plantuml graphviz
```

## Windows (PowerShell, with Chocolatey)

```powershell
choco install plantuml graphviz
```

## Linux (Ubuntu/Debian)

```bash
sudo apt-get update
sudo apt-get install -y plantuml graphviz
```

### Swap the render script

Replace `scripts/render_diagrams.sh` with this Docker-free version:

```bash
#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

command -v plantuml >/dev/null 2>&1 || { echo "plantuml CLI not found. Install plantuml."; exit 1; }

mkdir -p "$ROOT/diagrams/svg"
mapfile -t FILES < <(find "$ROOT/diagrams" -name '*.puml' -not -path '*/svg/*' | sort)
[ ${#FILES[@]} -eq 0 ] && { echo "No .puml files found."; exit 0; }

plantuml -tsvg -o ./diagrams/svg "${FILES[@]}"
echo "Rendered SVGs to diagrams/svg/"
```

Then run:

```bash
chmod +x scripts/render_diagrams.sh
./scripts/render_diagrams.sh
```

---

# Option C — Let CI render for you (no local setup)

You can **skip local rendering** entirely:

```bash
git add .
git commit -m "feat: add diagrams"
git push
```

* GitHub Actions will render `.puml` → `.svg` and commit the SVGs back to your branch.
* You’ll see the **Render Diagrams** job in the **Actions** tab.

---

## Handy fallback: export from VS Code

If you only need a one-off export:

1. Open a `.puml` file in VS Code
2. `Ctrl/Cmd+Shift+P` → **PlantUML: Export Current Diagram** → choose **SVG**
3. Save into `diagrams/svg/<topic>/` with the same filename (e.g., `C2-Container.svg`)
4. Commit the SVGs.

---

### Quick sanity checks

* `docker run --rm hello-world` works → Docker is healthy.
* `plantuml -version` and `dot -V` (Graphviz) both show versions → Local CLI is ready.
* SVGs appear under `diagrams/svg/...` and are referenced from your Markdown.

If you tell me your OS, I’ll tailor the exact steps (and fix any path/permission hiccups like WSL2 group membership on Windows).


Perfect, Sidd — I built you a plug-and-play starter repo and a guided setup.

[Download the starter repo (ZIP)](sandbox:/mnt/data/ai-data-architecture-starter.zip)

# Step-by-step: set up from VS Code and push to a remote

## 0) Prereqs

* Install: **Git**, **VS Code**, **Docker Desktop** (for PlantUML rendering).
* VS Code extensions: PlantUML, Markdown All in One, markdownlint (the repo recommends them).

## 1) Create the local repo from the starter

1. Unzip `ai-data-architecture-starter.zip`.
2. Open VS Code → **File → Open Folder…** → select the unzipped `ai-data-architecture` folder.

## 2) Initialize Git & make the first commit

In VS Code Terminal (``Ctrl+` ``):

```bash
git init
git add .
git commit -m "feat: bootstrap ai-data-architecture repo scaffold"
```

## 3) Render diagrams locally (optional, good smoke test)

```bash
chmod +x scripts/render_diagrams.sh
./scripts/render_diagrams.sh
git add diagrams/svg
git commit -m "chore(diagrams): render initial SVGs"
```

## 4) Create a remote repo (GitHub) directly from VS Code (easiest)

* In the **Source Control** panel, click **Publish to GitHub** (or **Publish Branch**).

  * Choose **Public** or **Private**.
  * VS Code will create the GitHub repo for you and set the `origin` remote.
* That’s it—your initial commit(s) are pushed and the GitHub Actions workflow will run.

### …or do it manually via CLI (if you prefer)

1. Create an empty repo on GitHub named `ai-data-architecture`.
2. Back in VS Code Terminal:

   ```bash
   git branch -M main
   git remote add origin https://github.com/<your-username>/ai-data-architecture.git
   git push -u origin main
   ```

## 5) Verify CI (GitHub Actions)

* Open your new GitHub repo → **Actions** tab.
* You’ll see **Render Diagrams** running on your push/PR.
  It renders `.puml` → `.svg` and commits any new SVGs so they show up in READMEs/PRs.

## 6) Create your first architecture doc

1. Copy the template:

   ```bash
   mkdir -p design-docs/feature-store
   cp templates/arch-doc.md design-docs/feature-store/README.md
   mkdir -p diagrams/c4/feature-store
   # sample C1–C4 already included in the starter under diagrams/c4/feature-store
   ```
2. Update `design-docs/feature-store/README.md` front matter and content.
3. Render diagrams and commit:

   ```bash
   ./scripts/render_diagrams.sh
   git add .
   git commit -m "feat: add feature store architecture (C1–C4) and doc"
   git push
   ```

# What’s already included in the starter

* README, CONTRIBUTING, Code of Conduct, editor/lint configs
* **Templates**: `templates/arch-doc.md`, `templates/adr.md`, `templates/pattern.md`
* **C4 PUML includes** + theme under `diagrams/includes/`
* **Sample topic**: `diagrams/c4/feature-store` with C1–C4 PUML
* **Render script**: `scripts/render_diagrams.sh` (Dockerized PlantUML → SVG)
* **CI**: `.github/workflows/diagrams.yml` (renders SVGs on push/PR and commits if changed)
* VS Code extension recommendations in `.vscode/extensions.json`

# Team workflow (quick refresher)

* Branches: `feat/<topic>`, `fix/<topic>`, `docs/<topic>`
* All docs in **Markdown**; all diagrams in **PlantUML** using **C1–C4**.
* Commit both `.puml` and the rendered `.svg`, and link SVGs from docs.
* Use ADRs for decisions; reference them from design docs.
* Open PRs; CI ensures diagrams are up-to-date.

Want me to pre-generate another example (e.g., ingestion pipeline C1–C4) in this repo too?

