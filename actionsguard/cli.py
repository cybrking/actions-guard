"""Command-line interface for ActionsGuard."""

import sys
import logging
import json
from pathlib import Path
from typing import Optional, List
from datetime import datetime

import click
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

from actionsguard.__version__ import __version__
from actionsguard.scanner import Scanner
from actionsguard.scorecard_runner import ScorecardRunner
from actionsguard.inventory import Inventory
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
    "--user",
    "-u",
    help="Scan all repositories for a user account (or use --user without value for authenticated user)"
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
    user: Optional[str],
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

      # Scan a user account (e.g., your personal repos)
      actionsguard scan --user cybrking

      # Scan with filters
      actionsguard scan --org my-org --exclude repo1,repo2
      actionsguard scan --user cybrking --only my-important-repo

      # Custom output and formats
      actionsguard scan --org my-org --output ./my-reports --format json,html
    """
    try:
        # Validate input
        specified = sum([bool(repo), bool(org), bool(user)])
        if specified == 0:
            console.print("[red]Error: Must specify either --repo, --org, or --user[/red]")
            sys.exit(2)

        if specified > 1:
            console.print("[red]Error: Cannot specify multiple sources (--repo, --org, --user)[/red]")
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
        elif org:
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
        else:  # user
            exclude_list = exclude.split(",") if exclude else []
            only_list = only.split(",") if only else []

            user_display = user if user else "authenticated user"
            console.print(f"[bold]Scanning user account:[/bold] {user_display}")
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

                summary = scanner.scan_user(
                    username=user,
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


@cli.group()
def inventory():
    """Manage repository inventory and tracking."""
    pass


@inventory.command()
@click.option(
    "--org",
    "-o",
    help="Organization name to scan and update inventory"
)
@click.option(
    "--user",
    "-u",
    help="User account to scan and update inventory (use without value for authenticated user)"
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
    "--token",
    "-t",
    help="GitHub token (or set GITHUB_TOKEN env var)"
)
@click.pass_context
def update(ctx, org, user, exclude, only, token):
    """
    Scan organization or user account and update inventory.

    This scans all repositories and updates the inventory database
    with current scores and status.

    Examples:

      # Update inventory for your organization
      actionsguard inventory update --org my-org

      # Update inventory for a user account
      actionsguard inventory update --user cybrking

      # Exclude certain repos
      actionsguard inventory update --org my-org --exclude archived-repo

      # Only scan specific repos
      actionsguard inventory update --user cybrking --only critical-app
    """
    try:
        # Validate input
        specified = sum([bool(org), bool(user)])
        if specified == 0:
            console.print("[red]Error: Must specify either --org or --user[/red]")
            sys.exit(2)

        if specified > 1:
            console.print("[red]Error: Cannot specify both --org and --user[/red]")
            sys.exit(2)

        console.print("\n[bold blue]📊 Updating Repository Inventory[/bold blue]\n")

        # Build config
        config_kwargs = {
            "parallel_scans": 5,
            "verbose": ctx.obj.get("verbose", False),
        }
        if token:
            config_kwargs["github_token"] = token

        config = Config(**config_kwargs)
        config.validate()

        # Create scanner
        scanner = Scanner(config)

        # Scan organization or user
        exclude_list = exclude.split(",") if exclude else None
        only_list = only.split(",") if only else None

        if org:
            console.print(f"[cyan]Scanning organization:[/cyan] {org}\n")
            summary = scanner.scan_organization(
                org_name=org,
                exclude=exclude_list,
                only=only_list,
            )
        else:  # user
            user_display = user if user else "authenticated user"
            console.print(f"[cyan]Scanning user account:[/cyan] {user_display}\n")
            summary = scanner.scan_user(
                username=user,
                exclude=exclude_list,
                only=only_list,
            )

        # Update inventory
        console.print("\n[cyan]Updating inventory...[/cyan]")
        inv = Inventory()
        changes = inv.update_from_scan(summary.results)

        # Display changes
        new_count = sum(1 for c in changes.values() if c == "new")
        updated_count = sum(1 for c in changes.values() if c == "updated")
        unchanged_count = sum(1 for c in changes.values() if c == "unchanged")

        console.print(f"\n[green]✅ Inventory updated![/green]\n")
        console.print(f"  🆕 New repositories:     {new_count}")
        console.print(f"  📝 Updated repositories: {updated_count}")
        console.print(f"  ✓  Unchanged:            {unchanged_count}")

        # Show score changes
        score_changes = inv.get_score_changes()
        if score_changes:
            console.print(f"\n[bold]Recent Score Changes:[/bold]\n")
            for change in score_changes[:5]:  # Show top 5
                emoji = "📈" if change["change"] > 0 else "📉"
                console.print(
                    f"  {emoji} {change['repo_name']}: "
                    f"{change['previous_score']:.1f} → {change['current_score']:.1f} "
                    f"({change['change']:+.1f})"
                )

        console.print(f"\n[dim]Inventory stored in: .actionsguard/inventory.json[/dim]\n")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        if ctx.obj.get("verbose"):
            console.print_exception()
        sys.exit(2)


@inventory.command()
@click.option(
    "--sort",
    type=click.Choice(["score", "risk", "name", "updated"]),
    default="risk",
    help="Sort by field (default: risk)"
)
@click.option(
    "--filter-risk",
    type=click.Choice(["CRITICAL", "HIGH", "MEDIUM", "LOW"]),
    help="Show only repos with specific risk level"
)
def list(sort, filter_risk):
    """
    List all repositories in inventory.

    Shows current score, risk level, and last update time for all
    repositories being tracked.

    Examples:

      # List all repos
      actionsguard inventory list

      # Show only critical risk repos
      actionsguard inventory list --filter-risk CRITICAL

      # Sort by score (lowest first)
      actionsguard inventory list --sort score
    """
    inv = Inventory()
    entries = inv.get_all()

    if not entries:
        console.print("[yellow]Inventory is empty. Run 'actionsguard inventory update' first.[/yellow]")
        return

    # Filter
    if filter_risk:
        entries = [e for e in entries if e.current_risk == filter_risk]

    # Sort
    if sort == "score":
        entries.sort(key=lambda e: e.current_score)
    elif sort == "risk":
        risk_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
        entries.sort(key=lambda e: risk_order.get(e.current_risk, 4))
    elif sort == "name":
        entries.sort(key=lambda e: e.repo_name)
    elif sort == "updated":
        entries.sort(key=lambda e: e.last_updated, reverse=True)

    # Create table
    table = Table(title="Repository Inventory", show_header=True, header_style="bold magenta")
    table.add_column("Repository", style="cyan")
    table.add_column("Score", justify="right")
    table.add_column("Risk", justify="center")
    table.add_column("Scans", justify="right")
    table.add_column("Last Updated", style="dim")

    # Add rows
    risk_colors = {
        "CRITICAL": "red",
        "HIGH": "orange1",
        "MEDIUM": "yellow",
        "LOW": "green",
    }

    for entry in entries:
        risk_color = risk_colors.get(entry.current_risk, "white")
        table.add_row(
            entry.repo_name,
            f"{entry.current_score:.1f}/10",
            f"[{risk_color}]{entry.current_risk}[/{risk_color}]",
            str(entry.scan_count),
            entry.last_updated[:10],  # Just the date
        )

    console.print()
    console.print(table)

    # Summary stats
    stats = inv.get_summary_stats()
    console.print(f"\n[bold]Summary:[/bold]")
    console.print(f"  Total: {stats['total_repos']} repos")
    console.print(f"  Average Score: {stats['avg_score']:.1f}/10")
    console.print(f"  🔴 Critical: {stats['risk_breakdown']['CRITICAL']}")
    console.print(f"  🟠 High: {stats['risk_breakdown']['HIGH']}")
    console.print(f"  🟡 Medium: {stats['risk_breakdown']['MEDIUM']}")
    console.print(f"  🟢 Low: {stats['risk_breakdown']['LOW']}\n")


@inventory.command()
@click.option(
    "--output",
    "-o",
    default="./inventory-export",
    help="Output directory for export (default: ./inventory-export)"
)
@click.option(
    "--format",
    "-f",
    "formats",
    default="html,csv,json",
    help="Export formats (comma-separated: json,html,csv)"
)
def export(output, formats):
    """
    Export inventory to various formats.

    Generates comprehensive reports of your entire repository inventory
    including historical trends and current status.

    Examples:

      # Export to all formats
      actionsguard inventory export

      # Export only CSV
      actionsguard inventory export --format csv

      # Custom output directory
      actionsguard inventory export --output ./reports/inventory
    """
    inv = Inventory()
    entries = inv.get_all()

    if not entries:
        console.print("[yellow]Inventory is empty. Run 'actionsguard inventory update' first.[/yellow]")
        return

    output_dir = Path(output)
    output_dir.mkdir(parents=True, exist_ok=True)

    console.print(f"\n[bold]Exporting inventory...[/bold]\n")

    format_list = [f.strip().lower() for f in formats.split(",")]

    # Export JSON
    if "json" in format_list:
        json_path = output_dir / "inventory.json"
        with open(json_path, 'w') as f:
            json.dump(inv.export_to_dict(), f, indent=2)
        console.print(f"  ✓ JSON: {json_path}")

    # Export CSV
    if "csv" in format_list:
        import csv
        csv_path = output_dir / "inventory.csv"
        with open(csv_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                "Repository", "URL", "Current Score", "Risk Level",
                "First Seen", "Last Updated", "Scan Count"
            ])
            for entry in entries:
                writer.writerow([
                    entry.repo_name,
                    entry.repo_url,
                    f"{entry.current_score:.1f}",
                    entry.current_risk,
                    entry.first_seen[:10],
                    entry.last_updated[:10],
                    entry.scan_count,
                ])
        console.print(f"  ✓ CSV: {csv_path}")

    # Export HTML (simple dashboard)
    if "html" in format_list:
        html_path = output_dir / "inventory.html"
        _generate_inventory_html(inv, html_path)
        console.print(f"  ✓ HTML: {html_path}")

    console.print(f"\n[green]✅ Inventory exported to: {output_dir}[/green]\n")


@inventory.command()
def diff():
    """
    Show changes since last scan.

    Displays repositories with score changes, highlighting improvements
    and regressions.
    """
    inv = Inventory()
    changes = inv.get_score_changes()

    if not changes:
        console.print("[yellow]No score changes found. All repositories are stable.[/yellow]")
        return

    console.print("\n[bold]📊 Score Changes Since Last Scan[/bold]\n")

    # Separate improvements and regressions
    improved = [c for c in changes if c["change"] > 0]
    regressed = [c for c in changes if c["change"] < 0]

    if improved:
        console.print("[green]📈 Improved:[/green]")
        for change in improved:
            console.print(
                f"  {change['repo_name']}: "
                f"{change['previous_score']:.1f} → {change['current_score']:.1f} "
                f"[green](+{change['change']:.1f})[/green]"
            )
        console.print()

    if regressed:
        console.print("[red]📉 Regressed:[/red]")
        for change in regressed:
            console.print(
                f"  {change['repo_name']}: "
                f"{change['previous_score']:.1f} → {change['current_score']:.1f} "
                f"[red]({change['change']:.1f})[/red]"
            )
        console.print()


def _generate_inventory_html(inv: Inventory, output_path: Path):
    """Generate simple HTML dashboard for inventory."""
    stats = inv.get_summary_stats()
    entries = inv.get_all()

    # Sort by risk
    risk_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
    entries.sort(key=lambda e: risk_order.get(e.current_risk, 4))

    html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Repository Inventory</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; }}
        h1 {{ color: #2c3e50; }}
        .stats {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; margin: 20px 0; }}
        .stat-card {{ background: #f8f9fa; padding: 20px; border-radius: 6px; text-align: center; }}
        .stat-value {{ font-size: 2em; font-weight: bold; color: #2c3e50; }}
        .stat-label {{ color: #7f8c8d; text-transform: uppercase; font-size: 0.9em; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
        th {{ background: #3498db; color: white; padding: 12px; text-align: left; }}
        td {{ padding: 10px; border-bottom: 1px solid #ddd; }}
        tr:hover {{ background: #f8f9fa; }}
        .risk-critical {{ background: #e74c3c; color: white; padding: 5px 10px; border-radius: 4px; }}
        .risk-high {{ background: #f39c12; color: white; padding: 5px 10px; border-radius: 4px; }}
        .risk-medium {{ background: #f1c40f; color: #333; padding: 5px 10px; border-radius: 4px; }}
        .risk-low {{ background: #27ae60; color: white; padding: 5px 10px; border-radius: 4px; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🛡️ Repository Inventory Dashboard</h1>
        <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>

        <div class="stats">
            <div class="stat-card">
                <div class="stat-value">{stats['total_repos']}</div>
                <div class="stat-label">Total Repos</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{stats['avg_score']:.1f}</div>
                <div class="stat-label">Avg Score</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{stats['risk_breakdown']['CRITICAL']}</div>
                <div class="stat-label">Critical</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{stats['risk_breakdown']['HIGH']}</div>
                <div class="stat-label">High Risk</div>
            </div>
        </div>

        <table>
            <thead>
                <tr>
                    <th>Repository</th>
                    <th>Score</th>
                    <th>Risk Level</th>
                    <th>Scans</th>
                    <th>Last Updated</th>
                </tr>
            </thead>
            <tbody>
"""

    for entry in entries:
        html += f"""
                <tr>
                    <td><a href="{entry.repo_url}" target="_blank">{entry.repo_name}</a></td>
                    <td>{entry.current_score:.1f}/10</td>
                    <td><span class="risk-{entry.current_risk.lower()}">{entry.current_risk}</span></td>
                    <td>{entry.scan_count}</td>
                    <td>{entry.last_updated[:10]}</td>
                </tr>
"""

    html += """
            </tbody>
        </table>
    </div>
</body>
</html>
"""

    with open(output_path, 'w') as f:
        f.write(html)


if __name__ == "__main__":
    cli(obj={})
