"""Workflow-level security analysis for ActionsGuard."""

import logging
from typing import List, Dict, Any, Optional
from actionsguard.models import WorkflowFinding, WorkflowAnalysis, Severity, CheckResult

logger = logging.getLogger("actionsguard")


class WorkflowAnalyzer:
    """Analyzes Scorecard results to extract per-workflow security findings."""

    def __init__(self):
        """Initialize workflow analyzer."""
        pass

    def analyze_scorecard_results(
        self,
        scorecard_data: Dict[str, Any],
        checks: List[CheckResult]
    ) -> List[WorkflowAnalysis]:
        """
        Extract workflow-level findings from Scorecard results.

        Args:
            scorecard_data: Raw Scorecard JSON data
            checks: Parsed CheckResult objects

        Returns:
            List of WorkflowAnalysis objects, one per workflow file
        """
        # Validate inputs
        if not scorecard_data or not checks:
            logger.debug("No scorecard data or checks to analyze")
            return []

        workflow_findings_map = {}  # Map workflow path -> list of findings

        # Parse each check's details for workflow-specific information
        checks_data = scorecard_data.get("checks", [])
        if not checks_data:
            logger.debug("No checks in scorecard data")
            return []

        for check_data in checks_data:
            check_name = check_data.get("name", "Unknown")
            check_score = check_data.get("score", 0)

            # Find corresponding CheckResult for severity
            check_result = next(
                (c for c in checks if c.name == check_name),
                None
            )

            if not check_result:
                continue

            # Extract details which contain file-specific information
            details = check_data.get("details")

            # Skip if no details or details is None
            if not details:
                continue

            # Ensure details is iterable
            if not isinstance(details, (list, tuple)):
                logger.warning(f"Details for {check_name} is not iterable: {type(details)}")
                continue

            for detail in details:
                if not detail or not isinstance(detail, dict):
                    continue

                # Scorecard details contain file paths and messages
                msg = detail.get("msg", "")
                detail_type = detail.get("type", "")

                # Extract workflow file path from the detail
                workflow_path = self._extract_workflow_path(detail, msg)

                if workflow_path:
                    # Create finding
                    finding = WorkflowFinding(
                        workflow_path=workflow_path,
                        check_name=check_name,
                        severity=check_result.severity,
                        message=msg,
                        line_number=self._extract_line_number(detail),
                        snippet=self._extract_snippet(detail),
                        recommendation=self._get_recommendation(check_name, msg),
                    )

                    # Add to workflow's findings
                    if workflow_path not in workflow_findings_map:
                        workflow_findings_map[workflow_path] = []

                    workflow_findings_map[workflow_path].append(finding)

        # Convert map to list of WorkflowAnalysis objects
        workflow_analyses = []
        for workflow_path, findings in workflow_findings_map.items():
            analysis = WorkflowAnalysis(
                path=workflow_path,
                findings=findings,
                score=None,  # Could calculate per-workflow score if needed
            )
            workflow_analyses.append(analysis)

        # Sort by number of findings (most issues first)
        workflow_analyses.sort(
            key=lambda w: (w.get_critical_count(), w.get_high_count(), len(w.findings)),
            reverse=True
        )

        return workflow_analyses

    def _extract_workflow_path(self, detail: Dict[str, Any], msg: str) -> Optional[str]:
        """
        Extract workflow file path from Scorecard detail.

        Args:
            detail: Scorecard detail object
            msg: Detail message

        Returns:
            Workflow path or None
        """
        # Check if detail has a path field
        if "path" in detail:
            path = detail["path"]
            if ".github/workflows/" in path:
                return path

        # Try to extract from message
        if ".github/workflows/" in msg:
            # Extract path from message like "found in .github/workflows/ci.yml"
            import re
            match = re.search(r'\.github/workflows/[\w\-\.]+\.ya?ml', msg)
            if match:
                return match.group(0)

        return None

    def _extract_line_number(self, detail: Dict[str, Any]) -> Optional[int]:
        """Extract line number from detail if available."""
        # Scorecard sometimes provides line numbers
        if "line" in detail:
            return detail["line"]

        # Try to extract from offset
        if "offset" in detail:
            return detail["offset"]

        return None

    def _extract_snippet(self, detail: Dict[str, Any]) -> Optional[str]:
        """Extract code snippet from detail if available."""
        if "snippet" in detail:
            return detail["snippet"]

        return None

    def _get_recommendation(self, check_name: str, message: str) -> str:
        """
        Generate remediation recommendation based on check type.

        Args:
            check_name: Name of the security check
            message: The finding message

        Returns:
            Recommendation string
        """
        recommendations = {
            "Dangerous-Workflow": self._recommend_dangerous_workflow(message),
            "Token-Permissions": self._recommend_token_permissions(message),
            "Pinned-Dependencies": self._recommend_pinned_dependencies(message),
        }

        return recommendations.get(check_name, "Review and remediate this security issue.")

    def _recommend_dangerous_workflow(self, message: str) -> str:
        """Generate recommendation for dangerous workflow patterns."""
        if "pull_request_target" in message.lower():
            return (
                "Replace 'pull_request_target' with 'pull_request' trigger. "
                "If you must use pull_request_target, add explicit permission checks "
                "and avoid checking out PR code."
            )

        if "untrusted" in message.lower() or "injection" in message.lower():
            return (
                "Avoid using untrusted input directly in shell commands. "
                "Use environment variables or GITHUB_ENV file instead. "
                "Example: echo \"INPUT=${{ inputs.value }}\" >> $GITHUB_ENV"
            )

        return "Review workflow for dangerous patterns and follow GitHub Actions security best practices."

    def _recommend_token_permissions(self, message: str) -> str:
        """Generate recommendation for token permission issues."""
        if "write-all" in message.lower() or "write" in message.lower():
            return (
                "Use minimal permissions. Replace 'permissions: write-all' with specific permissions. "
                "Example:\n"
                "permissions:\n"
                "  contents: read\n"
                "  pull-requests: write"
            )

        return "Review and minimize token permissions to only what's necessary."

    def _recommend_pinned_dependencies(self, message: str) -> str:
        """Generate recommendation for unpinned dependencies."""
        # Extract action name if possible
        import re
        action_match = re.search(r'([\w\-]+/[\w\-]+)@(v?\d+)', message)

        if action_match:
            action_name = action_match.group(1)
            return (
                f"Pin '{action_name}' to a specific commit SHA instead of a tag. "
                f"Visit https://github.com/{action_name}/releases to find the commit SHA "
                f"for the version you want to use."
            )

        return (
            "Pin all GitHub Actions to specific commit SHAs instead of tags for supply chain security. "
            "Example: uses: actions/checkout@8e5e7e5ab8b370d6c329ec480221332ada57f0ab"
        )
