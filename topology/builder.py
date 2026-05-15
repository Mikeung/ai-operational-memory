import logging
from typing import Any

logger = logging.getLogger(__name__)


class TopologyBuilder:
    """Constructs a service topology map from scan results.

    Placeholder — Phase 1 implementation pending.
    Advisory output only. Does not modify any systems.
    """

    def build(self, scan_results: list[dict[str, Any]]) -> dict[str, Any]:
        logger.info("Building topology", extra={"scan_count": len(scan_results)})
        return {
            "status": "placeholder",
            "nodes": [],
            "edges": [],
            "scan_count": len(scan_results),
        }
