"""Smoke tests for the hmm-studio CLI."""

from __future__ import annotations

from typer.testing import CliRunner

from hmm_studio.cli import app


def test_cli_help():
    runner = CliRunner()
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "serve" in result.stdout.lower()


def test_cli_serve_help():
    runner = CliRunner()
    result = runner.invoke(app, ["serve", "--help"])
    assert result.exit_code == 0
    assert "host" in result.stdout.lower()
    assert "port" in result.stdout.lower()
