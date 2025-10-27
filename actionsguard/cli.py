"""Command-line interface for ActionsGuard."""

import os
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
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose logging")
@click.option(
    "--json-logs", is_flag=True, help="Use structured JSON logging (for production/automation)"
)
@click.pass_context
def cli(ctx, verbose, json_logs):
    """ActionsGuard - GitHub Actions Security Scanner."""
    global logger
    logger = setup_logger(verbose=verbose, json_format=json_logs)
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose
    ctx.obj["json_logs"] = json_logs


@cli.command()
@click.option(
    "--config",
    type=click.Path(exists=True),
    help="Path to configuration file (.yml, .yaml, or .json)",
)
@click.option("--repo", "-r", help="Scan a single repository (format: owner/repo)")
@click.option("--org", "-o", help="Scan all repositories in an organization")
@click.option(
    "--user",
    "-u",
    help="Scan all repositories for a user account (or use --user without value for authenticated user)",
)
@click.option("--exclude", help="Comma-separated list of repositories to exclude")
@click.option("--only", help="Comma-separated list of repositories to scan (all others excluded)")
@click.option(
    "--output", "-d", default="./reports", help="Output directory for reports (default: ./reports)"
)
@click.option(
    "--format",
    "-f",
    "formats",
    default="json,html,csv,markdown",
    help="Report formats (comma-separated: json,html,csv,markdown)",
)
@click.option(
    "--checks",
    "-c",
    help="Scorecard checks to run (comma-separated, default: Dangerous-Workflow,Token-Permissions,Pinned-Dependencies)",
)
@click.option("--all-checks", is_flag=True, help="Run all Scorecard checks")
@click.option(
    "--fail-on-critical", is_flag=True, help="Exit with error code if critical issues found"
)
@click.option("--token", "-t", help="GitHub token (or set GITHUB_TOKEN env var)")
@click.option("--parallel", "-p", default=5, type=int, help="Number of parallel scans (default: 5)")
@click.option(
    "--include-forks",
    is_flag=True,
    help="Include forked repositories when scanning user accounts (default: exclude forks)",
)
@click.pass_context
def scan(
    ctx,
    config: Optional[str],
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
    parallel: int,
    include_forks: bool,
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
            console.print(
                "[red]Error: Cannot specify multiple sources (--repo, --org, --user)[/red]"
            )
            sys.exit(2)

        # Build configuration
        # Load from config file if provided, otherwise create default
        if config:
            try:
                cfg = Config.from_file(config)
                console.print(f"[dim]Loaded configuration from: {config}[/dim]\n")
            except (FileNotFoundError, ValueError) as e:
                console.print(f"[red]Error loading config file: {e}[/red]")
                sys.exit(2)
        else:
            cfg = Config()

        # Override config file with CLI arguments (CLI takes precedence)
        if output != "./reports":  # Not default
            cfg.output_dir = output
        if formats != "json,html,csv,markdown":  # Not default
            cfg.formats = formats.split(",")
        if checks:  # Explicitly provided
            cfg.checks = checks.split(",")
        if fail_on_critical:
            cfg.fail_on_critical = fail_on_critical
        if token:  # Explicitly provided via CLI
            cfg.github_token = token
        if parallel != 5:  # Not default
            cfg.parallel_scans = parallel

        cfg.verbose = ctx.obj["verbose"]

        if all_checks:
            cfg.checks = ["all"]

        config = cfg

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

            summary = scanner.scan_organization(
                org_name=org,
                exclude=exclude_list if exclude_list else None,
                only=only_list if only_list else None,
            )
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

            summary = scanner.scan_user(
                username=user,
                exclude=exclude_list if exclude_list else None,
                only=only_list if only_list else None,
                include_forks=include_forks,
            )

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
@click.argument("scorecard_json", type=click.Path(exists=True))
@click.option(
    "--output", "-o", default="./reports", help="Output directory for reports (default: ./reports)"
)
@click.option(
    "--format",
    "-f",
    "formats",
    default="html,markdown,csv",
    help="Report formats (comma-separated: json,html,csv,markdown)",
)
@click.option("--repo-name", help="Repository name (auto-detected from JSON if not provided)")
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
        with open(scorecard_json, "r") as f:
            scorecard_data = json.load(f)

        # Parse the data (don't check for scorecard installation)
        scorecard_runner = ScorecardRunner(check_install=False)
        checks = scorecard_runner.parse_results(scorecard_data)
        score = scorecard_runner.get_overall_score(scorecard_data)
        metadata = scorecard_runner.get_metadata(scorecard_data)

        # Get repo name
        if not repo_name:
            repo_name = scorecard_data.get("repo", {}).get("name", "unknown-repo")
            repo_name = repo_name.replace("github.com/", "")

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
@click.option("--org", "-o", help="Organization name to scan and update inventory")
@click.option(
    "--user",
    "-u",
    help="User account to scan and update inventory (use without value for authenticated user)",
)
@click.option("--exclude", help="Comma-separated list of repositories to exclude")
@click.option("--only", help="Comma-separated list of repositories to scan (all others excluded)")
@click.option("--token", "-t", help="GitHub token (or set GITHUB_TOKEN env var)")
@click.option(
    "--include-forks",
    is_flag=True,
    help="Include forked repositories when scanning user accounts (default: exclude forks)",
)
@click.pass_context
def update(ctx, org, user, exclude, only, token, include_forks):
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
                include_forks=include_forks,
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


@inventory.command(name="list")
@click.option(
    "--sort",
    type=click.Choice(["score", "risk", "name", "updated"]),
    default="risk",
    help="Sort by field (default: risk)",
)
@click.option(
    "--filter-risk",
    type=click.Choice(["CRITICAL", "HIGH", "MEDIUM", "LOW"]),
    help="Show only repos with specific risk level",
)
def list_inventory(sort, filter_risk):
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
        console.print(
            "[yellow]Inventory is empty. Run 'actionsguard inventory update' first.[/yellow]"
        )
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
    help="Output directory for export (default: ./inventory-export)",
)
@click.option(
    "--format",
    "-f",
    "formats",
    default="html,csv,json",
    help="Export formats (comma-separated: json,html,csv)",
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
        console.print(
            "[yellow]Inventory is empty. Run 'actionsguard inventory update' first.[/yellow]"
        )
        return

    output_dir = Path(output)
    output_dir.mkdir(parents=True, exist_ok=True)

    console.print(f"\n[bold]Exporting inventory...[/bold]\n")

    format_list = [f.strip().lower() for f in formats.split(",")]

    # Export JSON
    if "json" in format_list:
        json_path = output_dir / "inventory.json"
        with open(json_path, "w") as f:
            json.dump(inv.export_to_dict(), f, indent=2)
        console.print(f"  ✓ JSON: {json_path}")

    # Export CSV
    if "csv" in format_list:
        import csv

        csv_path = output_dir / "inventory.csv"
        with open(csv_path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(
                [
                    "Repository",
                    "URL",
                    "Current Score",
                    "Risk Level",
                    "First Seen",
                    "Last Updated",
                    "Scan Count",
                ]
            )
            for entry in entries:
                writer.writerow(
                    [
                        entry.repo_name,
                        entry.repo_url,
                        f"{entry.current_score:.1f}",
                        entry.current_risk,
                        entry.first_seen[:10],
                        entry.last_updated[:10],
                        entry.scan_count,
                    ]
                )
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

    with open(output_path, "w") as f:
        f.write(html)


@cli.command()
@click.option("--user", "-u", help="GitHub username to check (default: authenticated user)")
@click.option("--token", "-t", help="GitHub token (or set GITHUB_TOKEN env var)")
def debug(user: Optional[str], token: Optional[str]):
    """
    Debug GitHub API access and check what repositories are visible.

    This command helps diagnose issues with token permissions and
    repository visibility.

    Examples:

      # Check your own repos
      actionsguard debug

      # Check another user's repos
      actionsguard debug --user cybrking
    """
    try:
        console.print("\n[bold blue]🔍 ActionsGuard Debug Tool[/bold blue]\n")

        # Build config
        config_kwargs = {}
        if token:
            config_kwargs["github_token"] = token

        config = Config(**config_kwargs)

        # Check if token is set
        if not config.github_token:
            console.print("[red]❌ No GitHub token found![/red]")
            console.print(
                "\n[yellow]Please set GITHUB_TOKEN environment variable or use --token flag[/yellow]\n"
            )
            sys.exit(1)

        console.print("[green]✓ GitHub token found[/green]\n")

        # Test GitHub API
        from actionsguard.github_client import GitHubClient

        console.print("[cyan]Testing GitHub API connection...[/cyan]")
        client = GitHubClient(config.github_token)

        # Check token scopes
        try:
            import requests

            headers = {"Authorization": f"token {config.github_token}"}
            resp = requests.get("https://api.github.com/user", headers=headers)
            scopes = resp.headers.get("X-OAuth-Scopes", "")

            console.print("[cyan]Token Scopes:[/cyan]")
            if scopes:
                scopes_list = [s.strip() for s in scopes.split(",")]
                for scope in scopes_list:
                    console.print(f"  ✓ {scope}")

                # Check for required scopes
                has_repo = "repo" in scopes_list
                has_public_repo = "public_repo" in scopes_list

                if not has_repo and not has_public_repo:
                    console.print(
                        "\n[red]⚠️  WARNING: Token is missing repository access scopes![/red]"
                    )
                    console.print(
                        "  You need either 'repo' (for private repos) or 'public_repo' (for public repos only)"
                    )
                    console.print("\n[yellow]How to fix:[/yellow]")
                    console.print("  1. Go to https://github.com/settings/tokens")
                    console.print("  2. Create a new token (classic)")
                    console.print(
                        "  3. Select the 'repo' scope (full control of private repositories)"
                    )
                    console.print("  4. Set: export GITHUB_TOKEN='your_new_token'")
                elif has_public_repo and not has_repo:
                    console.print(
                        "\n[yellow]⚠️  NOTE: Token only has 'public_repo' scope (can't see private repos)[/yellow]"
                    )
                    console.print("  To see private repos, create a token with 'repo' scope")
                    console.print("\n[yellow]How to fix:[/yellow]")
                    console.print("  1. Go to https://github.com/settings/tokens")
                    console.print("  2. Create a new token (classic) with 'repo' scope")
                    console.print("  3. Set: export GITHUB_TOKEN='your_new_token'")
                else:
                    console.print(
                        "\n[green]✓ Token has 'repo' scope - can access private repositories[/green]"
                    )
            else:
                console.print(
                    "  [yellow]No OAuth scopes detected (this is a fine-grained token)[/yellow]"
                )
                console.print("\n[cyan]For fine-grained tokens, ensure you have:[/cyan]")
                console.print("  • Contents: Read access")
                console.print("  • Metadata: Read access")
                console.print("  • Actions: Read access (for workflow scanning)")
            console.print()
        except Exception as e:
            console.print(f"[dim]  (Unable to check token scopes: {e})[/dim]\n")

        # Get authenticated user
        auth_user = client.github.get_user()
        console.print(f"[green]✓ Authenticated as:[/green] {auth_user.login}")
        console.print(f"  Name: {auth_user.name or 'N/A'}")
        console.print(f"  Type: {auth_user.type}")
        console.print()

        # Get user to check
        if user:
            console.print(f"[cyan]Fetching info for user:[/cyan] {user}")

            # Check if this is the authenticated user
            is_self = user.lower() == auth_user.login.lower()
            if is_self:
                console.print(
                    f"[yellow]  Note: You're querying your own account - using authenticated endpoint[/yellow]"
                )
                target_user = auth_user
            else:
                target_user = client.github.get_user(user)
        else:
            console.print(f"[cyan]Fetching your repositories...[/cyan]")
            target_user = auth_user

        console.print(f"  Login: {target_user.login}")
        console.print(f"  Public repos: {target_user.public_repos}")

        # Get total repos if this is the authenticated user
        if hasattr(target_user, "total_private_repos"):
            console.print(f"  Private repos: {target_user.total_private_repos}")
            console.print(
                f"  Total owned repos: {target_user.owned_private_repos + target_user.public_repos}"
            )

        console.print(f"  Type: {target_user.type}")
        console.print()

        # Get repositories
        console.print("[cyan]Fetching repositories via API...[/cyan]")

        # For authenticated user, try different methods
        if user and user.lower() == auth_user.login.lower():
            console.print("[dim]  Using authenticated user endpoint[/dim]")

        repos_list = list(target_user.get_repos())

        console.print(f"\n[bold]Total repositories found: {len(repos_list)}[/bold]\n")

        if not repos_list:
            console.print("[yellow]⚠️  No repositories found![/yellow]\n")

            is_own_account = (not user) or (user.lower() == auth_user.login.lower())

            if is_own_account:
                # Scanning their own account but found no repos
                console.print(
                    "[red]You're scanning your own account but no repos were found.[/red]\n"
                )
                console.print(
                    "This usually means your repos are private and your token doesn't have the 'repo' scope.\n"
                )
                console.print("[yellow]Solution:[/yellow]")
                console.print("  1. Go to https://github.com/settings/tokens")
                console.print("  2. Create a new Personal Access Token (classic)")
                console.print(
                    "  3. Select the 'repo' scope checkbox (full control of private repositories)"
                )
                console.print("  4. Generate the token and copy it")
                console.print("  5. Set it: export GITHUB_TOKEN='your_new_token_here'")
                console.print("  6. Run the debug command again")
            else:
                console.print("Possible reasons:")
                console.print("  • User has no public repositories")
                console.print(
                    "  • User's repositories are all private (and your token can't see them)"
                )
                console.print("  • User account doesn't exist")
            console.print()
            return

        # Categorize repos
        owned_repos = [r for r in repos_list if not r.fork]
        forked_repos = [r for r in repos_list if r.fork]
        archived_repos = [r for r in repos_list if r.archived]
        with_workflows = []

        console.print(f"  📦 Owned repositories: {len(owned_repos)}")
        console.print(f"  🍴 Forked repositories: {len(forked_repos)}")
        console.print(f"  📁 Archived repositories: {len(archived_repos)}")
        console.print()

        # Show first 10 repos
        console.print("[bold]First 10 repositories:[/bold]\n")

        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("Repository")
        table.add_column("Fork?")
        table.add_column("Archived?")
        table.add_column("Private?")

        for repo in repos_list[:10]:
            table.add_row(
                repo.name,
                "Yes" if repo.fork else "No",
                "Yes" if repo.archived else "No",
                "Yes" if repo.private else "No",
            )

        console.print(table)
        console.print()

        # Scanning recommendations
        console.print("[bold]Scanning recommendations:[/bold]\n")

        if len(owned_repos) > 0:
            console.print(f"[green]✓ You have {len(owned_repos)} owned repos to scan[/green]")
            user_arg = f" --user {user}" if user else ""
            console.print(f"  Run: actionsguard scan{user_arg}")

        if len(forked_repos) > 0:
            console.print(
                f"[yellow]• You have {len(forked_repos)} forked repos (excluded by default)[/yellow]"
            )
            user_arg = f" --user {user}" if user else ""
            console.print(f"  To include forks: actionsguard scan{user_arg} --include-forks")

        if len(archived_repos) > 0:
            console.print(f"[dim]• {len(archived_repos)} archived repos (always excluded)[/dim]")

        console.print()

    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Unexpected error: {e}[/red]")
        import traceback

        console.print(traceback.format_exc())
        sys.exit(1)


@cli.command()
@click.option("--token", "-t", help="GitHub token to verify (or set GITHUB_TOKEN env var)")
@click.pass_context
def health(ctx, token: Optional[str]):
    """
    Check system health and verify configuration.

    Verifies:
    - GitHub token is valid
    - Scorecard binary is installed
    - API connectivity
    - Token permissions

    Example:
      actionsguard health
      actionsguard health --token ghp_xxxx
    """
    console.print("\n[bold blue]🏥 ActionsGuard Health Check[/bold blue]\n")

    checks_passed = 0
    checks_failed = 0

    # Check 1: Scorecard binary
    console.print("[cyan]1. Checking Scorecard installation...[/cyan]")
    try:
        runner = ScorecardRunner()
        version = runner.get_version()
        console.print(f"   [green]✓[/green] Scorecard found: {version}\n")
        checks_passed += 1
    except Exception as e:
        console.print(f"   [red]✗[/red] Scorecard not found: {e}")
        console.print(
            "   [yellow]Install Scorecard: https://github.com/ossf/scorecard#installation[/yellow]\n"
        )
        checks_failed += 1

    # Check 2: GitHub Token
    console.print("[cyan]2. Checking GitHub token...[/cyan]")

    if token:
        github_token = token
    else:
        github_token = os.getenv("GITHUB_TOKEN")

    if not github_token:
        console.print("   [red]✗[/red] No GitHub token found")
        console.print(
            "   [yellow]Set GITHUB_TOKEN environment variable or use --token flag[/yellow]\n"
        )
        checks_failed += 1
    else:
        console.print(f"   [green]✓[/green] Token found (length: {len(github_token)} characters)\n")
        checks_passed += 1

        # Check 3: Token validity and permissions
        console.print("[cyan]3. Verifying token permissions...[/cyan]")
        try:
            from actionsguard.github_client import GitHubClient

            client = GitHubClient(github_token)

            # Get authenticated user
            user = client.github.get_user()
            console.print(f"   [green]✓[/green] Authenticated as: {user.login}")

            # Check rate limit
            rate_limit = client.github.get_rate_limit()
            core = rate_limit.core
            console.print(
                f"   [green]✓[/green] API Rate Limit: {core.remaining}/{core.limit} remaining"
            )

            if core.remaining < 100:
                console.print(f"   [yellow]⚠[/yellow]  Low rate limit. Resets at {core.reset}\n")
            else:
                console.print()

            checks_passed += 1

            # Check 4: Repository access
            console.print("[cyan]4. Testing repository access...[/cyan]")
            try:
                # Try to get user's repos (will fail if no repo scope)
                repos = list(client.github.get_user().get_repos()[:1])
                console.print(f"   [green]✓[/green] Can access repositories\n")
                checks_passed += 1
            except Exception as e:
                console.print(f"   [red]✗[/red] Cannot access repositories: {e}")
                console.print("   [yellow]Token may need 'repo' scope[/yellow]\n")
                checks_failed += 1

        except ValueError as e:
            console.print(f"   [red]✗[/red] {e}\n")
            checks_failed += 1
        except Exception as e:
            console.print(f"   [red]✗[/red] Token verification failed: {e}\n")
            checks_failed += 1

    # Summary
    console.print("[bold]Summary:[/bold]")
    console.print(f"  [green]✓[/green] {checks_passed} checks passed")
    if checks_failed > 0:
        console.print(f"  [red]✗[/red] {checks_failed} checks failed")
        console.print("\n[yellow]⚠ System not ready for scanning[/yellow]")
        sys.exit(1)
    else:
        console.print("\n[green]✅ System ready for scanning![/green]")


if __name__ == "__main__":
    cli(obj={})
