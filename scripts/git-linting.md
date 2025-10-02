Awesome—here's a practical, configurable **Git linting** setup you can drop into any repo to enforce folder structure and naming rules. It lints only staged files by default (so it works great as a pre-commit hook), but you can also run it against the whole repo.

---

# 1) `git-lint.py` (Python, no deps beyond PyYAML if you use YAML)

```python
#!/usr/bin/env python3
"""
git-lint.py — Lint folder structure & names based on a config file.

* Lints STAGED files by default (so it's ideal for pre-commit).
* Use `--all` to lint the whole repo.
* Config file: .gitlint.yml or .gitlint.json at repo root (YAML preferred).
* Exits non-zero on violations.

Rules supported (see sample config below):
- allowed_root_dirs: restrict top-level folders
- required_files: files that must exist
- forbidden_paths_glob: block specific globs
- allowed_extensions, blocked_extensions
- file_name_patterns: regex per glob or extension
- dir_name_pattern: regex for all directory names
- max_depth, max_filename_length, max_path_length
- enforce_case: snake | kebab | camel | pascal
- ignore_globs: paths to skip

Author: you ☺
"""
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Any, Tuple

try:
    import yaml  # type: ignore
    YAML_AVAILABLE = True
except Exception:
    YAML_AVAILABLE = False

REPO_ROOT = Path(__file__).resolve().parent

CASE_FUNCS = {
    "snake": lambda s: re.fullmatch(r"[a-z0-9]+(?:_[a-z0-9]+)*", s) is not None,
    "kebab": lambda s: re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", s) is not None,
    "camel": lambda s: re.fullmatch(r"[a-z][A-Za-z0-9]*", s) is not None,   # lowerCamel
    "pascal": lambda s: re.fullmatch(r"[A-Z][A-Za-z0-9]*", s) is not None,
}

def load_config() -> Dict[str, Any]:
    candidates = [REPO_ROOT / ".gitlint.yml", REPO_ROOT / ".gitlint.yaml", REPO_ROOT / ".gitlint.json"]
    for p in candidates:
        if p.exists():
            if p.suffix in (".yml", ".yaml"):
                if not YAML_AVAILABLE:
                    print("ERROR: PyYAML not installed but .gitlint.yml detected. Install with: pip install pyyaml", file=sys.stderr)
                    sys.exit(2)
                return yaml.safe_load(p.read_text()) or {}
            else:
                return json.loads(p.read_text() or "{}")
    # default empty config
    return {}

def get_staged_files() -> List[str]:
    result = subprocess.run(["git", "diff", "--name-only", "--cached"], capture_output=True, text=True)
    if result.returncode != 0:
        print(result.stderr, file=sys.stderr)
        sys.exit(result.returncode)
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]

def get_all_repo_files() -> List[str]:
    # Exclude .git directory
    files = []
    for p in REPO_ROOT.rglob("*"):
        if ".git" in p.parts:
            continue
        if p.is_file():
            files.append(str(p.relative_to(REPO_ROOT)))
    return files

def path_depth(path_str: str) -> int:
    return len(Path(path_str).parts)

def matches_any_glob(path: str, globs: List[str]) -> bool:
    from fnmatch import fnmatch
    return any(fnmatch(path, g) for g in globs)

def compile_regex_map(pattern_map: Dict[str, str]) -> Dict[str, re.Pattern]:
    out = {}
    for k, v in pattern_map.items():
        out[k] = re.compile(v)
    return out

def check_case(name: str, mode: str) -> bool:
    fn = CASE_FUNCS.get(mode.lower())
    if not fn:
        return True
    base = os.path.splitext(name)[0]
    return fn(base)

def lint(paths: List[str], cfg: Dict[str, Any]) -> List[str]:
    errors: List[str] = []
    # normalize config
    allowed_root_dirs = set(cfg.get("allowed_root_dirs", []))
    required_files = cfg.get("required_files", [])
    forbidden_paths_glob = cfg.get("forbidden_paths_glob", [])
    ignore_globs = cfg.get("ignore_globs", [])
    allowed_extensions = set(cfg.get("allowed_extensions", []))
    blocked_extensions = set(cfg.get("blocked_extensions", []))
    max_depth = cfg.get("max_depth")
    max_filename_len = cfg.get("max_filename_length")
    max_path_len = cfg.get("max_path_length")
    enforce_case = cfg.get("enforce_case")  # snake/kebab/camel/pascal or null
    dir_name_pattern = cfg.get("dir_name_pattern")
    file_name_patterns = cfg.get("file_name_patterns", {})  # key: glob or extension (e.g. "*.php" or ".env")
    compiled_file_name_patterns = compile_regex_map(file_name_patterns) if file_name_patterns else {}
    dir_name_regex = re.compile(dir_name_pattern) if isinstance(dir_name_pattern, str) else None

    # 0) required files exist (only when running --all or if staged includes them? Check repo)
    for rf in required_files:
        if not (REPO_ROOT / rf).exists():
            errors.append(f"[required_files] Missing required path: {rf}")

    for path in paths:
        # ignore?
        if ignore_globs and matches_any_glob(path, ignore_globs):
            continue

        # forbidden globs
        if forbidden_paths_glob and matches_any_glob(path, forbidden_paths_glob):
            errors.append(f"[forbidden_paths_glob] Path not allowed by glob rule: {path}")
            continue

        p = Path(path)

        # 1) allowed_root_dirs
        if allowed_root_dirs:
            if len(p.parts) >= 1:
                root = p.parts[0]
                # allow files at root if allowed_root_dirs contains "" or special "*"
                if root not in allowed_root_dirs and root != "." and root != "":
                    # But also allow files at root if the file is directly at root and allowed_root_dirs includes "<root>"
                    if p.parent == Path(".") and "<root>" in allowed_root_dirs:
                        pass
                    else:
                        errors.append(f"[allowed_root_dirs] Top-level folder '{root}' not in allowed set {sorted(allowed_root_dirs)} (path: {path})")

        # 2) depth
        if isinstance(max_depth, int):
            d = path_depth(path)
            if d > max_depth:
                errors.append(f"[max_depth] {path} has depth {d} > {max_depth}")

        # 3) lengths
        filename = p.name
        if isinstance(max_filename_len, int) and len(filename) > max_filename_len:
            errors.append(f"[max_filename_length] '{filename}' length {len(filename)} > {max_filename_len} (path: {path})")
        if isinstance(max_path_len, int) and len(path) > max_path_len:
            errors.append(f"[max_path_length] Path length {len(path)} > {max_path_len}: {path}")

        # 4) extensions allow/deny
        ext = p.suffix  # includes dot, e.g. ".php"
        if allowed_extensions and ext and ext not in allowed_extensions:
            errors.append(f"[allowed_extensions] Extension '{ext}' not allowed (path: {path})")
        if blocked_extensions and ext in blocked_extensions:
            errors.append(f"[blocked_extensions] Extension '{ext}' is blocked (path: {path})")

        # 5) case convention for files
        if enforce_case and not check_case(filename, enforce_case):
            errors.append(f"[enforce_case] '{filename}' does not follow {enforce_case}-case (path: {path})")

        # 6) directory name rules
        if dir_name_regex:
            for part in p.parts[:-1]:
                if part in (".",):
                    continue
                if not dir_name_regex.fullmatch(part):
                    errors.append(f"[dir_name_pattern] Directory '{part}' fails pattern '{dir_name_pattern}' (path: {path})")

        # 7) file_name_patterns (glob or extension key)
        for key, rx in compiled_file_name_patterns.items():
            # key can be like "*.php" or ".env" or "src/**/*.ts"
            # if match, then filename must pass regex
            from fnmatch import fnmatch
            matches = False
            if key.startswith("."):
                # treat as extension mapping
                if ext == key:
                    matches = True
            else:
                if fnmatch(path, key):
                    matches = True
            if matches:
                if not rx.fullmatch(filename):
                    errors.append(f"[file_name_patterns:{key}] '{filename}' fails regex '{rx.pattern}' (path: {path})")

        # 8) directory case convention (reuse enforce_case)
        if enforce_case:
            for part in p.parts[:-1]:
                if part in (".",):
                    continue
                if not CASE_FUNCS.get(enforce_case, lambda _: True)(part):
                    errors.append(f"[enforce_case-dir] Directory '{part}' does not follow {enforce_case}-case (path: {path})")

    return errors

def main(argv: List[str]) -> int:
    cfg = load_config()
    if "--print-config" in argv:
        print(json.dumps(cfg, indent=2))
        return 0

    if "--all" in argv:
        candidate_paths = get_all_repo_files()
    else:
        candidate_paths = get_staged_files()

    # If nothing to check, succeed.
    if not candidate_paths:
        return 0

    violations = lint(candidate_paths, cfg)
    if violations:
        print("❌ Lint failures:")
        for v in violations:
            print(" -", v)
        return 1

    print("✅ All checked paths pass lint rules.")
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
```

