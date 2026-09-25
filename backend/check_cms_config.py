"""
Validates admin/config.yml against the parts of Decap's schema that have
actually bitten this repo.

Decap validates its config in the browser. A value it rejects does not
degrade — it replaces the whole admin with "Error loading the CMS
configuration", so /admin is simply down until someone notices. That has
happened twice: once from a mangled YAML header, and once from putting
"image" in a markdown widget's `buttons`, where it is not allowed (images
are an editor component, not a toolbar button).

Both would have been caught here. This checks the constraints that are
cheap to encode and expensive to get wrong; it is not a full port of
Decap's schema.

Run manually:
    python3 backend/check_cms_config.py

It also runs in .github/workflows/render-content.yml on any push touching
admin/**, so a bad config fails CI instead of reaching the browser.
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "admin" / "config.yml"

# https://decapcms.org/docs/widgets/#markdown — formatting controls only.
# "image" belongs in editor_components, not here.
MARKDOWN_BUTTONS = {
    "bold", "italic", "code", "link", "quote",
    "bulleted-list", "numbered-list",
    "heading-one", "heading-two", "heading-three",
    "heading-four", "heading-five", "heading-six",
}

# Built-in components. Anything else must be registered with
# CMS.registerEditorComponent in admin/index.html.
EDITOR_COMPONENTS = {"image", "code-block"}

WIDGETS = {
    "boolean", "code", "color", "datetime", "file", "hidden", "image",
    "list", "map", "markdown", "number", "object", "relation", "select",
    "string", "text", "uuid",
}


def walk_fields(fields, where, errors):
    """Checks a field list, recursing into list/object children."""
    for index, field in enumerate(fields or []):
        if not isinstance(field, dict):
            errors.append(f"{where}[{index}] is not a mapping")
            continue

        path = f"{where}[{index}] ({field.get('name', 'unnamed')})"
        widget = field.get("widget")

        if widget is None:
            errors.append(f"{path}: no widget")
        elif widget not in WIDGETS:
            errors.append(f"{path}: unknown widget {widget!r}")

        if widget == "markdown":
            for button in field.get("buttons") or []:
                if button not in MARKDOWN_BUTTONS:
                    errors.append(
                        f"{path}: {button!r} is not a valid markdown button. "
                        f"Images and code blocks go in editor_components."
                    )
            for component in field.get("editor_components") or []:
                if component not in EDITOR_COMPONENTS:
                    errors.append(
                        f"{path}: {component!r} is not a built-in editor "
                        f"component; register it in admin/index.html or remove it"
                    )

        # A datetime that hides the clock has to pin `format` too, or Decap
        # writes a full timestamp back into the file anyway.
        if widget == "datetime" and field.get("time_format") is False:
            if not field.get("format"):
                errors.append(f"{path}: time_format is off but no format is set")

        for key in ("fields", "field"):
            child = field.get(key)
            if isinstance(child, dict):
                walk_fields([child], f"{path}.{key}", errors)
            elif isinstance(child, list):
                walk_fields(child, f"{path}.{key}", errors)


def main() -> int:
    if not CONFIG_PATH.exists():
        print(f"No {CONFIG_PATH}")
        return 1

    try:
        config = yaml.safe_load(CONFIG_PATH.read_text())
    except yaml.YAMLError as exc:
        print(f"FAIL — {CONFIG_PATH.name} is not valid YAML:\n  {exc}")
        return 1

    errors: list[str] = []
    for key in ("backend", "media_folder", "collections"):
        if key not in config:
            errors.append(f"missing top-level key {key!r}")

    collections = config.get("collections") or []
    if not collections:
        errors.append("no collections defined")

    checked = 0
    for collection in collections:
        name = collection.get("name", "unnamed")
        if "files" in collection:
            for entry in collection["files"]:
                walk_fields(entry.get("fields"), f"{name}/{entry.get('name')}", errors)
                checked += len(entry.get("fields") or [])
        else:
            walk_fields(collection.get("fields"), name, errors)
            checked += len(collection.get("fields") or [])

    if errors:
        print(f"FAIL — {len(errors)} problem(s) in {CONFIG_PATH.name}:")
        for error in errors:
            print(f"  - {error}")
        return 1

    print(f"OK — {CONFIG_PATH.name} valid ({len(collections)} collections, {checked} fields checked).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
