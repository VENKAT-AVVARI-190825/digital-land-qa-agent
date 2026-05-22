"""`dl-qa` CLI entrypoint."""

from __future__ import annotations

import sys

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from digital_land_qa_agent.config import Settings, TargetConfig, list_targets
from digital_land_qa_agent.orchestrator import run_pipeline

console = Console()


@click.group()
def cli() -> None:
    """digital-land-qa-agent — multi-agent QA automation."""


@cli.command("list-targets")
def list_targets_cmd() -> None:
    """List configured target repos."""
    names = list_targets()
    if not names:
        console.print("[yellow]No targets configured under config/targets/[/]")
        return
    table = Table(title="Configured targets")
    table.add_column("Name")
    table.add_column("Path")
    for name in names:
        try:
            t = TargetConfig.load(name)
            table.add_row(name, str(t.path))
        except Exception as e:  # pragma: no cover - cli error display
            table.add_row(name, f"[red]error: {e}[/]")
    console.print(table)


@cli.command()
@click.option("--target", required=True, help="Target name (matches config/targets/<name>.yaml).")
@click.option("--goal", required=True, help="What you want the agent to do.")
@click.option("--max-revisions", default=3, type=int, show_default=True)
def run(target: str, goal: str, max_revisions: int) -> None:
    """Run the full Profiler -> Planner -> TestWriter -> Critic pipeline."""
    settings = Settings.load()
    target_cfg = TargetConfig.load(target)

    console.print(
        Panel.fit(
            f"[bold]target[/] {target_cfg.name}\n"
            f"[bold]path[/] {target_cfg.path}\n"
            f"[bold]goal[/] {goal}\n"
            f"[bold]model[/] {settings.model}\n"
            f"[bold]runs_dir[/] {settings.runs_dir}",
            title="dl-qa run",
        )
    )

    result = run_pipeline(target_cfg, goal, settings, max_revisions=max_revisions)

    console.rule("Result")
    console.print(result.summary())
    console.print(f"\n[dim]Audit log:[/] {result.run.audit_log}")
    console.print(f"[dim]Staged tests:[/] {result.run.staged_tests_dir}")

    if not result.approved:
        sys.exit(1)


@cli.command()
@click.option("--target", required=True)
def profile(target: str) -> None:
    """Run just the Profiler stage and print the RepoProfile."""
    from digital_land_qa_agent.agents import ProfilerAgent
    from digital_land_qa_agent.llm import build_client
    from digital_land_qa_agent.runs import new_run

    settings = Settings.load()
    target_cfg = TargetConfig.load(target)
    run = new_run(settings.runs_dir, target_cfg.name)
    llm = build_client(settings.model)
    agent = ProfilerAgent(llm=llm, run=run)
    profile = agent.profile(target_cfg)

    console.print_json(data=profile)
    console.print(f"\n[dim]Audit log:[/] {run.audit_log}")


if __name__ == "__main__":
    cli()
