#!/usr/bin/env python3
import os
import sys
import io
import json
import base64
import re
from pathlib import Path
from typing import Dict, List, Tuple, Optional

import gitlab  # python-gitlab
import requests
import networkx as nx

# Azure OpenAI client via OpenAI SDK (pointed to Azure endpoint)
from openai import OpenAI

# -----------------------------
# Config via environment
# -----------------------------
GITLAB_URL = os.getenv("GITLAB_URL", "https://gitlab.com")
GITLAB_PROJECT = os.getenv("GITLAB_PROJECT_ID")  # can be numeric or 'namespace/project'
GITLAB_TOKEN = os.getenv("GITLAB_TOKEN")

AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT")  # deployment name
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2024-07-01-preview")

OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "docs"))
DEFAULT_BRANCH = os.getenv("DEFAULT_BRANCH", "main")
MAX_FILES = int(os.getenv("MAX_FILES", "400"))  # safety cap

# -----------------------------
# Utilities
# -----------------------------
def ensure_env():
    missing = []
    for k in ["GITLAB_PROJECT_ID", "GITLAB_TOKEN", "AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_API_KEY", "AZURE_OPENAI_DEPLOYMENT"]:
        if not os.getenv(k):
            missing.append(k)
    if missing:
        print(f"Missing required environment variables: {', '.join(missing)}", file=sys.stderr)
        sys.exit(1)

def sanitize_path(p: str) -> str:
    return p.strip().lstrip("/")

def is_text_file(name: str) -> bool:
    # Heuristic: only fetch code/text files to save tokens
    text_ext = [
        ".py",".js",".ts",".java",".go",".rb",".php",".cs",".cpp",".c",".h",".hpp",
        ".rs",".kt",".m",".swift",".scala",".sql",".yaml",".yml",".json",".toml",".ini",
        ".cfg",".md",".txt",".sh",".bash",".ps1",".xml",".html",".css",".vue",".svelte",
        ".gradle",".properties",".dockerfile",".dockerignore",".gitignore"
    ]
    lower = name.lower()
    if lower.endswith(tuple(text_ext)):
        return True
    # treat top-level Dockerfile etc. as text
    if os.path.basename(lower) in ["dockerfile", "makefile", "procfile"]:
        return True
    return False

# -----------------------------
# GitLab fetcher
# -----------------------------
class GitLabRepo:
    def __init__(self, url: str, token: str, project: str):
        self.url = url
        self.token = token
        self.project_id_or_path = project
        self.gl = gitlab.Gitlab(url=self.url, private_token=self.token)
        self.gl.auth()
        self.project = self._get_project()

    def _get_project(self):
        # Supports numeric ID or full path
        try:
            if self.project_id_or_path.isdigit():
                return self.gl.projects.get(int(self.project_id_or_path))
        except Exception:
            pass
        return self.gl.projects.get(self.project_id_or_path)

    def get_default_branch(self) -> str:
        return self.project.default_branch or DEFAULT_BRANCH

    def walk_tree(self, branch: str) -> List[Dict]:
        # Paginate through repository_tree; python-gitlab handles paging via iterator
        items = []
        page = 1
        while True:
            chunk = self.project.repository_tree(ref=branch, recursive=True, per_page=100, page=page)
            if not chunk:
                break
            items.extend(chunk)
            page += 1
            if len(items) >= MAX_FILES:
                break
        return items

    def get_file(self, file_path: str, ref: str) -> Optional[str]:
        # Use API to get base64 content
        try:
            f = self.project.files.get(file_path=file_path, ref=ref)
            content = base64.b64decode(f.content).decode("utf-8", errors="ignore")
            return content
        except Exception:
            return None

