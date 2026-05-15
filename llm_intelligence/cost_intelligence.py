import logging
from typing import Any

from topology.models import CostObservation, InferredWorkflow, NodeType, TopologyGraph

logger = logging.getLogger(__name__)

_HIGH_COST_WORKFLOW_TYPES = frozenset({
    "retrieval_augmented_generation",
    "batch_processing",
    "multi_agent",
    "orchestration",
})

_MEDIUM_COST_WORKFLOW_TYPES = frozenset({
    "event_driven",
    "api_service",
    "async_worker",
})

_PREMIUM_PROVIDERS = frozenset({"openai", "anthropic", "gemini", "google-gemini", "cohere"})
_SELF_HOSTED_PROVIDERS = frozenset({"ollama", "huggingface"})


class LLMCostIntelligence:
    """Generates heuristic cost observations from topology and workflow data.

    Observations are advisory only. No billing data is accessed.
    All estimates are based on structural patterns, not measured usage.
    """

    def observe(
        self,
        topology: TopologyGraph,
        workflows: list[InferredWorkflow],
        scan_payload: dict[str, Any],
    ) -> list[CostObservation]:
        observations: list[CostObservation] = []

        llm_providers = [n.label for n in topology.nodes_by_type(NodeType.LLM_PROVIDER)]
        vector_dbs = [n.label for n in topology.nodes_by_type(NodeType.VECTOR_DB)]
        workflow_engines = [n.label for n in topology.nodes_by_type(NodeType.WORKFLOW_ENGINE)]

        obs = self._observe_ocr_llm(workflows, llm_providers)
        if obs:
            observations.append(obs)

        obs = self._observe_multi_agent(workflows, llm_providers)
        if obs:
            observations.append(obs)

        obs = self._observe_multi_provider(llm_providers)
        if obs:
            observations.append(obs)

        obs = self._observe_orchestration_overhead(workflow_engines, workflows)
        if obs:
            observations.append(obs)

        obs = self._observe_rag_cost(workflows, vector_dbs)
        if obs:
            observations.append(obs)

        obs = self._observe_missing_usage_tracking(scan_payload, llm_providers)
        if obs:
            observations.append(obs)

        obs = self._observe_self_hosted_opportunity(llm_providers)
        if obs:
            observations.append(obs)

        obs = self._observe_premium_only(llm_providers)
        if obs:
            observations.append(obs)

        logger.info(
            "Cost intelligence complete",
            extra={"observation_count": len(observations)},
        )
        return observations

    def _observe_ocr_llm(
        self, workflows: list[InferredWorkflow], llm_providers: list[str]
    ) -> CostObservation | None:
        ocr_workflows = [w for w in workflows if w.workflow_type == "batch_processing"]
        if not ocr_workflows:
            return None

        return CostObservation(
            observation="OCR/document pipeline with LLM processing detected — document ingestion can produce large token volumes per file.",
            evidence=[
                "OCR or PDF parsing library detected alongside LLM provider",
                f"LLM providers: {', '.join(llm_providers)}",
                "Document pages typically generate 500–4000 tokens each; batch runs compound cost quickly",
            ],
            severity="warning",
            estimated_tier="high",
        )

    def _observe_multi_agent(
        self, workflows: list[InferredWorkflow], llm_providers: list[str]
    ) -> CostObservation | None:
        agent_workflows = [w for w in workflows if w.workflow_type == "multi_agent"]
        if not agent_workflows:
            return None

        return CostObservation(
            observation="Multi-agent system detected — agent loops and inter-agent communication multiply LLM call volume significantly.",
            evidence=[
                "Multi-agent orchestration framework detected",
                f"LLM providers in use: {', '.join(llm_providers)}",
                "Each agent turn incurs a full LLM round-trip; coordination overhead adds additional calls",
            ],
            severity="high",
            estimated_tier="high",
        )

    def _observe_multi_provider(self, llm_providers: list[str]) -> CostObservation | None:
        premium = [p for p in llm_providers if p in _PREMIUM_PROVIDERS]
        if len(premium) < 2:
            return None

        return CostObservation(
            observation=f"Multiple premium LLM providers in use ({', '.join(premium)}) — ensure routing logic avoids redundant parallel calls.",
            evidence=[
                f"Premium providers detected: {', '.join(premium)}",
                "Without explicit routing logic, requests may fan out to all providers",
                "Consider a single primary provider with a fallback only on failure",
            ],
            severity="warning",
            estimated_tier="high",
        )

    def _observe_orchestration_overhead(
        self, workflow_engines: list[str], workflows: list[InferredWorkflow]
    ) -> CostObservation | None:
        orchestration = [e for e in workflow_engines if e in ("langchain", "llama-index", "crewai", "autogen")]
        if not orchestration:
            return None

        return CostObservation(
            observation=f"LLM orchestration framework detected ({', '.join(orchestration)}) — framework abstraction layers often add hidden prompt overhead.",
            evidence=[
                f"Orchestration frameworks: {', '.join(orchestration)}",
                "Frameworks inject system prompts, chain-of-thought scaffolding, and tool descriptions that inflate token counts",
                "Prompt overhead can range from 200 to 2000+ tokens per call depending on configuration",
            ],
            severity="info",
            estimated_tier="medium",
        )

    def _observe_rag_cost(
        self, workflows: list[InferredWorkflow], vector_dbs: list[str]
    ) -> CostObservation | None:
        rag = [w for w in workflows if w.workflow_type == "retrieval_augmented_generation"]
        if not rag:
            return None

        evidence = [
            "RAG pipeline detected: each query adds retrieved context chunks to the LLM prompt",
            "Typical RAG context injection: 500–3000 tokens per retrieved chunk × number of chunks",
        ]
        if vector_dbs:
            evidence.append(f"Vector stores in use: {', '.join(vector_dbs)}")

        return CostObservation(
            observation="RAG pipeline detected — retrieved context chunks are injected into prompts, substantially increasing per-request token consumption.",
            evidence=evidence,
            severity="warning",
            estimated_tier="high",
        )

    def _observe_missing_usage_tracking(
        self, scan_payload: dict[str, Any], llm_providers: list[str]
    ) -> CostObservation | None:
        if not llm_providers:
            return None

        repo = scan_payload.get("scanner_results", {}).get("results", {}).get("repo_scanner", {})
        all_files_clue = repo.get("capabilities", {})

        # Heuristic: if there's no database and no observability library found, likely no usage tracking
        has_database = all_files_clue.get("has_database", False)
        if has_database:
            return None

        return CostObservation(
            observation="No usage tracking database detected — LLM token consumption and costs may not be instrumented.",
            evidence=[
                f"LLM providers in use: {', '.join(llm_providers)}",
                "No database or storage layer detected that could log token usage",
                "Without usage tracking, cost spikes and budget overruns cannot be detected early",
            ],
            severity="warning",
            estimated_tier="unknown",
        )

    def _observe_self_hosted_opportunity(
        self, llm_providers: list[str]
    ) -> CostObservation | None:
        premium = [p for p in llm_providers if p in _PREMIUM_PROVIDERS]
        self_hosted = [p for p in llm_providers if p in _SELF_HOSTED_PROVIDERS]
        if not premium or self_hosted:
            return None

        return CostObservation(
            observation=f"Only cloud LLM providers detected ({', '.join(premium)}) — no self-hosted or local inference observed.",
            evidence=[
                f"Premium cloud providers: {', '.join(premium)}",
                "Self-hosted options (Ollama, vLLM) can reduce cost for high-volume or latency-sensitive workloads",
                "Ollama is detectable on port 11434 if running locally",
            ],
            severity="info",
            estimated_tier="medium",
        )

    def _observe_premium_only(self, llm_providers: list[str]) -> CostObservation | None:
        # Only surface this if there are many premium providers (already covered by multi-provider obs)
        # and no cheaper alternatives detected
        if len(llm_providers) == 1 and llm_providers[0] in _PREMIUM_PROVIDERS:
            return CostObservation(
                observation=f"Single premium LLM provider ({llm_providers[0]}) — consider adding a cheaper fallback for non-critical requests.",
                evidence=[
                    f"Provider: {llm_providers[0]}",
                    "Tiered routing (premium for critical paths, cheaper models for drafts/classification) can reduce costs 30–70%",
                ],
                severity="info",
                estimated_tier="medium",
            )
        return None
