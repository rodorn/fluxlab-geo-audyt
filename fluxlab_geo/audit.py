"""Orkiestracja audytu GEO/AEO: zapytania -> modele AI -> analiza cytowan."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

from .citations import Citation, analyze_answer
from .providers import available_provider, run_query
from .queries import generate_queries


@dataclass
class AuditResult:
    company: str
    industry: str
    city: str
    provider_label: str
    is_sample: bool
    citations: list[Citation] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.citations)

    @property
    def mentions(self) -> int:
        return sum(1 for c in self.citations if c.mentioned)

    @property
    def visibility_score(self) -> float:
        """Udzial zapytan, w ktorych marka byla wspomniana (0..1)."""
        return self.mentions / self.total if self.total else 0.0

    @property
    def avg_position(self) -> float | None:
        positions = [c.position for c in self.citations if c.position is not None]
        return sum(positions) / len(positions) if positions else None

    @property
    def top_competitors(self) -> list[tuple[str, int]]:
        counter: Counter[str] = Counter()
        for c in self.citations:
            for name in c.competitors:
                counter[name] += 1
        return counter.most_common(8)


def run_audit(
    company: str,
    industry: str,
    city: str,
    limit: int = 8,
    force_sample: bool = False,
) -> AuditResult:
    """Uruchamia pelny audyt dla jednej firmy."""
    queries = generate_queries(company, industry, city, limit=limit)
    provider = None if force_sample else available_provider()

    citations: list[Citation] = []
    any_sample = False
    labels: set[str] = set()

    for q in queries:
        label, content, sources, is_sample = run_query(
            q, company, industry, city, provider
        )
        labels.add(label)
        any_sample = any_sample or is_sample
        citations.append(
            analyze_answer(
                query=q,
                provider=label,
                answer=content,
                company=company,
                is_sample=is_sample,
                api_sources=sources,
            )
        )

    provider_label = ", ".join(sorted(labels)) if labels else "PRZYKLAD"
    return AuditResult(
        company=company,
        industry=industry,
        city=city,
        provider_label=provider_label,
        is_sample=any_sample,
        citations=citations,
    )