# -----------------------------
# Azure OpenAI analysis
# -----------------------------
class AzureOpenAIAnalyzer:
    def __init__(self, endpoint: str, api_key: str, deployment: str, api_version: str):
        # OpenAI SDK configured for Azure REST base_url
        self.client = OpenAI(
            base_url=f"{endpoint.rstrip('/')}/openai/v1/",
            api_key=api_key,
        )
        self.deployment = deployment
        self.api_version = api_version

    def analyze(self, project_summary: str, sampled_files: Dict[str, str]) -> Dict:
        """
        Use the Responses API to produce structured outputs: C1–C4 textual descriptions,
        mind map nodes/edges, and narrative.
        """
        # Build a compressed prompt – only summarize key files to control token usage
        files_list = "\n".join([f"- {p}" for p in sampled_files.keys()])
        instructions = (
            "You are an expert software architect. From the provided project summary and code snippets, produce:\n"
            "1) C1 Context: external actors and systems; concise bullet list.\n"
            "2) C2 Containers: list containers/apps/data stores, responsibilities, technologies; bullet list.\n"
            "3) C3 Components: per container, key components and relationships; bullet list.\n"
            "4) C4 Code-level notes: modules/classes/functions that form critical paths; bullet list.\n"
            "5) Mind map plan: root name, main branches, and edges as pairs for a Mermaid mindmap.\n"
            "Return strict JSON with fields: {\"c1\":..., \"c2\":..., \"c3\":..., \"c4\":..., \"mindmap\": {\"root\": str, \"branches\": [str], \"edges\": [[str,str], ...]}, \"narrative\": str}."
        )

        # Prepare compact snippets
        snippet_pairs = []
        limit = 12000  # characters cap for request body assembly
        used = 0
        for path, text in sampled_files.items():
            if used > limit:
                break
            short = text[:3000]
            snippet_pairs.append(f"\n### {path}\n``````")
            used += len(short)

        input_text = f"""
PROJECT SUMMARY:
{project_summary}

FILES INCLUDED:
{files_list}

SNIPPETS:
{''.join(snippet_pairs)}
"""

        response = self.client.responses.create(
            model=self.deployment,
            # Azure Responses accepts an array for input or a string; keep simple
            input=[
                {"role": "system", "content": instructions},
                {"role": "user", "content": input_text},
            ],
        )
        # Extract text output
        out = response.output_text if hasattr(response, "output_text") else None
        if not out:
            # Fallback parse
            try:
                out = response.output[0].content[0].text
            except Exception:
                out = ""

        # Try parse JSON
        try:
            start = out.find("{")
            end = out.rfind("}")
            parsed = json.loads(out[start:end+1])
            return parsed
        except Exception:
            return {
                "c1": "Parsing error; see narrative.",
                "c2": "",
                "c3": "",
                "c4": "",
                "mindmap": {"root": "Project", "branches": [], "edges": []},
                "narrative": out[:4000],
            }

# -----------------------------
# Diagram emitters (PlantUML C4 and Mermaid mindmap)
# -----------------------------
def emit_c4_plantuml(c1: str, c2: str, c3: str, c4: str) -> Dict[str, str]:
    """
    Return PlantUML text for C1, C2, C3 using C4-PlantUML macros.
    C4 (code-level) will be kept as notes or simple relationships comment.
    """
    header_ctx = "!include https://raw.githubusercontent.com/plantuml-stdlib/C4-PlantUML/master/C4_Context.puml"
    header_ctr = "!include https://raw.githubusercontent.com/plantuml-stdlib/C4-PlantUML/master/C4_Container.puml"
    header_cmp = "!include https://raw.githubusercontent.com/plantuml-stdlib/C4-PlantUML/master/C4_Component.puml"

    # Minimal scaffolding; user edits after generation
    c1_puml = f"""@startuml C1_Context
{header_ctx}
title C1: System Context
' Auto-generated summary bullets in note
note as N1
{c1}
end note
@enduml
"""

    c2_puml = f"""@startuml C2_Containers
{header_ctr}
title C2: Containers
note as N2
{c2}
end note
@enduml
"""

    c3_puml = f"""@startuml C3_Components
{header_cmp}
title C3: Components
note as N3
{c3}
end note
@enduml
"""

    # For C4 code-level, include as a note or leave for class diagrams/sequence later
    c4_puml = f"""@startuml C4_Code
title C4: Code-Level Notes
note as N4
{c4}
end note
@enduml
"""
    return {"c1": c1_puml, "c2": c2_puml, "c3": c3_puml, "c4": c4_puml}

