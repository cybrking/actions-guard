"""HTML report generator for ActionsGuard."""

import logging
from pathlib import Path
from datetime import datetime

from jinja2 import Environment, FileSystemLoader, select_autoescape

from actionsguard.reporters.base import BaseReporter
from actionsguard.models import ScanSummary


logger = logging.getLogger("actionsguard")


class HTMLReporter(BaseReporter):
    """Generate HTML reports."""

    def __init__(self, output_dir):
        """Initialize HTML reporter."""
        super().__init__(output_dir)

        # Set up Jinja2 environment
        template_dir = Path(__file__).parent.parent / "templates"
        self.env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            autoescape=select_autoescape(["html", "xml"]),
        )

    def generate_report(self, summary: ScanSummary, filename: str = "report") -> Path:
        """
        Generate HTML report.

        Args:
            summary: Scan summary
            filename: Output filename (without extension)

        Returns:
            Path to generated HTML file
        """
        output_path = self.output_dir / f"{filename}.html"

        # Get executive summary
        exec_summary = summary.get_executive_summary()

        # Prepare template data
        template_data = {
            "summary": summary,
            "exec_summary": exec_summary,
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "critical_repos": [
                r for r in summary.results
                if r.risk_level.value == "CRITICAL" and not r.error
            ],
            "high_repos": [
                r for r in summary.results
                if r.risk_level.value == "HIGH" and not r.error
            ],
            "medium_repos": [
                r for r in summary.results
                if r.risk_level.value == "MEDIUM" and not r.error
            ],
            "low_repos": [
                r for r in summary.results
                if r.risk_level.value == "LOW" and not r.error
            ],
            "error_repos": [r for r in summary.results if r.error],
        }

        # Render template
        template = self.env.get_template("report_enhanced.html")
        html_content = template.render(**template_data)

        # Write to file
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        logger.info(f"Generated HTML report: {output_path}")
        return output_path

    def get_extension(self) -> str:
        """Get file extension."""
        return ".html"
