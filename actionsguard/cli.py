"""Command-line interface for ActionsGuard."""

import sys
import logging
import json
from pathlib import Path
from typing import Optional, List
from datetime import datetime

import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

from actionsguard.__version__ import __version__
from actionsguard.scanner import Scanner
from actionsguard.scorecard_runner import ScorecardRunner
from actionsguard.models import ScanResult, ScanSummary, RiskLevel
from actionsguard.utils.config import Config
from actionsguard.utils.logging import setup_logger
from actionsguard.reporters import JSONReporter, HTMLReporter, CSVReporter, MarkdownReporter


console = Console()
logger = None


@click.group()
@click.version_option(version=__version__, prog_name="actionsguard")
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Enable verbose logging"
)
@click.pass_context
def cli(ctx, verbose):
    """ActionsGuard - GitHub Actions Security Scanner."""
    global logger
    logger = setup_logger(verbose=verbose)
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose


@cli.command()
@click.option(
    "--repo",
    "-r",
    help="Scan a single repository (format: owner/repo)"
)
@click.option(
    "--org",
    "-o",
    help="Scan all repositories in an organization"
)
@click.option(
    "--exclude",
    help="Comma-separated list of repositories to exclude"
)
@click.option(
    "--only",
    help="Comma-separated list of repositories to scan (all others excluded)"
)
@click.option(
    "--output",
    "-d",
    default="./reports",
    help="Output directory for reports (default: ./reports)"
)
@click.option(
    "--format",
    "-f",
    "formats",
    default="json,html,csv,markdown",
    help="Report formats (comma-separated: json,html,csv,markdown)"
)
@click.option(
    "--checks",
    "-c",
    help="Scorecard checks to run (comma-separated, default: Dangerous-Workflow,Token-Permissions,Pinned-Dependencies)"
)
@click.option(
    "--all-checks",
    is_flag=True,
    help="Run all Scorecard checks"
)
@click.option(
    "--fail-on-critical",
    is_flag=True,
    help="Exit with error code if critical issues found"
)
@click.option(
    "--token",
    "-t",
    help="GitHub token (or set GITHUB_TOKEN env var)"
)
@click.option(
    "--parallel",
    "-p",
    default=5,
    type=int,
    help="Number of parallel scans (default: 5)"
)
@click.pass_context
def scan(
    ctx,
    repo: Optional[str],
    org: Optional[str],
    exclude: Optional[str],
    only: Optional[str],
    output: str,
    formats: str,
    checks: Optional[str],
    all_checks: bool,
    fail_on_critical: bool,
    token: Optional[str],
    parallel: int
):
    """
    Scan GitHub Actions workflows for security issues.

    Examples:

      # Scan a single repository
      actionsguard scan --repo kubernetes/kubernetes

      # Scan an entire organization
      actionsguard scan --org my-org

      # Scan with filters
      actionsguard scan --org my-org --exclude repo1,repo2

      # Custom output and formats
      actionsguard scan --org my-org --output ./my-reports --format json,html
    """
    try:
        # Validate input
        if not repo and not org:
            console.print("[red]Error: Must specify either --repo or --org[/red]")
            sys.exit(2)

        if repo and org:
            console.print("[red]Error: Cannot specify both --repo and --org[/red]")
            sys.exit(2)

        # Build configuration
        # Only pass github_token if explicitly provided via --token flag
        # Otherwise, Config will read from GITHUB_TOKEN env var
        config_kwargs = {
            "output_dir": output,
            "formats": formats.split(","),
            "checks": checks.split(",") if checks else Config().checks,
            "fail_on_critical": fail_on_critical,
            "verbose": ctx.obj["verbose"],
            "parallel_scans": parallel,
        }

        if token:
            config_kwargs["github_token"] = token

        config = Config(**config_kwargs)

        if all_checks:
            config.checks = ["all"]

        # Validate token
        try:
            config.validate()
        except ValueError as e:
            console.print(f"[red]Error: {e}[/red]")
            sys.exit(2)

        # Create scanner
        scanner = Scanner(config)

        # Run scan
        console.print("\n[bold blue]🛡️  ActionsGuard Security Scanner[/bold blue]\n")

        if repo:
            console.print(f"[bold]Scanning repository:[/bold] {repo}\n")
            result = scanner.scan_single_repository(repo)
            from actionsguard.models import ScanSummary
            summary = ScanSummary.from_results([result])
        else:
            exclude_list = exclude.split(",") if exclude else []
            only_list = only.split(",") if only else []

            console.print(f"[bold]Scanning organization:[/bold] {org}")
            if exclude_list:
                console.print(f"[dim]Excluding: {', '.join(exclude_list)}[/dim]")
            if only_list:
                console.print(f"[dim]Only scanning: {', '.join(only_list)}[/dim]")
            console.print()

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                console=console,
            ) as progress:
                task = progress.add_task(
                    "[cyan]Scanning repositories...",
                    total=None
                )

                summary = scanner.scan_organization(
                    org_name=org,
                    exclude=exclude_list if exclude_list else None,
                    only=only_list if only_list else None,
                )

                progress.update(task, completed=True)

        # Display summary
        _display_summary(summary)

        # Generate reports
        console.print("\n[bold]Generating reports...[/bold]\n")
        _generate_reports(summary, config)

        # Check for critical issues
        if config.fail_on_critical:
            has_critical = any(r.has_critical_issues() for r in summary.results)
            if has_critical:
                console.print("\n[red]❌ Critical security issues found![/red]")
                sys.exit(1)

        console.print("\n[green]✅ Scan complete![/green]\n")

    except KeyboardInterrupt:
        console.print("\n[yellow]Scan cancelled by user[/yellow]")
        sys.exit(130)

    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]")
        if ctx.obj["verbose"]:
            console.print_exception()
        sys.exit(2)


