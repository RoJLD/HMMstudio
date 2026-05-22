"""hmm-studio CLI: `hmm-studio serve` to launch the web UI."""

from __future__ import annotations

import typer
import uvicorn

app = typer.Typer(help="hmm-studio: web UI for hmm-core.")


@app.command()
def serve(
    host: str = typer.Option("127.0.0.1", help="Bind host. Default localhost-only."),
    port: int = typer.Option(8000, help="Port to bind."),
    reload: bool = typer.Option(False, "--reload", help="Auto-reload on code changes (dev only)."),
) -> None:
    """Launch the hmm-studio web server."""
    if reload:
        uvicorn.run(
            "hmm_studio.server.app:create_app",
            host=host,
            port=port,
            reload=True,
            factory=True,
        )
    else:
        from hmm_studio.server.app import create_app

        uvicorn.run(create_app(), host=host, port=port)


if __name__ == "__main__":
    app()
