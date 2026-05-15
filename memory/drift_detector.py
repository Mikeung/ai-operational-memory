import logging
from typing import Any

logger = logging.getLogger(__name__)


class DriftDetector:
    """Compares two operational snapshot payloads and produces a structured drift report.

    Deterministic, evidence-based, rule-driven. No AI reasoning.
    Advisory output only.
    """

    def compare(self, previous: dict[str, Any], current: dict[str, Any]) -> dict[str, Any]:
        changes: list[dict[str, Any]] = []
        human_readable: list[str] = []

        self._compare_llm_detections(
            previous.get("llm_detections", []),
            current.get("llm_detections", []),
            changes,
            human_readable,
        )

        prev_repo = previous.get("scanner_results", {}).get("results", {}).get("repo_scanner", {})
        curr_repo = current.get("scanner_results", {}).get("results", {}).get("repo_scanner", {})

        if prev_repo and curr_repo:
            self._compare_repo(prev_repo, curr_repo, changes, human_readable)

        logger.info(
            "Drift comparison complete",
            extra={"change_count": len(changes), "changes": [c["type"] for c in changes]},
        )

        return {
            "change_count": len(changes),
            "changes": changes,
            "summary": (
                f"Detected {len(changes)} operational change(s)"
                if changes
                else "No changes detected"
            ),
            "human_readable": human_readable,
        }

    def _compare_llm_detections(
        self,
        prev: list[dict[str, Any]],
        curr: list[dict[str, Any]],
        changes: list[dict[str, Any]],
        human_readable: list[str],
    ) -> None:
        prev_providers = {d["provider"] for d in prev}
        curr_providers = {d["provider"] for d in curr}

        for provider in curr_providers - prev_providers:
            changes.append({"type": "llm_provider_added", "value": provider})
            human_readable.append(f"New LLM provider detected in source code: {provider}")

        for provider in prev_providers - curr_providers:
            changes.append({"type": "llm_provider_removed", "value": provider})
            human_readable.append(f"LLM provider no longer detected: {provider}")

    def _compare_repo(
        self,
        prev: dict[str, Any],
        curr: dict[str, Any],
        changes: list[dict[str, Any]],
        human_readable: list[str],
    ) -> None:
        # LLM SDKs in package manifests
        for sdk in set(curr.get("llm_sdks", [])) - set(prev.get("llm_sdks", [])):
            changes.append({"type": "llm_sdk_added", "value": sdk})
            human_readable.append(f"New LLM SDK added to packages: {sdk}")

        for sdk in set(prev.get("llm_sdks", [])) - set(curr.get("llm_sdks", [])):
            changes.append({"type": "llm_sdk_removed", "value": sdk})
            human_readable.append(f"LLM SDK removed from packages: {sdk}")

        # Frameworks
        for fw in set(curr.get("frameworks", [])) - set(prev.get("frameworks", [])):
            changes.append({"type": "framework_added", "value": fw})
            human_readable.append(f"New framework detected: {fw}")

        for fw in set(prev.get("frameworks", [])) - set(curr.get("frameworks", [])):
            changes.append({"type": "framework_removed", "value": fw})
            human_readable.append(f"Framework no longer detected: {fw}")

        # Docker
        prev_docker = prev.get("docker", {}).get("present", False)
        curr_docker = curr.get("docker", {}).get("present", False)
        if not prev_docker and curr_docker:
            changes.append({"type": "docker_added"})
            human_readable.append("Docker configuration added to project")
        elif prev_docker and not curr_docker:
            changes.append({"type": "docker_removed"})
            human_readable.append("Docker configuration removed from project")

        # CI/CD
        for ci in set(curr.get("ci_cd", [])) - set(prev.get("ci_cd", [])):
            changes.append({"type": "ci_added", "value": ci})
            human_readable.append(f"New CI/CD system detected: {ci}")

        for ci in set(prev.get("ci_cd", [])) - set(curr.get("ci_cd", [])):
            changes.append({"type": "ci_removed", "value": ci})
            human_readable.append(f"CI/CD system no longer detected: {ci}")

        # Primary language change
        prev_lang = prev.get("primary_language")
        curr_lang = curr.get("primary_language")
        if prev_lang and curr_lang and prev_lang != curr_lang:
            changes.append({"type": "language_changed", "from": prev_lang, "to": curr_lang})
            human_readable.append(f"Primary language changed: {prev_lang} → {curr_lang}")

        # Significant file count change (>20%)
        prev_files = prev.get("total_files", 0)
        curr_files = curr.get("total_files", 0)
        if prev_files > 0:
            change_pct = abs(curr_files - prev_files) / prev_files
            if change_pct > 0.20:
                direction = "increased" if curr_files > prev_files else "decreased"
                changes.append(
                    {
                        "type": "file_count_changed",
                        "from": prev_files,
                        "to": curr_files,
                        "change_pct": round(change_pct * 100, 1),
                    }
                )
                human_readable.append(
                    f"File count {direction} significantly: "
                    f"{prev_files} → {curr_files} ({change_pct:.0%})"
                )