def emit_mermaid_mindmap(root: str, branches: List[str], edges: List[List[str]]) -> str:
    """
    Mermaid mindmap DSL; simple tree projection.
    """
    # Mermaid mindmap is a newer diagram type; safe to emit simple tree-like structure.
    lines = ["```
mermaid
mindmap"]
    norm = lambda s: re.sub(r'[^A-Za-z0-9]+', '_', s.lower()).strip("_") or "node"
    bmap = {}
    for b in branches:
        bid = norm(b)
        bmap[b] = bid
        lines.append(f"    {bid}({b})")
        lines.append(f"  root --> {bid}")
    for a, b in edges:
        aid = bmap.get(a, norm(a))
        bid = bmap.get(b, norm(b))
        # define if missing
        if a not in bmap:
            lines.append(f"    {aid}({a})")
            lines.append(f"  root --> {aid}")
            bmap[a] = aid
        if b not in bmap:
            lines.append(f"    {bid}({b})")
            lines.append(f"  {aid} --> {bid}")
        else:
            lines.append(f"  {aid} --> {bid}")
    lines.append("```")
    return "\n".join(lines)

# -----------------------------
# Markdown report
# -----------------------------
def write_markdown_report(out_dir: Path, project_name: str, narrative: str, c4_files: Dict[str, str], mindmap_mermaid: str):
    out_dir.mkdir(parents=True, exist_ok=True)
    # Write PlantUML sources
    for k, txt in c4_files.items():
        (out_dir / f"{k}.puml").write_text(txt, encoding="utf-8")

    # Write mindmap
    (out_dir / "mindmap.mmd").write_text(mindmap_mermaid, encoding="utf-8")

    # Compose README.md
    md = []
    md.append(f"# {project_name} - Architecture Report")
    md.append("")
    md.append("## Executive Summary")
    md.append("")
    md.append(narrative)
    md.append("")
    md.append("## C4 Diagrams")
    md.append("")
    md.append("PlantUML sources are included for C1–C4 in this folder. Render them with PlantUML or integrate in your docs pipeline.")
    md.append("")
    md.append("Files:")
    md.append("- C1: C1.puml")
    md.append("- C2: C2.puml")
    md.append("- C3: C3.puml")
    md.append("- C4 (notes): C4.puml")
    md.append("")
    md.append("## Mind Map")
    md.append("")
    md.append("Mermaid mind map source:")
    md.append("")
    md.append(mindmap_mermaid)
    md.append("")
    (out_dir / "README.md").write_text("\n".join(md), encoding="utf-8")

# -----------------------------
# Project summarization helpers
# -----------------------------
def summarize_tree(tree: List[Dict]) -> Tuple[str, List[str]]:
    files = [t["path"] for t in tree if t.get("type") == "blob"]
    dirs = [t["path"] for t in tree if t.get("type") == "tree"]
    langs = set()
    for f in files:
        ext = Path(f).suffix.lower()
        if ext:
            langs.add(ext)
    summary = f"Found {len(files)} files and {len(dirs)} directories. Common extensions: {', '.join(sorted(list(langs))[:12])}."
    return summary, files

def sample_files_for_llm(files: List[str], limit: int = 40) -> List[str]:
    # Prioritize key files
    priority = []
    patterns = [
        r"(^|/)requirements\\.txt$", r"(^|/)pyproject\\.toml$", r"(^|/)poetry\\.lock$",
        r"(^|/)package\\.json$", r"(^|/)build\\.gradle(\\.kts)?$", r"(^|/)pom\\.xml$",
        r"(^|/)Dockerfile$", r"(^|/)docker-compose\\.ya?ml$", r"(^|/).*\\.ya?ml$",
        r"(^|/)Makefile$", r"(^|/).*settings\\.py$", r"(^|/)main\\.(py|js|ts|go|java)$",
        r"(^|/)app\\.(py|js|ts)$", r"(^|/).*init\\.py$", r"(^|/).*routes?\\.py$",
        r"(^|/).*controller.*\\.(py|js|ts)$", r"(^|/).*service.*\\.(py|js|ts)$",
        r"(^|/).*config.*\\.(py|js|ts|yaml|yml)$"
    ]
    for p in patterns:
        for f in files:
            if re.search(p, f, flags=re.IGNORECASE):
                priority.append(f)
    # fill remainder with readable text files
    remainder = [f for f in files if f not in priority and is_text_file(f)]
    selected = list(dict.fromkeys(priority + remainder))[:limit]
    return selected

# -----------------------------
# Main
# -----------------------------
def main():
    ensure_env()
    repo = GitLabRepo(GITLAB_URL, GITLAB_TOKEN, GITLAB_PROJECT)
    branch = repo.get_default_branch()
    tree = repo.walk_tree(branch)
    project_summary, files = summarize_tree(tree)

    # Select subset of files for analysis
    selected = sample_files_for_llm(files, limit=40)

    # Pull contents
    contents: Dict[str, str] = {}
    for path in selected:
        if not is_text_file(path):
            continue
        txt = repo.get_file(path, branch)
        if txt:
            contents[path] = txt

    # Analyze via Azure OpenAI Responses API
    az = AzureOpenAIAnalyzer(AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY, AZURE_OPENAI_DEPLOYMENT, AZURE_OPENAI_API_VERSION)
    analysis = az.analyze(project_summary=f"Branch: {branch}. {project_summary}", sampled_files=contents)

    # Emit diagrams
    c4_txts = emit_c4_plantuml(
        c1=analysis.get("c1", ""),
        c2=analysis.get("c2", ""),
        c3=analysis.get("c3", ""),
        c4=analysis.get("c4", "")
    )
    mindmap = analysis.get("mindmap", {"root": "Project", "branches": [], "edges": []})
    mindmap_mermaid = emit_mermaid_mindmap(
        root=mindmap.get("root", "Project"),
        branches=mindmap.get("branches", []),
        edges=mindmap.get("edges", []),
    )

    # Write report
    pname = repo.project.path_with_namespace
    write_markdown_report(OUTPUT_DIR, pname, analysis.get("narrative", ""), c4_txts, mindmap_mermaid)
    print(f"Report and diagram sources written to: {OUTPUT_DIR.resolve()}")

if __name__ == "__main__":
    main()