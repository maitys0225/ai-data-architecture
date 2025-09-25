Got it, Sidd! Below is a ready-to-run Python module that:

* Reads a GitLab repo (public or private) into text
* Chunks source files sensibly
* Calls **Azure OpenAI** with robust retries
* Produces:

  1. Summary of the code
  2. Variables used & relationships (as JSON)
  3. A **Mermaid** control-flow diagram
  4. A code improvement report
  5. A consistent checklist for a Design Review Board

It’s designed so you can point it at a repo URL, or a local path you’ve already cloned. It uses only environment variables for secrets and supports private GitLab tokens and private Azure OpenAI deployments.

---

### What you’ll need

**Environment variables**

* `GITLAB_TOKEN` (optional, for private repos over HTTPS)
* `AZURE_OPENAI_ENDPOINT` (e.g., `https://your-resource-name.openai.azure.com`)
* `AZURE_OPENAI_API_KEY`
* `AZURE_OPENAI_DEPLOYMENT` (your chat/completions deployment name)
* `AZURE_OPENAI_API_VERSION` (e.g., `2024-08-01-preview`)

**Dependencies**

```bash
pip install gitpython requests pydantic python-dotenv
```

---

### The module

````python
# file: repo_inspector.py
from __future__ import annotations

import os
import re
import json
import time
import fnmatch
import shutil
import tempfile
import hashlib
import logging
from typing import Iterable, List, Dict, Optional, Tuple
from dataclasses import dataclass

import requests
from pydantic import BaseModel, Field, ValidationError

try:
    from git import Repo  # GitPython
except ImportError:
    Repo = None

# ----------------------------
# Logging
# ----------------------------
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger("repo_inspector")


# ----------------------------
# Models
# ----------------------------
class VariableEntity(BaseModel):
    name: str
    type: Optional[str] = None
    defined_in_files: List[str] = Field(default_factory=list)
    defined_lines: List[str] = Field(default_factory=list)
    used_in_files: List[str] = Field(default_factory=list)
    related_to: List[str] = Field(default_factory=list)  # other variable names


class VariablesGraph(BaseModel):
    variables: List[VariableEntity] = Field(default_factory=list)
    relationships: List[Tuple[str, str, str]] = Field(
        default_factory=list,
        description="(source_var, target_var, relation_label)"
    )


class GenerationBundle(BaseModel):
    summary_md: str
    variables_graph_json: str
    control_flow_mermaid: str
    improvement_report_md: str
    drb_checklist_md: str


# ----------------------------
# Git / File ingestion
# ----------------------------
DEFAULT_INCLUDE = [
    "*.py", "*.js", "*.ts", "*.tsx", "*.jsx", "*.java", "*.go", "*.rb", "*.php",
    "*.cs", "*.cpp", "*.c", "*.h", "*.hpp", "*.rs", "*.kt", "*.swift",
    "*.sql", "*.yml", "*.yaml", "*.toml", "*.json", "Dockerfile", "Makefile",
    "*.sh", "*.bat", "*.ps1"
]
DEFAULT_EXCLUDE = [
    ".git/*", "node_modules/*", "dist/*", "build/*", "venv/*", ".venv/*",
    ".mypy_cache/*", ".ruff_cache/*", ".pytest_cache/*", ".idea/*", ".vscode/*",
    "coverage/*", "site-packages/*", "__pycache__/*", "*.min.js", "*.lock",
    "*.png", "*.jpg", "*.jpeg", "*.gif", "*.svg", "*.pdf", "*.ico", "*.bin",
    "*.exe", "*.zip", "*.tar", "*.gz"
]


def _match_any(path: str, patterns: List[str]) -> bool:
    norm = path.replace("\\", "/")
    return any(fnmatch.fnmatch(norm, pat) for pat in patterns)


def _iter_files(root: str, include: List[str], exclude: List[str]) -> Iterable[str]:
    for base, dirs, files in os.walk(root):
        rel_base = os.path.relpath(base, root)
        for f in files:
            rel_path = os.path.join(rel_base, f) if rel_base != "." else f
            rel_path_norm = rel_path.replace("\\", "/")
            if _match_any(rel_path_norm, exclude):
                continue
            if any(fnmatch.fnmatch(rel_path_norm, pat) for pat in include):
                yield os.path.join(root, rel_path)


