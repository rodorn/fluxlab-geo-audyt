"""CLI: audyt GEO/AEO widocznosci marki w odpowiedziach AI.

Uzycie:
    python -m fluxlab_geo.cli --firma "Nazwa" --branza "fotograf slubny" --miasto "Krakow" \\
        --pdf out/mini_audyt.pdf
    python -m fluxlab_geo.cli --firma "X" --branza "hydraulik" --miasto "Gdansk" --json
    python -m fluxlab_geo.cli --firma "X" --branza "X" --miasto "X" --sample  # wymus PRZYKLAD

Klucze API (opcjonalne) tylko ze srodowiska:
    export PERPLEXITY_API_KEY=...   # preferowany, model z dostepem do sieci
    export OPENAI_API_KEY=...       # alternatywa
Bez kluczy narzedzie dziala w trybie PRZYKLAD (fallback deterministyczny).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .audit import run_audit
from .providers import available_provider
from .report import html_to_pdf, render_html


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="fluxlab-geo",
        description="Audyt GEO/AEO: czy AI (ChatGPT/Perplexity) poleca Twoja firme.",
    )
    p.add_argument("--firma", required=True, help="Nazwa firmy / marki.")
    p.add_argument(
        "--branza", required=True, help="Branza lub usluga, np. 'fotograf slubny'."
    )
    p.add_argument("--miasto", required=True, help="Miasto / rynek lokalny.")
    p.add_argument(
        "--liczba",
        type=int,
        default=8,
        help="Liczba zapytan do sprawdzenia (5-10, domyslnie 8).",
    )
    p.add_argument(
        "--sample",
        action="store_true",
        help="Wymus tryb PRZYKLAD (ignoruj klucze API).",
    )
    p.add_argument("--pdf", metavar="PLIK", help="Wygeneruj mini-audyt PDF.")
    p.add_argument("--html", metavar="PLIK", help="Zapisz mini-audyt HTML.")
    p.add_argument("--json", action="store_true", help="Wypisz wynik jako JSON.")
    args = p.parse_args(argv)

    result = run_audit(
        company=args.firma,
        industry=args.branza,
        city=args.miasto,
        limit=args.liczba,
        force_sample=args.sample,
    )

    if args.json:
        print(
            json.dumps(
                {
                    "firma": result.company,
                    "branza": result.industry,
                    "miasto": result.city,
                    "zrodlo": result.provider_label,
                    "przyklad": result.is_sample,
                    "wzmianki": result.mentions,
                    "zapytan": result.total,
                    "widocznosc": round(result.visibility_score, 3),
                    "srednia_pozycja": result.avg_position,
                    "konkurenci": [
                        {"nazwa": n, "liczba": c} for n, c in result.top_competitors
                    ],
                    "zapytania": [
                        {
                            "query": c.query,
                            "provider": c.provider,
                            "mentioned": c.mentioned,
                            "position": c.position,
                            "competitors": c.competitors,
                            "sources": c.sources,
                        }
                        for c in result.citations
                    ],
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        if not args.sample and available_provider() is None:
            print(
                "UWAGA: brak PERPLEXITY_API_KEY / OPENAI_API_KEY. "
                "Tryb PRZYKLAD (dane demonstracyjne).\n",
                file=sys.stderr,
            )
        print(f"Audyt GEO/AEO: {result.company} ({result.industry}, {result.city})")
        print(f"Zrodlo odpowiedzi: {result.provider_label}")
        print(
            f">>> WIDOCZNOSC: {result.mentions}/{result.total} zapytan "
            f"({result.visibility_score * 100:.0f}%)"
        )
        if result.avg_position is not None:
            print(f"Srednia pozycja na liscie AI: {result.avg_position:.1f}")
        print("\nZapytania:")
        for i, c in enumerate(result.citations, 1):
            mark = "TAK" if c.mentioned else "NIE "
            pos = f" #{c.position}" if c.position else ""
            comps = ", ".join(c.competitors[:3]) or "-"
            print(f"  {i:2}. [{mark}{pos:>3}] {c.query}")
            print(f"       konkurenci: {comps}")
        print("\nKto wygrywa Twoje zapytania w AI:")
        for name, cnt in result.top_competitors:
            print(f"  - {name:<22} w {cnt} odpowiedziach")

    if args.html:
        Path(args.html).write_text(render_html(result), encoding="utf-8")
        print(f"\nZapisano HTML: {args.html}", file=sys.stderr)

    if args.pdf:
        out = html_to_pdf(render_html(result), args.pdf)
        print(f"Zapisano PDF: {out}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
