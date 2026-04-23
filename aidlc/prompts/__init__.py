"""Prompt template loader.

Templates live as sibling ``.md`` files. We load them via
``importlib.resources`` so they ship correctly when the package is installed
as a wheel (see ``pyproject.toml``'s force-include rule).
"""

from __future__ import annotations

from importlib import resources
from string import Template


def load(name: str) -> str:
    """Return the raw template text for ``name``, e.g. ``'idea_to_spec'``."""
    return resources.files(__name__).joinpath(f"{name}.md").read_text(encoding="utf-8")


def render(name: str, **kwargs: str) -> str:
    """Render a template using ``string.Template`` ($var) substitution.

    We use ``$var`` rather than ``{var}`` because the prompts contain JSON
    examples with ``{`` characters; safer to use the simpler syntax.
    """
    return Template(load(name)).safe_substitute(**kwargs)
