"""`dl-qa` CLI entrypoint."""

from __future__ import annotations

import sys
from pathlib import Path

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
@click.option("--target-path", default=None, type=click.Path(exists=True, file_okay=False, path_type=Path),
              help="Override the target repo path from the YAML (useful in CI).")
@click.option("--max-revisions", default=3, type=int, show_default=True)
def run(target: str, goal: str, target_path: Path | None, max_revisions: int) -> None:
    """Run the full Profiler -> Planner -> TestWriter -> Critic pipeline."""
    settings = Settings.load()
    target_cfg = TargetConfig.load(target, override_path=target_path)

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
def metrics() -> None:
    """Aggregate observability across every run under runs/."""
    from digital_land_qa_agent.metrics import collect

    settings = Settings.load()
    agg = collect(settings.runs_dir)

    if agg.total_runs == 0:
        console.print(f"[yellow]No runs found under {settings.runs_dir}[/]")
        return

    summary = Table(title=f"Pipeline metrics ({agg.total_runs} runs)")
    summary.add_column("Metric")
    summary.add_column("Value", justify="right")
    summary.add_row("Approved", str(agg.approved))
    summary.add_row("Needs review", str(agg.needs_review))
    summary.add_row("Incomplete", str(agg.incomplete))
    summary.add_row("Approval rate", f"{agg.approval_rate:.0%}")
    summary.add_row("Avg revisions / run", f"{agg.avg_revisions:.2f}")
    summary.add_row("Total input tokens", f"{agg.total_input_tokens:,}")
    summary.add_row("Total output tokens", f"{agg.total_output_tokens:,}")
    summary.add_row("Mode counts", ", ".join(f"{k}={v}" for k, v in sorted(agg.mode_counts.items())))
    console.print(summary)

    detail = Table(title="Per-run")
    detail.add_column("Run")
    detail.add_column("Mode")
    detail.add_column("Goal", overflow="fold")
    detail.add_column("Revs", justify="right")
    detail.add_column("In", justify="right")
    detail.add_column("Out", justify="right")
    detail.add_column("Verdict")
    for r in agg.per_run[-20:]:  # show only the most recent 20
        verdict = "approved" if r.approved else ("needs review" if r.approved is False else "incomplete")
        detail.add_row(
            r.run_id,
            r.llm_mode or "?",
            r.goal or "",
            str(r.revisions),
            f"{r.input_tokens:,}",
            f"{r.output_tokens:,}",
            verdict,
        )
    console.print(detail)


@cli.command()
@click.option("--target", required=True)
@click.option("--target-path", default=None, type=click.Path(exists=True, file_okay=False, path_type=Path))
def profile(target: str, target_path: Path | None) -> None:
    """Run just the Profiler stage and print the RepoProfile."""
    from digital_land_qa_agent.agents import ProfilerAgent
    from digital_land_qa_agent.llm import build_client
    from digital_land_qa_agent.runs import new_run

    settings = Settings.load()
    target_cfg = TargetConfig.load(target, override_path=target_path)
    run = new_run(settings.runs_dir, target_cfg.name)
    llm = build_client(settings.model)
    agent = ProfilerAgent(llm=llm, run=run)
    profile = agent.profile(target_cfg)

    console.print_json(data=profile)
    console.print(f"\n[dim]Audit log:[/] {run.audit_log}")


@cli.command("diff")
@click.option("--target", required=True, help="Target name (matches config/targets/<name>.yaml).")
@click.option("--base", default=None, help="Base git ref. Run pipeline against files changed since this ref.")
@click.option("--head", default="HEAD", show_default=True)
@click.option("--target-path", default=None, type=click.Path(exists=True, file_okay=False, path_type=Path),
              help="Override target repo path (defaults to YAML value).")
@click.option("--files", "explicit_files", multiple=True, type=click.Path(path_type=Path),
              help="Explicit source files to test (repeatable). Bypasses git diff.")
@click.option("--max-files", default=10, type=int, show_default=True,
              help="Cost cap. Refuse to run if more files would be processed.")
def diff_cmd(
    target: str,
    base: str | None,
    head: str,
    target_path: Path | None,
    explicit_files: tuple[Path, ...],
    max_files: int,
) -> None:
    """Run the pipeline against every source file changed between two refs."""
    from digital_land_qa_agent.diff_runner import run_diff

    settings = Settings.load()
    target_cfg = TargetConfig.load(target, override_path=target_path)

    if not base and not explicit_files:
        console.print("[red]Provide either --base <ref> or --files <path>[/]")
        sys.exit(2)

    console.print(
        Panel.fit(
            f"[bold]target[/] {target_cfg.name}\n"
            f"[bold]path[/] {target_cfg.path}\n"
            f"[bold]base[/] {base or '(explicit files)'}\n"
            f"[bold]head[/] {head}\n"
            f"[bold]max_files[/] {max_files}",
            title="dl-qa diff",
        )
    )

    try:
        summary = run_diff(
            target=target_cfg,
            settings=settings,
            base=base,
            head=head,
            explicit_files=list(explicit_files) if explicit_files else None,
            max_files=max_files,
        )
    except RuntimeError as e:
        console.print(f"[red]{e}[/]")
        sys.exit(2)

    console.rule(f"Results — {summary.approved} approved / {summary.needs_review} need review")
    if not summary.results:
        console.print(
            f"[yellow]No relevant source files to test.[/]"
            f" (saw {summary.files_seen}, skipped {summary.files_skipped} non-source)"
        )
        return

    table = Table(title="Per-file pipeline results")
    table.add_column("Module")
    table.add_column("Verdict")
    table.add_column("Staged file", overflow="fold")
    for r in summary.results:
        verdict = "[green]APPROVED[/]" if r.approved else "[yellow]needs review[/]"
        table.add_row(r.plan.get("target_module", "?"), verdict, str(r.staged_path))
    console.print(table)

    if summary.needs_review:
        sys.exit(1)


if __name__ == "__main__":
    cli()
