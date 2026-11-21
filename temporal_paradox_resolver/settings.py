"""Local settings, kept in a ``.env`` file that git ignores.

This is how the Gemini key gets into the app without ever being written into
the code: you paste it into the app's Settings panel (or into ``.env`` by
hand), it is saved to ``.env`` on your own computer, and it is loaded into the
environment when the app or the CLI starts.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, Optional

ENV_FILE = Path(os.getenv("TPR_ENV_FILE", ".env"))
KEY_NAME = "GEMINI_API_KEY"


def read_env(path: Optional[Path] = None) -> Dict[str, str]:
    path = Path(path or ENV_FILE)
    values: Dict[str, str] = {}
    if not path.exists():
        return values
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        values[name.strip()] = value.strip().strip('"').strip("'")
    return values


def load_env(path: Optional[Path] = None) -> None:
    """Copy values from ``.env`` into the environment, without overriding real env vars."""
    for name, value in read_env(path).items():
        if value and not os.environ.get(name):
            os.environ[name] = value


def _write(name: str, value: Optional[str], path: Optional[Path] = None) -> None:
    path = Path(path or ENV_FILE)
    lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    kept = [l for l in lines if l.split("=", 1)[0].strip() != name]
    if value:
        kept.append(f"{name}={value}")
    path.write_text("\n".join(kept) + ("\n" if kept else ""), encoding="utf-8")
    try:
        path.chmod(0o600)  # readable only by you
    except OSError:
        pass


def save_key(key: str, path: Optional[Path] = None) -> None:
    key = key.strip()
    if not key:
        raise ValueError("The key is empty.")
    _write(KEY_NAME, key, path)
    os.environ[KEY_NAME] = key


def clear_key(path: Optional[Path] = None) -> None:
    _write(KEY_NAME, None, path)
    os.environ.pop(KEY_NAME, None)


def masked_key() -> str:
    key = os.environ.get(KEY_NAME, "")
    return f"••••{key[-4:]}" if len(key) > 8 else ("••••" if key else "")
