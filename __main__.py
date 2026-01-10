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
    Common Options (see --help for details):
    --task: [required] Task type (batched_inference, online_serving, embeddings, image_generation)
    
    --model: [required] Huggingface model name
    
    --file: Input file (for batched inference)
    
    --engine: Engine: vllm, sglang, diffusers, xDIT
    
    --description: Optional job description
    
    --priority: low / normal / high / urgent (default: auto)
    
    --sku: Preferred GPU (e.g. H100, A100)
    
    --deadline: Deadline/SLO (hrs, for batched_inference)
    
    --slo-mode: offline / online
    
    --speculative-decode, --pd-disaggregation: (flags, advanced text engine options)
    
    [vLLM Specific Configuration] --max-model-len / --max-num-seqs / --max-batched-tokens / --trust-remote-code / --tokenizer / --tokenizer-mode / --kv-cache-dtype / --config-format / --limit-mm
    
    [Speculative Configuration] --speculative-method / --num-spec-tokens / --draft-model / --prompt-lookup-max
    
    --dry-run: Validate config without submitting

    Run without arguments to launch the TUI (Example: tandemn).
    """
    if ctx.invoked_subcommand is None:
        # no subcommand, laumch TUI
        from tui.app import TandemnCLIApp
        TandemnCLIApp().run()

# from tandemn_cli.cli.commands import submit, upload, jobs
from cli.commands import submit
main.add_command(submit)
# main.add_command(upload)
# main.add_command(jobs)

if __name__ == "__main__":
    main()