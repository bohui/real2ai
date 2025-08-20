"""
Normalize YAML frontmatter for all prompt fragments under backend/app/prompts/fragments
to align with the folder-structure-driven schema. Uses planning_certificates.md as
the reference: include keys {category, context{state, contract_type, purchase_method,
use_category, user_experience, analysis_depth}, priority, version, description, tags}.

Rules:
- Derive context defaults from folder path where possible
  - state_requirements/<STATE>/... -> context.state = <STATE>
  - contract_types/(purchase|lease|option)/... -> context.contract_type mapped to
    purchase_agreement | lease_agreement | option_to_purchase
  - user_experience/(novice|intermediate|expert)/... -> context.user_experience
  - analysis_depth/(comprehensive|quick|focused)/... -> context.analysis_depth
  - use_category/(residential|commercial|industrial|retail)/... -> context.use_category
- Ensure all context keys exist; default to "*" when not derived
- For state_requirements group, force wildcard for non-state keys (matches reference)
- Remove deprecated fields (group, domain)
- Normalize contract_type short names (purchase -> purchase_agreement, etc.)
- If a context value is a comma-separated string, transform to a list of strings
- Preserve body content unchanged; only frontmatter is updated
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, Tuple

import yaml


FRAGMENTS_DIR = (
    Path(__file__).resolve().parents[1] / "backend" / "app" / "prompts" / "fragments"
)


def parse_frontmatter(text: str) -> Tuple[Dict[str, Any], str]:
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            fm = parts[1].strip()
            body = parts[2].lstrip("\n")
            try:
                meta = yaml.safe_load(fm) or {}
            except Exception:
                meta = {}
            if not isinstance(meta, dict):
                meta = {}
            return meta, body
    return {}, text


def dump_frontmatter(meta: Dict[str, Any]) -> str:
    return yaml.safe_dump(meta, allow_unicode=True, sort_keys=False).strip()


def derive_description(body: str, path: Path) -> str:
    for line in body.splitlines():
        s = line.lstrip()
        if s.startswith("### "):
            return s.lstrip("#").strip()
        if s.startswith("# "):
            return s.lstrip("#").strip()
    return path.stem.replace("_", " ").title()


CONTRACT_TYPE_MAP = {
    "purchase": "purchase_agreement",
    "lease": "lease_agreement",
    "option": "option_to_purchase",
}


def normalize_context_values(ctx: Dict[str, Any]) -> Dict[str, Any]:
    normalized: Dict[str, Any] = {}
    for key, value in ctx.items():
        # Convert comma-separated strings to list of strings
        if isinstance(value, str) and "," in value:
            items = [v.strip() for v in value.split(",") if v.strip()]
            normalized[key] = items if items else "*"
        else:
            normalized[key] = value
    # Normalize contract_type short names inside strings
    v = normalized.get("contract_type")
    if isinstance(v, str) and v in CONTRACT_TYPE_MAP:
        normalized["contract_type"] = CONTRACT_TYPE_MAP[v]
    # Normalize contract_type lists
    if isinstance(v, list):
        normalized["contract_type"] = [CONTRACT_TYPE_MAP.get(x, x) for x in v]
    return normalized


def process_fragment_file(fp: Path) -> bool:
    text = fp.read_text(encoding="utf-8")
    meta, body = parse_frontmatter(text)

    rel = fp.relative_to(FRAGMENTS_DIR)
    parts = list(rel.parts)
    group = parts[0] if parts else "shared"

    # Start from existing metadata dict
    new_meta: Dict[str, Any] = dict(meta)

    # Remove deprecated fields
    for deprecated in ("group", "domain"):
        new_meta.pop(deprecated, None)

    # Ensure category
    if not new_meta.get("category"):
        new_meta["category"] = group

    # Normalize/build context
    raw_ctx = new_meta.get("context")
    ctx: Dict[str, Any] = raw_ctx if isinstance(raw_ctx, dict) else {}

    # Migrate legacy top-level state -> context.state
    if isinstance(new_meta.get("state"), str):
        ctx["state"] = new_meta.pop("state")

    # Derive from path
    if group == "state_requirements" and len(parts) >= 2:
        state_dir = parts[1]
        if not ctx.get("state") or ctx.get("state") == "*":
            ctx["state"] = state_dir

    if group == "contract_types" and len(parts) >= 2:
        sub = parts[1]
        if sub in CONTRACT_TYPE_MAP:
            v = ctx.get("contract_type")
            if v in (None, "*", ""):
                ctx["contract_type"] = CONTRACT_TYPE_MAP[sub]
            elif isinstance(v, str) and v in CONTRACT_TYPE_MAP:
                ctx["contract_type"] = CONTRACT_TYPE_MAP[v]

    if group == "user_experience" and len(parts) >= 2:
        ux = parts[1]
        if ctx.get("user_experience") in (None, "*", ""):
            ctx["user_experience"] = ux

    if group == "analysis_depth" and len(parts) >= 2:
        depth = parts[1]
        if ctx.get("analysis_depth") in (None, "*", ""):
            ctx["analysis_depth"] = depth

    if group == "use_category" and len(parts) >= 2:
        uc = parts[1]
        if ctx.get("use_category") in (None, "*", ""):
            ctx["use_category"] = uc

    # Specific rule: for state_requirements, force wildcard for non-state keys to match reference
    if group == "state_requirements":
        for k in (
            "contract_type",
            "purchase_method",
            "use_category",
            "user_experience",
            "analysis_depth",
        ):
            ctx[k] = "*"

    # Normalize context values (comma -> list, short contract_type -> enum value)
    ctx = normalize_context_values(ctx)

    # Ensure expected context keys exist with wildcard defaults
    for key in [
        "state",
        "contract_type",
        "purchase_method",
        "use_category",
        "user_experience",
        "analysis_depth",
    ]:
        if key not in ctx or ctx[key] in (None, ""):
            ctx[key] = "*"

    new_meta["context"] = ctx

    # Ensure priority
    if not isinstance(new_meta.get("priority"), int):
        new_meta["priority"] = 80 if group == "state_requirements" else 70

    # Ensure version
    if not isinstance(new_meta.get("version"), str):
        new_meta["version"] = "1.0.0"

    # Ensure description
    if (
        not isinstance(new_meta.get("description"), str)
        or not new_meta["description"].strip()
    ):
        new_meta["description"] = derive_description(body, fp)

    # Ensure tags list
    tags = new_meta.get("tags")
    if not isinstance(tags, list) or not all(isinstance(t, str) for t in tags):
        derived = [p.lower() for p in parts[:-1]]
        name_tags = [t for t in re.split(r"[-_\s]+", fp.stem.lower()) if t]
        new_meta["tags"] = list(dict.fromkeys(derived + name_tags))

    # Reorder keys for consistency
    ordered_keys = ["category", "context", "priority", "version", "description", "tags"]
    ordered: Dict[str, Any] = {k: new_meta[k] for k in ordered_keys if k in new_meta}
    for k, v in new_meta.items():
        if k not in ordered:
            ordered[k] = v

    fm_text = dump_frontmatter(ordered)
    new_text = "---\n" + fm_text + "\n---\n\n" + body

    if new_text != text:
        fp.write_text(new_text, encoding="utf-8")
        return True
    return False


def main() -> None:
    changed = []
    for fp in FRAGMENTS_DIR.rglob("*.md"):
        try:
            if process_fragment_file(fp):
                changed.append(str(fp.relative_to(FRAGMENTS_DIR)))
        except Exception as e:
            print(f"! Failed to process {fp}: {e}")
    print({"changed_count": len(changed), "changed": changed})


if __name__ == "__main__":
    main()