---

# 2) Sample config: `.gitlint.yml`

```yaml
# Top-level folders allowed. Use "<root>" to permit files at repo root.
allowed_root_dirs:
  - "<root>"
  - src
  - public
  - config
  - tests
  - scripts

# Files/directories that must exist
required_files:
  - README.md
  - config
  - src

# Ignore certain paths (globs)
ignore_globs:
  - ".git/**"
  - "vendor/**"
  - "node_modules/**"
  - ".venv/**"
  - "coverage/**"

# Forbid specific globs entirely
forbidden_paths_glob:
  - "**/*.tmp"
  - "**/~*"
  - "**/.DS_Store"
  - "public/**/debug/**"

# Allowed / blocked extensions
allowed_extensions: [".php", ".js", ".ts", ".json", ".yml", ".yaml", ".md"]
blocked_extensions: [".bak", ".swp", ".log"]

# Depth & length limits
max_depth: 12
max_filename_length: 64
max_path_length: 180

# Enforce a naming case across files & directories (snake|kebab|camel|pascal)
enforce_case: kebab

# Regex that every directory name must match (after case check)
dir_name_pattern: "^[a-z0-9-]+$"

# Per-glob or per-extension file name rules (regex applied to the filename only)
file_name_patterns:
  "*.php": "^[a-z0-9-]+\\.php$"
  "src/**/*.ts": "^[a-z0-9-]+\\.(d\\.)?ts$"
  ".json": "^[a-z0-9-]+\\.json$"
  "tests/**/*.php": "^[a-z0-9-]+Test\\.php$"
```