def clone_gitlab_repo(repo_url: str, branch: Optional[str] = None) -> str:
    """
    Clone to a temp dir. Supports HTTPS with optional GITLAB_TOKEN.
    For SSH URLs, rely on your local SSH agent.
    """
    if Repo is None:
        raise RuntimeError("GitPython not installed. Run: pip install gitpython")

    tmpdir = tempfile.mkdtemp(prefix="repo_inspector_")
    token = os.getenv("GITLAB_TOKEN")

    # If HTTPS and token present, inject token
    if token and repo_url.startswith("https://"):
        # https://oauth2:<TOKEN>@gitlab.com/group/project.git
        repo_url = re.sub(r"^https://", f"https://oauth2:{token}@", repo_url)

    log.info(f"Cloning {repo_url} -> {tmpdir}")
    repo = Repo.clone_from(repo_url, tmpdir, branch=branch) if branch else Repo.clone_from(repo_url, tmpdir)
    log.info(f"Cloned commit: {repo.head.commit.hexsha}")
    return tmpdir


def load_repo_text(
    repo_root: str,
    include: Optional[List[str]] = None,
    exclude: Optional[List[str]] = None,
    max_bytes_per_file: int = 150_000
) -> Dict[str, str]:
    include = include or DEFAULT_INCLUDE
    exclude = exclude or DEFAULT_EXCLUDE
    out: Dict[str, str] = {}
    for path in _iter_files(repo_root, include, exclude):
        try:
            with open(path, "rb") as f:
                raw = f.read(max_bytes_per_file + 1)
            if len(raw) > max_bytes_per_file:
                log.warning(f"Truncated large file: {os.path.relpath(path, repo_root)}")
                raw = raw[:max_bytes_per_file]
            # naive decode
            text = raw.decode("utf-8", errors="replace")
            rel = os.path.relpath(path, repo_root).replace("\\", "/")
            out[rel] = text
        except Exception as e:
            log.error(f"Failed to read {path}: {e}")
    return out


# ----------------------------
# Chunking / Prompting helpers
# ----------------------------
def chunk_text(name: str, text: str, chunk_chars: int = 8000, overlap: int = 400) -> List[Tuple[str, str]]:
    """
    Break a file into overlapping chunks for LLM context. Returns list of (chunk_id, chunk_text).
    """
    chunks = []
    i = 0
    n = len(text)
    while i < n:
        j = min(i + chunk_chars, n)
        chunk = text[i:j]
        chunk_id = f"{name}::[{i}:{j}]"
        chunks.append((chunk_id, chunk))
        i = j - overlap
        if i < 0:
            i = 0
    return chunks


def make_file_digest(file_map: Dict[str, str]) -> List[Tuple[str, str]]:
    """
    Convert repo files into (path, content) pairs, skipping empty.
    """
    items = []
    for path, text in file_map.items():
        t = text.strip()
        if t:
            items.append((path, t))
    # Small deterministic order
    items.sort(key=lambda x: x[0])
    return items


# ----------------------------
# Azure OpenAI low-level REST client (chat/completions)
# ----------------------------
class AzureChatClient:
    def __init__(
        self,
        endpoint: Optional[str] = None,
        api_key: Optional[str] = None,
        deployment: Optional[str] = None,
        api_version: Optional[str] = None,
        timeout: int = 60
    ):
        self.endpoint = endpoint or os.getenv("AZURE_OPENAI_ENDPOINT")
        self.api_key = api_key or os.getenv("AZURE_OPENAI_API_KEY")
        self.deployment = deployment or os.getenv("AZURE_OPENAI_DEPLOYMENT")
        self.api_version = api_version or os.getenv("AZURE_OPENAI_API_VERSION", "2024-08-01-preview")
        self.timeout = timeout

        if not all([self.endpoint, self.api_key, self.deployment, self.api_version]):
            raise RuntimeError("Missing one or more Azure OpenAI env vars: AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY, AZURE_OPENAI_DEPLOYMENT, AZURE_OPENAI_API_VERSION")

        self.url = f"{self.endpoint}/openai/deployments/{self.deployment}/chat/completions?api-version={self.api_version}"
        self.headers = {
            "Content-Type": "application/json",
            "api-key": self.api_key,
        }

    def chat(self, messages: List[Dict], temperature: float = 0.2, max_tokens: int = 2000, retries: int = 5) -> str:
        backoff = 1.5
        for attempt in range(retries):
            try:
                payload = {
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "n": 1,
                }
                resp = requests.post(self.url, headers=self.headers, json=payload, timeout=self.timeout)
                if resp.status_code == 200:
                    data = resp.json()
                    return data["choices"][0]["message"]["content"]
                else:
                    log.warning(f"Azure OpenAI HTTP {resp.status_code}: {resp.text[:300]}")
                    if resp.status_code in (429, 500, 502, 503, 504):
                        time.sleep(backoff ** (attempt + 1))
                        continue
                    resp.raise_for_status()
            except Exception as e:
                log.warning(f"Azure call failed (attempt {attempt+1}/{retries}): {e}")
                time.sleep(backoff ** (attempt + 1))
        raise RuntimeError("Azure OpenAI request failed after retries")


