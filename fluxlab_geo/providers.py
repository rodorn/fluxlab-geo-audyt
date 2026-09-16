"""Odpytywanie modeli AI oraz deterministyczny fallback.

Klucze wylacznie ze zmiennych srodowiskowych:
  - PERPLEXITY_API_KEY  (Perplexity, model z dostepem do sieci = najlepszy sygnal GEO)
  - OPENAI_API_KEY      (OpenAI, model bez sieci na zywo, sygnal wiedzy modelu)

Gdy brak kluczy, uzywany jest fallback deterministyczny na przykladowych
odpowiedziach. Kazda taka odpowiedz jest oznaczona jako PRZYKLAD, aby nikt nie
pomylil jej z realnym pomiarem. Dzieki temu narzedzie dziala end-to-end nawet
bez dostepu do platnych API.
"""

from __future__ import annotations

import hashlib
import os

PERPLEXITY_URL = "https://api.perplexity.ai/chat/completions"
OPENAI_URL = "https://api.openai.com/v1/chat/completions"

_SYSTEM_PROMPT = (
    "Jestes asystentem zakupowym. Odpowiadaj po polsku. Na pytanie o polecenie "
    "uslugi lub firmy zwroc krotka, ponumerowana liste 3-5 konkretnych firm z "
    "krotkim uzasadnieniem przy kazdej."
)


def available_provider() -> str | None:
    """Zwraca nazwe dostepnego providera wg kluczy w env, albo None."""
    if os.environ.get("PERPLEXITY_API_KEY"):
        return "perplexity"
    if os.environ.get("OPENAI_API_KEY"):
        return "openai"
    return None


def _post_json(url: str, headers: dict, payload: dict, timeout: int = 60) -> dict:
    import requests  # lazy: testy nie wymagaja requests

    resp = requests.post(url, headers=headers, json=payload, timeout=timeout)
    resp.raise_for_status()
    return resp.json()


def query_perplexity(query: str, model: str = "sonar") -> tuple[str, list[str]]:
    """Odpytuje Perplexity. Zwraca (tresc, lista_zrodel)."""
    key = os.environ["PERPLEXITY_API_KEY"]
    data = _post_json(
        PERPLEXITY_URL,
        {"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        {
            "model": model,
            "messages": [
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": query},
            ],
        },
    )
    content = data["choices"][0]["message"]["content"]
    sources = data.get("citations") or []
    if not isinstance(sources, list):
        sources = []
    return content, [str(s) for s in sources]


def query_openai(query: str, model: str = "gpt-4o-mini") -> tuple[str, list[str]]:
    """Odpytuje OpenAI. Zwraca (tresc, lista_zrodel). OpenAI nie zwraca zrodel."""
    key = os.environ["OPENAI_API_KEY"]
    data = _post_json(
        OPENAI_URL,
        {"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        {
            "model": model,
            "messages": [
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": query},
            ],
        },
    )
    return data["choices"][0]["message"]["content"], []


# --- Deterministyczny fallback (PRZYKLAD) -------------------------------------

# Pula wiarygodnie brzmiacych nazw konkurentow uzywanych w przykladach.
_SAMPLE_COMPETITORS = [
    "ProSerwis",
    "TechMistrz",
    "Grupa Ekspert",
    "StudioPremium",
    "SzybkaPomoc24",
    "CentrumUslug",
    "MasterFix",
    "Partner Plus",
]


def _seed(*parts: str) -> int:
    raw = "|".join(parts).encode("utf-8")
    return int(hashlib.sha256(raw).hexdigest(), 16)


def sample_answer(
    query: str, company: str, industry: str, city: str
) -> tuple[str, list[str]]:
    """Buduje deterministyczna, przykladowa odpowiedz AI.

    Marka pojawia sie tylko w czesci zapytan (i rzadko na 1. miejscu), co
    odwzorowuje realny problem slabej widocznosci w AI. Wynik jest w 100%
    powtarzalny dla tych samych danych wejsciowych.
    """
    seed = _seed(query, company, industry, city)
    n = len(_SAMPLE_COMPETITORS)
    start = seed % n
    picks = [_SAMPLE_COMPETITORS[(start + i) % n] for i in range(3)]

    # Marka wchodzi na liste w ~35% przypadkow, na pozycji 2 lub 3.
    include_brand = (seed % 100) < 35 and bool(company.strip())
    brand_pos = 2 if (seed % 2 == 0) else 3

    lines = [
        f'Oto firmy, ktore najczesciej sa polecane na zapytanie "{query}":',
        "",
    ]
    listed = list(picks)
    if include_brand:
        idx = min(brand_pos - 1, len(listed))
        listed.insert(idx, company.strip())
        listed = listed[:4]

    reasons = [
        "dobre opinie klientow i szybka realizacja",
        "szeroki zakres uslug i konkurencyjne ceny",
        "duze doswiadczenie na lokalnym rynku",
        "wysokie oceny w wizytowce Google",
    ]
    for i, name in enumerate(listed, 1):
        why = reasons[(seed + i) % len(reasons)]
        lines.append(f"{i}. **{name}** - {why}.")

    lines += [
        "",
        f"Wybierajac {industry} w miescie {city}, warto porownac opinie i zapytac o wycene.",
    ]
    answer = "\n".join(lines)

    sources = [
        f"https://www.google.com/search?q={industry.replace(' ', '+')}+{city}",
        "https://mapy.google.com/",
        f"https://panoramafirm.pl/{industry.replace(' ', '_')}/{city}",
    ]
    return answer, sources


def run_query(
    query: str,
    company: str,
    industry: str,
    city: str,
    provider: str | None,
) -> tuple[str, str, list[str], bool]:
    """Wykonuje pojedyncze zapytanie.

    Zwraca (provider_label, tresc, zrodla, is_sample).
    Gdy provider jest None lub wywolanie API zawiedzie -> fallback PRZYKLAD.
    """
    if provider == "perplexity":
        try:
            content, sources = query_perplexity(query)
            return "Perplexity", content, sources, False
        except Exception:
            pass
    elif provider == "openai":
        try:
            content, sources = query_openai(query)
            return "OpenAI", content, sources, False
        except Exception:
            pass

    content, sources = sample_answer(query, company, industry, city)
    return "PRZYKLAD", content, sources, True
