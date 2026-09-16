"""Generator zapytan zakupowych (purchase-intent) do audytu GEO/AEO.

Wejscie: nazwa firmy, branza, miasto.
Wyjscie: 5-10 zapytan, jakie realny klient wpisuje do ChatGPT/Perplexity, gdy
szuka uslugi. Te zapytania sprawdzamy potem w modelach AI: czy marka jest
w odpowiedzi, na ktorej pozycji, kto jest zamiast niej.
"""

from __future__ import annotations


def _clean(text: str) -> str:
    return " ".join((text or "").split()).strip()


def generate_queries(
    company: str,
    industry: str,
    city: str,
    limit: int = 8,
) -> list[str]:
    """Zwraca liste unikalnych zapytan zakupowych.

    Miks zapytan generycznych ("najlepszy X w miescie") i markowych
    ("firma opinie"). Liczba wynikow jest przycieta do zakresu 5-10.
    """
    company = _clean(company)
    industry = _clean(industry)
    city = _clean(city)

    if not industry or not city:
        raise ValueError("Branza i miasto sa wymagane do wygenerowania zapytan.")

    generic = [
        f"najlepszy {industry} w {city}",
        f"najlepsze {industry} {city} ranking",
        f"polecany {industry} {city} opinie",
        f"gdzie zamowic {industry} w {city}",
        f"tani {industry} {city} czy warto",
        f"{industry} {city} porownanie firm",
    ]

    branded = []
    if company:
        branded = [
            f"{company} opinie",
            f"{company} czy warto",
            f"{company} {industry} {city}",
        ]

    # Najpierw generyczne (najwazniejszy sygnal widocznosci), potem markowe.
    ordered = generic + branded

    # Dedup zachowujac kolejnosc.
    seen: set[str] = set()
    unique: list[str] = []
    for q in ordered:
        key = q.lower()
        if key not in seen:
            seen.add(key)
            unique.append(q)

    limit = max(5, min(10, limit))
    return unique[:limit]


def is_branded_query(query: str, company: str) -> bool:
    """Czy zapytanie jest markowe (zawiera nazwe firmy)."""
    company = _clean(company).lower()
    if not company:
        return False
    return company in _clean(query).lower()
