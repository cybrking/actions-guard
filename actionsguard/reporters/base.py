"""Base reporter class for ActionsGuard."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Union

from actionsguard.models import ScanResult, ScanSummary


class BaseReporter(ABC):
    """Base class for all reporters."""

    def __init__(self, output_dir: Union[str, Path]):
        """
        Initialize reporter.

        Args:
            output_dir: Directory to write reports to
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    @abstractmethod
    def generate_report(self, summary: ScanSummary, filename: str) -> Path:
        """
        Generate a report.

        Args:
            summary: Scan summary to report on
            filename: Output filename (without extension)

        Returns:
            Path to generated report file
        """
        pass

    @abstractmethod
    def get_extension(self) -> str:
        """
        Get file extension for this reporter.

        Returns:
            File extension (e.g., '.json', '.html')
        """
        pass