> Prefer YAML for readability; if you'd rather not install PyYAML, rename to `.gitlint.json` with equivalent keys.

---

# 3) Wire it up as a **pre-commit hook**

### Option A — simple Git hook (no extra tooling)

```bash
# make script executable
chmod +x git-lint.py

# create .git/hooks/pre-commit
cat > .git/hooks/pre-commit << 'SH'
#!/bin/sh
# Run the linter on staged files
python3 git-lint.py
rc=$?
if [ $rc -ne 0 ]; then
  echo ""
  echo "Fix the lint errors above, then re-stage and commit again."
fi
exit $rc
SH
chmod +x .git/hooks/pre-commit
```

### Option B — pre-commit framework (recommended)

`.pre-commit-config.yaml`:

```yaml
repos:
  - repo: local
    hooks:
      - id: git-structure-lint
        name: Git Structure Lint
        entry: python3 git-lint.py
        language: system
        pass_filenames: false
```

Then:

```bash
pip install pre-commit pyyaml
pre-commit install
```

---

# 4) CI/CD (GitLab or GitHub)

**GitLab CI** (`.gitlab-ci.yml`):

```yaml
stages: [lint]
lint:structure:
  stage: lint
  image: python:3.12-slim
  script:
    - pip install pyyaml || true
    - python3 git-lint.py --all
```

**GitHub Actions** (`.github/workflows/lint-structure.yml`):

```yaml
name: Lint structure
on: [push, pull_request]
jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pip install pyyaml || true
      - run: python3 git-lint.py --all
```

---

# 5) Tweaking rules

* Change `enforce_case` to `snake` if you want `snake_case` everywhere.
* Narrow `allowed_root_dirs` to force a very specific repo layout.
* Add more `file_name_patterns` entries per folder tree to lock down naming in critical areas (e.g., `public/assets/**`).
* Use `forbidden_paths_glob` to block secrets from being committed (e.g., `**/*.pem`, `**/.env*`).

---

If you want, tell me your **desired layout** (top-level folders, conventions, special cases for PHP) and I'll pre-fill a config tailored to your repo.