# ----------------------------
# Prompts
# ----------------------------
SYSTEM_ANALYST = """You are a senior software analyst. Be precise, terse where appropriate, and return clean, validated formats when asked (JSON, Mermaid)."""

FILE_SUMMARY_PROMPT = """You will be given a code file chunk. Summarize its purpose, key functions/classes, and noteworthy behaviors.
Output in concise markdown with a short title.
"""

VARIABLES_PROMPT = """Extract variables, their types (if inferable), where they are defined and used, and relationships (e.g., 'feeds', 'derived-from', 'mutates', 'reads').
Return STRICT JSON in this schema:

{
  "variables": [
    {
      "name": "string",
      "type": "string|null",
      "defined_in_files": ["path:line", "..."],
      "defined_lines": ["line text (optional)"],
      "used_in_files": ["path", "..."],
      "related_to": ["otherVar", "..."]
    }
  ],
  "relationships": [
    ["sourceVar", "targetVar", "relationLabel"]
  ]
}

Do not include comments or backticks outside JSON.
"""

REPO_SUMMARY_PROMPT = """You will receive a collection of per-file summaries. Produce a cohesive repository overview:
- Project purpose and main components
- Key modules and their responsibilities
- Data flow between major parts
- External dependencies and integrations
Return markdown, ≤ 300 words.
"""

CONTROL_FLOW_PROMPT = """Based on the repository summaries and any variable graphs provided, produce a high-level control-flow diagram using Mermaid 'flowchart TD' syntax.
Guidelines:
- Keep nodes concise (≤ 5 words)
- Show start, key decisions, loops, error paths
- Group subsystems with subgraphs
Return ONLY Mermaid code block:
```mermaid
flowchart TD
...
````

"""

IMPROVEMENTS\_PROMPT = """Create a detailed code improvement report:

* Architecture issues and recommendations
* Code quality findings (readability, duplication, smells)
* Security considerations
* Performance hotspots and suggestions
* Testing gaps and coverage strategy
* Observability (logging/metrics/tracing)
  Return markdown with clear subsections and prioritized bullets.
  """

DRB\_CHECKLIST\_PROMPT = """Create a consistent Design Review Board checklist for this repo:

* Design & Architecture
* Security & Privacy
* Reliability & Performance
* Code Quality & Maintainability
* Testing & Release
* Documentation & Operations
  Return concise markdown checklist with checkboxes (- \[ ]).
  """

# ----------------------------

# Orchestrators

# ----------------------------

def summarize\_files(client: AzureChatClient, files: List\[Tuple\[str, str]], chunk\_chars: int = 8000) -> Dict\[str, str]:
per\_file\_summary: Dict\[str, str] = {}
for path, content in files:
chunks = chunk\_text(path, content, chunk\_chars=chunk\_chars)
chunk\_summaries = \[]
for cid, ctext in chunks:
messages = \[
{"role": "system", "content": SYSTEM\_ANALYST},
{"role": "user", "content": f"{FILE\_SUMMARY\_PROMPT}\n\nFile: {path}\nChunk: {cid}\n\n`text\n{ctext}\n`"}
]
chunk\_summaries.append(client.chat(messages, max\_tokens=800))
\# Merge chunk summaries
joined = "\n".join(f"- {s.strip()}" for s in chunk\_summaries)
per\_file\_summary\[path] = f"### {path}\n{joined}\n"
return per\_file\_summary

