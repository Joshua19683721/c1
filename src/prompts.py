# -*- coding: utf-8 -*-
"""Loader and renderer for the dsh pipeline prompt templates.

The YAML file is the contract between the specification and the code: the prompt
text lives in dsh_config/read_express_cot_pipelines_elem.yaml and is never
hard-coded in Python. Editing the YAML changes the assistant's voice without
touching the app.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import yaml

__all__ = [
    'Pipeline',
    'Step',
    'DEFAULT_CONFIG_PATH',
    'load_pipelines',
    'get_pipeline',
    'render_prompt',
    'placeholders_in',
    'MISSING',
]

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG_PATH = (
    PROJECT_ROOT / 'dsh_config' / 'read_express_cot_pipelines_elem.yaml'
)

#: {{ variable }}, tolerating whitespace inside the braces.
_PLACEHOLDER_RE = re.compile(r'\{\{\s*([A-Za-z_][A-Za-z0-9_]*)\s*\}\}')

#: A missing value renders as a visible marker. A silently blank slot weakens
#: the prompt in a way that is far harder to notice than an explicit marker.
MISSING = '（未提供）'


@dataclass(frozen=True)
class Step:
    id: str
    prompt_template: str


@dataclass(frozen=True)
class Pipeline:
    name: str
    description: str
    steps: tuple[Step, ...]

    @property
    def first(self) -> Step:
        if not self.steps:
            raise ValueError(f'pipeline {self.name!r} has no steps')
        return self.steps[0]


@lru_cache(maxsize=8)
def _load_cached(path_str: str, mtime: float) -> tuple[Pipeline, ...]:
    data = yaml.safe_load(Path(path_str).read_text(encoding='utf-8')) or {}
    pipelines = []
    for entry in data.get('pipelines', []) or []:
        steps = tuple(
            Step(
                id=raw.get('id', f'step_{i + 1}'),
                prompt_template=raw.get('prompt_template', ''),
            )
            for i, raw in enumerate(entry.get('steps', []) or [])
        )
        pipelines.append(
            Pipeline(
                name=entry.get('name', ''),
                description=entry.get('description', ''),
                steps=steps,
            )
        )
    return tuple(pipelines)


def load_pipelines(path: Path | str | None = None) -> tuple[Pipeline, ...]:
    """Load every pipeline from the YAML config, re-reading it if it changed."""
    config_path = Path(path) if path else DEFAULT_CONFIG_PATH
    if not config_path.exists():
        raise FileNotFoundError(f'pipeline config not found: {config_path}')
    return _load_cached(str(config_path), config_path.stat().st_mtime)


def get_pipeline(name: str, path: Path | str | None = None) -> Pipeline:
    for pipeline in load_pipelines(path):
        if pipeline.name == name:
            return pipeline
    available = ', '.join(p.name for p in load_pipelines(path))
    raise KeyError(f'pipeline {name!r} not found; available: {available}')


def render_prompt(template: str, **values: object) -> str:
    """Fill {{ variable }} placeholders."""

    def substitute(match: re.Match[str]) -> str:
        key = match.group(1)
        value = values.get(key)
        if value is None or (isinstance(value, str) and not value.strip()):
            return MISSING
        return str(value)

    return _PLACEHOLDER_RE.sub(substitute, template).strip()


def placeholders_in(template: str) -> tuple[str, ...]:
    """Names a template expects — used by the app for a wiring preview."""
    seen: list[str] = []
    for key in _PLACEHOLDER_RE.findall(template):
        if key not in seen:
            seen.append(key)
    return tuple(seen)
