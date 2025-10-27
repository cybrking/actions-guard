"""CSV report generator for ActionsGuard."""

import csv
import logging
from pathlib import Path

from actionsguard.reporters.base import BaseReporter
from actionsguard.models import ScanSummary


logger = logging.getLogger("actionsguard")


class CSVReporter(BaseReporter):
    """Generate CSV reports."""

    def generate_report(self, summary: ScanSummary, filename: str = "report") -> Path:
        """
        Generate CSV report.

        Args:
            summary: Scan summary
            filename: Output filename (without extension)

        Returns:
            Path to generated CSV file
        """
        output_path = self.output_dir / f"{filename}.csv"

        with open(output_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)

            # Write header
            writer.writerow(
                [
                    "Repository",
                    "URL",
                    "Score",
                    "Risk Level",
                    "Critical Issues",
                    "High Issues",
                    "Medium Issues",
                    "Low Issues",
                    "Has Workflows",
                    "Error",
                ]
            )

            # Write data rows
            for result in summary.results:
                severity_counts = result.get_severity_counts()
                has_workflows = result.metadata.get("has_workflows", True)

                writer.writerow(
                    [
                        result.repo_name,
                        result.repo_url,
                        f"{result.score:.1f}",
                        result.risk_level.value,
                        severity_counts["CRITICAL"],
                        severity_counts["HIGH"],
                        severity_counts["MEDIUM"],
                        severity_counts["LOW"],
                        "Yes" if has_workflows else "No",
                        result.error or "",
                    ]
                )

        logger.info(f"Generated CSV report: {output_path}")
        return output_path

    def get_extension(self) -> str:
        """Get file extension."""
        return ".csv"