def extract\_variables(client: AzureChatClient, files: List\[Tuple\[str, str]], chunk\_chars: int = 8000) -> VariablesGraph:
merged\_vars: Dict\[str, VariableEntity] = {}
relationships: set\[Tuple\[str, str, str]] = set()

````
for path, content in files:
    chunks = chunk_text(path, content, chunk_chars=chunk_chars)
    for cid, ctext in chunks:
        messages = [
            {"role": "system", "content": SYSTEM_ANALYST},
            {"role": "user", "content": f"{VARIABLES_PROMPT}\n\nContext file: {path}\nChunk: {cid}\n\n```code\n{ctext}\n```"}
        ]
        raw = client.chat(messages, max_tokens=1400)
        try:
            data = json.loads(raw)
            vg = VariablesGraph(**data)
        except (json.JSONDecodeError, ValidationError) as e:
            log.warning(f"Variable JSON parse error in {path} ({cid}): {e}")
            continue

        for v in vg.variables:
            if v.name not in merged_vars:
                merged_vars[v.name] = v
            else:
                # merge
                cur = merged_vars[v.name]
                cur.type = cur.type or v.type
                cur.defined_in_files = sorted(set(cur.defined_in_files + v.defined_in_files))
                cur.defined_lines = sorted(set(cur.defined_lines + v.defined_lines))
                cur.used_in_files = sorted(set(cur.used_in_files + v.used_in_files))
                cur.related_to = sorted(set(cur.related_to + v.related_to))

        for (s, t, r) in vg.relationships:
            relationships.add((s, t, r))

return VariablesGraph(variables=list(merged_vars.values()), relationships=list(relationships))
````

def generate\_repo\_summary(client: AzureChatClient, per\_file\_summary: Dict\[str, str]) -> str:
combined = "\n".join(per\_file\_summary\[k] for k in sorted(per\_file\_summary))
messages = \[
{"role": "system", "content": SYSTEM\_ANALYST},
{"role": "user", "content": f"{REPO\_SUMMARY\_PROMPT}\n\nPer-file summaries:\n\n{combined}"}
]
return client.chat(messages, max\_tokens=900)

def generate\_control\_flow(client: AzureChatClient, repo\_summary\_md: str, variables\_graph: VariablesGraph) -> str:
vg\_json = variables\_graph.model\_dump\_json()
messages = \[
{"role": "system", "content": SYSTEM\_ANALYST},
{"role": "user", "content": f"{CONTROL\_FLOW\_PROMPT}\n\nRepository summary:\n{repo\_summary\_md}\n\nVariables graph JSON:\n`json\n{vg_json}\n`"}
]
return client.chat(messages, max\_tokens=900)

def generate\_improvements(client: AzureChatClient, repo\_summary\_md: str) -> str:
messages = \[
{"role": "system", "content": SYSTEM\_ANALYST},
{"role": "user", "content": f"{IMPROVEMENTS\_PROMPT}\n\nRepository summary:\n{repo\_summary\_md}"}
]
return client.chat(messages, max\_tokens=1200)

def generate\_drb\_checklist(client: AzureChatClient, repo\_summary\_md: str) -> str:
messages = \[
{"role": "system", "content": SYSTEM\_ANALYST},
{"role": "user", "content": f"{DRB\_CHECKLIST\_PROMPT}\n\nContext:\n{repo\_summary\_md}"}
]
return client.chat(messages, max\_tokens=800)

def analyze\_repository(
repo\_source: str,
branch: Optional\[str] = None,
local\_path: bool = False,
include: Optional\[List\[str]] = None,
exclude: Optional\[List\[str]] = None,
cleanup: bool = True
) -> GenerationBundle:
"""
repo\_source: HTTPS/SSH URL or local path (if local\_path=True)
"""
tmpdir = None
try:
if local\_path:
repo\_root = repo\_source
else:
repo\_root = clone\_gitlab\_repo(repo\_source, branch=branch)
tmpdir = repo\_root

