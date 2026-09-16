"""Parser cytowan: analiza odpowiedzi modelu AI pod katem widocznosci marki.

Dla pojedynczej odpowiedzi ustala:
  - czy marka jest wspomniana (brand_mentioned),
  - na ktorej pozycji na liscie polecanych firm (position, 1 = najlepsza),
  - kto jest wymieniony zamiast niej (competitors),
  - z jakich zrodel korzystal model (sources: URL / domeny).
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field


def _strip_accents(text: str) -> str:
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def normalize(text: str) -> str:
    """Normalizacja do porownan: bez ogonkow, male litery, znaki -> spacja."""
    text = _strip_accents(text or "").lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())


def brand_mentioned(answer: str, company: str) -> bool:
    """Czy nazwa firmy pada w odpowiedzi (odporne na ogonki i wielkosc liter)."""
    ncompany = normalize(company)
    if not ncompany:
        return False
    nanswer = normalize(answer)
    # Dopasowanie na granicy slow, by "abc" nie trafialo w "abcd".
    return (
        re.search(rf"(?<![a-z0-9]){re.escape(ncompany)}(?![a-z0-9])", nanswer)
        is not None
    )


# Wzorce pozycji na liscie: "1. ", "1) ", "1 - ", "- ", "* ", "**Nazwa**"
_LIST_LINE = re.compile(r"^\s*(?:(\d{1,2})[.)]\s+|[-*]\s+)(.+)$")
_BOLD = re.compile(r"\*\*(.+?)\*\*")
_URL = re.compile(r"https?://[^\s\])>\"']+", re.IGNORECASE)
# Cytowania w stylu [1], [2] Perplexity oraz markdown [tekst](url).
_MD_LINK = re.compile(r"\[[^\]]+\]\((https?://[^)]+)\)")


def _extract_name(item_text: str) -> str:
    """Wyciaga wiodaca nazwe firmy z elementu listy.

    Priorytet: pogrubienie (**Nazwa**), inaczej tekst do pierwszego separatora.
    """
    bold = _BOLD.search(item_text)
    if bold:
        return bold.group(1).strip()
    # Odetnij opis po separatorze zdania.
    head = re.split("\\s[-\u2013\u2014:]\\s|[.:]\\s|\\s\\(", item_text, maxsplit=1)[0]
    return head.strip(" *_\"'")


def extract_ranked_names(answer: str) -> list[str]:
    """Zwraca uporzadkowana liste nazw firm z listy w odpowiedzi.

    Obsluguje listy numerowane i punktowane. Jesli w tekscie nie ma listy,
    zwraca liste pustą (pozycji nie da sie ustalic).
    """
    names: list[str] = []
    for line in answer.splitlines():
        m = _LIST_LINE.match(line)
        if not m:
            continue
        item = m.group(2).strip()
        name = _extract_name(item)
        if name and len(name) <= 80:
            names.append(name)
    return names


def brand_position(answer: str, company: str) -> int | None:
    """Pozycja marki na liscie polecanych firm (1 = pierwsza). None gdy brak."""
    ncompany = normalize(company)
    if not ncompany:
        return None
    for i, name in enumerate(extract_ranked_names(answer), 1):
        nname = normalize(name)
        if ncompany in nname or nname in ncompany:
            return i
    return None


def extract_competitors(answer: str, company: str, limit: int = 6) -> list[str]:
    """Nazwy firm wymienione zamiast marki (z zachowaniem kolejnosci)."""
    ncompany = normalize(company)
    out: list[str] = []
    seen: set[str] = set()
    for name in extract_ranked_names(answer):
        nname = normalize(name)
        if not nname:
            continue
        if ncompany and (ncompany in nname or nname in ncompany):
            continue
        if nname in seen:
            continue
        seen.add(nname)
        out.append(name)
        if len(out) >= limit:
            break
    return out


def extract_sources(answer: str, extra: list[str] | None = None) -> list[str]:
    """Zbiera zrodla: linki markdown, gole URL-e oraz cytowania z API."""
    found: list[str] = []
    seen: set[str] = set()

    def _add(url: str) -> None:
        url = url.rstrip(".,);]")
        if url and url not in seen:
            seen.add(url)
            found.append(url)

    for url in _MD_LINK.findall(answer or ""):
        _add(url)
    for url in _URL.findall(answer or ""):
        _add(url)
    for url in extra or []:
        _add(url)
    return found


@dataclass
class Citation:
    query: str
    provider: str
    answer: str
    is_sample: bool = False
    mentioned: bool = False
    position: int | None = None
    competitors: list[str] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)


def analyze_answer(
    query: str,
    provider: str,
    answer: str,
    company: str,
    is_sample: bool = False,
    api_sources: list[str] | None = None,
) -> Citation:
    """Buduje pelny wynik analizy pojedynczej odpowiedzi AI."""
    return Citation(
        query=query,
        provider=provider,
        answer=answer,
        is_sample=is_sample,
        mentioned=brand_mentioned(answer, company),
        position=brand_position(answer, company),
        competitors=extract_competitors(answer, company),
        sources=extract_sources(answer, api_sources),
    )
