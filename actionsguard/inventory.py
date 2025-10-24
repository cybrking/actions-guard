"""Inventory management for ActionsGuard."""

import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict

from actionsguard.models import ScanResult, ScanSummary


logger = logging.getLogger("actionsguard")


@dataclass
class InventoryEntry:
    """Single repository in inventory."""
    repo_name: str
    repo_url: str
    current_score: float
    current_risk: str
    first_seen: str
    last_updated: str
    scan_count: int
    score_history: List[Dict[str, Any]]  # [{date, score, risk}]
    latest_checks: Dict[str, Any]  # Latest check results
    metadata: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


class Inventory:
    """Manages repository inventory and historical tracking."""

    def __init__(self, inventory_path: str = ".actionsguard/inventory.json"):
        """
        Initialize inventory.

        Args:
            inventory_path: Path to inventory file
        """
        self.inventory_path = Path(inventory_path)
        self.inventory_path.parent.mkdir(parents=True, exist_ok=True)
        self.data = self._load()

    def _load(self) -> Dict[str, InventoryEntry]:
        """Load inventory from file."""
        if not self.inventory_path.exists():
            return {}

        try:
            with open(self.inventory_path, 'r') as f:
                data = json.load(f)

            # Convert to InventoryEntry objects
            inventory = {}
            for repo_name, entry_dict in data.items():
                inventory[repo_name] = InventoryEntry(**entry_dict)

            return inventory
        except Exception as e:
            logger.error(f"Failed to load inventory: {e}")
            return {}

    def _save(self) -> None:
        """Save inventory to file."""
        try:
            # Convert to dict for JSON serialization
            data = {
                repo_name: entry.to_dict()
                for repo_name, entry in self.data.items()
            }

            with open(self.inventory_path, 'w') as f:
                json.dump(data, f, indent=2)

            logger.debug(f"Saved inventory to {self.inventory_path}")
        except Exception as e:
            logger.error(f"Failed to save inventory: {e}")

    def update_from_scan(self, scan_results: List[ScanResult]) -> Dict[str, str]:
        """
        Update inventory with new scan results.

        Args:
            scan_results: List of scan results

        Returns:
            Dictionary of changes: {repo_name: "new|updated|unchanged"}
        """
        changes = {}
        now = datetime.now().isoformat()

        for result in scan_results:
            # Skip failed scans
            if result.error:
                logger.warning(f"Skipping {result.repo_name}: scan failed")
                continue

            repo_name = result.repo_name

            # Check if repo exists in inventory
            if repo_name in self.data:
                # Update existing entry
                entry = self.data[repo_name]

                # Check if score changed
                if entry.current_score != result.score:
                    changes[repo_name] = "updated"
                else:
                    changes[repo_name] = "unchanged"

                # Update fields
                entry.current_score = result.score
                entry.current_risk = result.risk_level.value
                entry.last_updated = now
                entry.scan_count += 1

                # Add to history
                entry.score_history.append({
                    "date": now,
                    "score": result.score,
                    "risk": result.risk_level.value,
                })

                # Update latest checks
                entry.latest_checks = {
                    check.name: {
                        "score": check.score,
                        "status": check.status.value,
                        "severity": check.severity.value,
                    }
                    for check in result.checks
                }

            else:
                # New entry
                changes[repo_name] = "new"

                self.data[repo_name] = InventoryEntry(
                    repo_name=repo_name,
                    repo_url=result.repo_url,
                    current_score=result.score,
                    current_risk=result.risk_level.value,
                    first_seen=now,
                    last_updated=now,
                    scan_count=1,
                    score_history=[{
                        "date": now,
                        "score": result.score,
                        "risk": result.risk_level.value,
                    }],
                    latest_checks={
                        check.name: {
                            "score": check.score,
                            "status": check.status.value,
                            "severity": check.severity.value,
                        }
                        for check in result.checks
                    },
                    metadata=result.metadata,
                )

        self._save()
        return changes

    def get_all(self) -> List[InventoryEntry]:
        """Get all inventory entries."""
        return list(self.data.values())

    def get_by_repo(self, repo_name: str) -> Optional[InventoryEntry]:
        """Get inventory entry for specific repo."""
        return self.data.get(repo_name)

    def get_summary_stats(self) -> Dict[str, Any]:
        """Get summary statistics."""
        if not self.data:
            return {
                "total_repos": 0,
                "avg_score": 0.0,
                "risk_breakdown": {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0},
            }

        total = len(self.data)
        avg_score = sum(e.current_score for e in self.data.values()) / total

        risk_breakdown = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
        for entry in self.data.values():
            risk_breakdown[entry.current_risk] = risk_breakdown.get(entry.current_risk, 0) + 1

        return {
            "total_repos": total,
            "avg_score": round(avg_score, 2),
            "risk_breakdown": risk_breakdown,
            "last_updated": max((e.last_updated for e in self.data.values()), default="never"),
        }

    def get_score_changes(self, days: int = 7) -> List[Dict[str, Any]]:
        """
        Get repositories with score changes in last N days.

        Args:
            days: Number of days to look back

        Returns:
            List of repos with score changes
        """
        changes = []

        for entry in self.data.values():
            if len(entry.score_history) < 2:
                continue  # Need at least 2 scans to compare

            previous = entry.score_history[-2]
            current = entry.score_history[-1]

            if previous["score"] != current["score"]:
                changes.append({
                    "repo_name": entry.repo_name,
                    "previous_score": previous["score"],
                    "current_score": current["score"],
                    "change": current["score"] - previous["score"],
                    "previous_risk": previous["risk"],
                    "current_risk": current["risk"],
                    "date": current["date"],
                })

        # Sort by change (most improved first)
        changes.sort(key=lambda x: x["change"], reverse=True)
        return changes

    def export_to_dict(self) -> Dict[str, Any]:
        """Export entire inventory as dictionary."""
        return {
            "metadata": {
                "exported_at": datetime.now().isoformat(),
                "total_repos": len(self.data),
            },
            "summary": self.get_summary_stats(),
            "repositories": [entry.to_dict() for entry in self.data.values()],
        }