```
    files_map = load_repo_text(repo_root, include=include, exclude=exclude)
    file_items = make_file_digest(files_map)

    client = AzureChatClient()

    # 1) Per-file summaries
    per_file_summaries = summarize_files(client, file_items)

    # 2) Repo summary
    repo_summary_md = generate_repo_summary(client, per_file_summaries)

    # 3) Variables & relationships (JSON)
    variables_graph = extract_variables(client, file_items)
    variables_graph_json = variables_graph.model_dump_json(indent=2)

    # 4) Control flow diagram (Mermaid)
    control_flow_mermaid = generate_control_flow(client, repo_summary_md, variables_graph)

    # 5) Improvement report
    improvement_report_md = generate_improvements(client, repo_summary_md)

    # 6) DRB checklist
    drb_checklist_md = generate_drb_checklist(client, repo_summary_md)

    return GenerationBundle(
        summary_md=repo_summary_md,
        variables_graph_json=variables_graph_json,
        control_flow_mermaid=control_flow_mermaid,
        improvement_report_md=improvement_report_md,
        drb_checklist_md=drb_checklist_md,
    )
finally:
    if tmpdir and cleanup:
        shutil.rmtree(tmpdir, ignore_errors=True)
```

# ----------------------------

# CLI

# ----------------------------

def \_write\_out(bundle: GenerationBundle, out\_dir: str) -> None:
os.makedirs(out\_dir, exist\_ok=True)
with open(os.path.join(out\_dir, "01\_summary.md"), "w", encoding="utf-8") as f:
f.write(bundle.summary\_md.strip() + "\n")
with open(os.path.join(out\_dir, "02\_variables.json"), "w", encoding="utf-8") as f:
f.write(bundle.variables\_graph\_json.strip() + "\n")
with open(os.path.join(out\_dir, "03\_control\_flow\.mmd"), "w", encoding="utf-8") as f:
f.write(bundle.control\_flow\_mermaid.strip() + "\n")
with open(os.path.join(out\_dir, "04\_improvements.md"), "w", encoding="utf-8") as f:
f.write(bundle.improvement\_report\_md.strip() + "\n")
with open(os.path.join(out\_dir, "05\_drb\_checklist.md"), "w", encoding="utf-8") as f:
f.write(bundle.drb\_checklist\_md.strip() + "\n")

def main():
import argparse
parser = argparse.ArgumentParser(description="Analyze a GitLab repository using Azure OpenAI.")
parser.add\_argument("repo", help="GitLab repo URL or local path")
parser.add\_argument("--branch", help="Branch name", default=None)
parser.add\_argument("--local", action="store\_true", help="Treat repo argument as a local path")
parser.add\_argument("--out", default="analysis\_out", help="Output directory")
parser.add\_argument("--no-clean", action="store\_true", help="Do not delete temp clone")
args = parser.parse\_args()

```
bundle = analyze_repository(
    repo_source=args.repo,
    branch=args.branch,
    local_path=args.local,
    cleanup=not args.no_clean
)
_write_out(bundle, args.out)
log.info(f"Wrote outputs to: {args.out}")
```

if **name** == "**main**":
main()

````

---

### How to run

```bash
export AZURE_OPENAI_ENDPOINT="https://<your-resource>.openai.azure.com"
export AZURE_OPENAI_API_KEY="<your-key>"
export AZURE_OPENAI_DEPLOYMENT="<your-chat-deployment>"
export AZURE_OPENAI_API_VERSION="2024-08-01-preview"
# Optional if private repo:
export GITLAB_TOKEN="<your-gitlab-pat>"

python repo_inspector.py https://gitlab.com/<group>/<project>.git --branch main --out rely_analysis
````

This will produce:

* `01_summary.md` — repository-level summary
* `02_variables.json` — variables & relationships (strict JSON)
* `03_control_flow.mmd` — Mermaid diagram (render in any Mermaid viewer)
* `04_improvements.md` — code improvement report
* `05_drb_checklist.md` — DRB checklist

---

### Notes & tweaks

* **Scope:** Adjust `DEFAULT_INCLUDE/DEFAULT_EXCLUDE` to match your stacks (e.g., Laravel/PHP, Vue, etc.).
* **Chunk size:** If you hit context limits, reduce `chunk_chars` in `summarize_files` / `extract_variables`.
* **Security:** For SSH-based private repos, skip `GITLAB_TOKEN` and use your SSH agent.
* **Output formats:** The control-flow is in Mermaid to drop into docs, PRs, or wikis.

If you want, share your repo URL pattern (public sample is fine) and I’ll tailor the include/exclude glob patterns for your codebase (e.g., PHP-heavy with Laravel conventions).
