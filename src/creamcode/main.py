from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

import click


async def async_main(config: dict | None = None) -> int:
    """Async main entry point"""
    from .app import Application
    
    app = Application(config)
    
    try:
        await app.initialize()
        
        if len(sys.argv) > 1:
            result = await app.run_command(sys.argv[1], {})
            await app.shutdown()
            return result
        else:
            await app.run_interactive()
            await app.shutdown()
            return 0
    except KeyboardInterrupt:
        click.echo("\nInterrupted.")
        await app.shutdown()
        return 130
    except Exception as e:
        logging.error(f"Fatal error: {e}", exc_info=True)
        await app.shutdown()
        return 1


@click.command()
@click.option("--config", "-c", type=click.Path(exists=True), help="Config file path")
@click.option("--debug", is_flag=True, help="Enable debug logging")
@click.option("--version", "-v", is_flag=True, help="Show version")
@click.argument("command", required=False)
def main(config: str | None, debug: bool, version: bool, command: str | None) -> int:
    """creamcode - Lightweight AI coding CLI"""
    
    logging.basicConfig(
        level=logging.DEBUG if debug else logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    if version:
        from .app import Application
        click.echo(f"creamcode {Application.VERSION}")
        return 0
    
    app_config: dict | None = None
    if config:
        import json
        with open(config) as f:
            app_config = json.load(f)
    
    if command:
        sys.argv = [sys.argv[0], command] + sys.argv[2:]
    
    try:
        return asyncio.run(async_main(app_config))
    except KeyboardInterrupt:
        click.echo("\nInterrupted.")
        return 130


if __name__ == "__main__":
    sys.exit(main())
