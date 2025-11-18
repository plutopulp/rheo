"""CLI commands.

Note: Currently using flat command structure (single commands registered directly).
When adding a second command group (e.g., 'config', 'queue', 'history'), consider
migrating to sub-app pattern similar to clockwork-canvas:
  - Create apps/ subdirectory for command groups
  - Use app.add_typer() to attach sub-apps
  - See clockwork-canvas/cli for reference implementation
"""

from .download import download

__all__ = ["download"]
