"""JSON report generator for ActionsGuard."""

import json
import logging
from pathlib import Path

from actionsguard.reporters.base import BaseReporter
from actionsguard.models import ScanSummary


logger = logging.getLogger("actionsguard")


class JSONReporter(BaseReporter):
    """Generate JSON reports."""

    def generate_report(self, summary: ScanSummary, filename: str = "report") -> Path:
        """
        Generate JSON report.

        Args:
            summary: Scan summary
            filename: Output filename (without extension)

        Returns:
            Path to generated JSON file
        """
        output_path = self.output_dir / f"{filename}.json"

        report_data = summary.to_dict()

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)

        logger.info(f"Generated JSON report: {output_path}")
        return output_path

    def get_extension(self) -> str:
        """Get file extension."""
        return ".json"
