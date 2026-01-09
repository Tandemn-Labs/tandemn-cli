# tandemn_cli/__main__.py
"""
Entry point for tandemn-cli.
- No args → Launch TUI
- Subcommand → Run CLI command
"""

import click
import sys

@click.group(invoke_without_command=True)
@click.pass_context
def main(ctx):
    """
    CLI 
    Run without arguments to launch the TUI
    Run with a subcommand to run a CLI command
    """
    if ctx.invoked_subcommand is None:
        # no subcommand, laumch TUI
        from tui.app import TandemnCLIApp
        TandemnCLIApp().run()

# from tandemn_cli.cli.commands import submit, upload, jobs

# main.add_command(submit)
# main.add_command(upload)
# main.add_command(jobs)

if __name__ == "__main__":
    main()