def _display_summary(summary):
    """Display scan summary."""
    console.print("\n[bold]📊 Scan Summary[/bold]\n")

    console.print(f"  Total Repositories: {summary.total_repos}")
    console.print(f"  Successful Scans:   {summary.successful_scans}")
    console.print(f"  Failed Scans:       {summary.failed_scans}")
    console.print(f"  Average Score:      {summary.average_score:.1f}/10.0")
    if summary.scan_duration:
        console.print(f"  Scan Duration:      {summary.scan_duration:.1f}s")

    console.print("\n[bold]Issue Breakdown:[/bold]")
    console.print(f"  🔴 Critical: {summary.critical_count}")
    console.print(f"  🟠 High:     {summary.high_count}")
    console.print(f"  🟡 Medium:   {summary.medium_count}")
    console.print(f"  🟢 Low:      {summary.low_count}")


def _generate_reports(summary, config):
    """Generate all requested report formats."""
    reporters = {
        "json": JSONReporter,
        "html": HTMLReporter,
        "csv": CSVReporter,
        "markdown": MarkdownReporter,
    }

    report_files = []

    for format_name in config.formats:
        format_name = format_name.strip().lower()
        if format_name not in reporters:
            console.print(f"[yellow]Warning: Unknown format '{format_name}', skipping[/yellow]")
            continue

        reporter_class = reporters[format_name]
        reporter = reporter_class(config.output_dir)

        try:
            report_path = reporter.generate_report(summary)
            report_files.append((format_name.upper(), report_path))
            console.print(f"  ✓ {format_name.upper()}: {report_path}")
        except Exception as e:
            console.print(f"  ✗ {format_name.upper()}: Failed ({e})")
            logger.error(f"Failed to generate {format_name} report: {e}")

    return report_files


@cli.command()
@click.argument('scorecard_json', type=click.Path(exists=True))
@click.option(
    "--output",
    "-o",
    default="./reports",
    help="Output directory for reports (default: ./reports)"
)
@click.option(
    "--format",
    "-f",
    "formats",
    default="html,markdown,csv",
    help="Report formats (comma-separated: json,html,csv,markdown)"
)
@click.option(
    "--repo-name",
    help="Repository name (auto-detected from JSON if not provided)"
)
@click.pass_context
def import_scorecard(ctx, scorecard_json, output, formats, repo_name):
    """
    Import Scorecard JSON report and generate beautiful reports.

    This command takes an existing Scorecard JSON file and generates
    user-friendly HTML, Markdown, and CSV reports.

    Examples:

      # Run Scorecard yourself, then import
      scorecard --repo=github.com/kubernetes/kubernetes --format=json > scorecard.json
      actionsguard import scorecard.json

      # Specify output directory
      actionsguard import scorecard.json --output ./my-reports

      # Generate only HTML and Markdown
      actionsguard import scorecard.json --format html,markdown
    """
    try:
        console.print("\n[bold blue]📊 ActionsGuard Report Generator[/bold blue]\n")

        # Read Scorecard JSON
        console.print(f"[cyan]Reading Scorecard report:[/cyan] {scorecard_json}")
        with open(scorecard_json, 'r') as f:
            scorecard_data = json.load(f)

        # Parse the data (don't check for scorecard installation)
        scorecard_runner = ScorecardRunner(check_install=False)
        checks = scorecard_runner.parse_results(scorecard_data)
        score = scorecard_runner.get_overall_score(scorecard_data)
        metadata = scorecard_runner.get_metadata(scorecard_data)

        # Get repo name
        if not repo_name:
            repo_name = scorecard_data.get('repo', {}).get('name', 'unknown-repo')
            repo_name = repo_name.replace('github.com/', '')

        repo_url = f"https://github.com/{repo_name}"

        # Create scan result
        result = ScanResult(
            repo_name=repo_name,
            repo_url=repo_url,
            score=score,
            risk_level=ScanResult.calculate_risk_level(score),
            scan_date=datetime.now(),
            checks=checks,
            metadata=metadata,
        )

        # Create summary
        summary = ScanSummary.from_results([result])

        # Display summary
        console.print(f"\n[bold green]✓[/bold green] Successfully parsed Scorecard data\n")
        _display_summary(summary)

        # Generate reports
        console.print("\n[bold]Generating reports...[/bold]\n")

        config = Config(output_dir=output, formats=formats.split(","))
        _generate_reports(summary, config)

        console.print(f"\n[green]✅ Reports generated in:[/green] {output}\n")

    except json.JSONDecodeError as e:
        console.print(f"[red]Error: Invalid JSON file - {e}[/red]")
        sys.exit(2)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        if ctx.obj.get("verbose"):
            console.print_exception()
        sys.exit(2)


if __name__ == "__main__":
    cli(obj={})
