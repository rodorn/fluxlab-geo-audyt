import pytest

from fluxlab_geo.citations import (
    analyze_answer,
    brand_mentioned,
    brand_position,
    extract_competitors,
    extract_ranked_names,
    extract_sources,
    normalize,
)

RANKED_ANSWER = """Oto najlepsi fotografowie slubni w Krakowie:

1. **StudioPremium** - swietne opinie i portfolio.
2. **Foto Kowalski** - dobre ceny, szybka realizacja.
3. **ProSerwis Foto** - dlugie doswiadczenie.

Warto porownac oferty przed decyzja.
"""

NO_BRAND_ANSWER = """Polecane firmy:
1. StudioPremium
2. TechMistrz
3. Grupa Ekspert
"""

WITH_URLS = """Zobacz oferty:
1. Firma A - opis [strona](https://firma-a.pl/oferta)
2. Firma B - opis, wiecej na https://firmab.example.com/uslugi.
Zrodla: https://mapy.google.com/
"""


class TestNormalize:
    def test_strips_accents(self):
        assert normalize("Krakow") == normalize("Kraków")

    def test_lowercase_and_spaces(self):
        assert normalize("Foto-Kowalski!!") == "foto kowalski"


class TestBrandMentioned:
    def test_present(self):
        assert brand_mentioned(RANKED_ANSWER, "Foto Kowalski")

    def test_present_accent_insensitive(self):
        assert brand_mentioned("Polecam firme Kraków-Serwis.", "krakow-serwis")

    def test_absent(self):
        assert not brand_mentioned(NO_BRAND_ANSWER, "Foto Kowalski")

    def test_word_boundary_no_partial(self):
        # "abc" nie powinno trafiac w srodek "abcdef"
        assert not brand_mentioned("polecam abcdef serwis", "abc")

    def test_empty_company(self):
        assert not brand_mentioned(RANKED_ANSWER, "")


class TestRankedNames:
    def test_numbered_bold(self):
        names = extract_ranked_names(RANKED_ANSWER)
        assert names[0] == "StudioPremium"
        assert names[1] == "Foto Kowalski"
        assert names[2] == "ProSerwis Foto"

    def test_plain_numbered(self):
        names = extract_ranked_names(NO_BRAND_ANSWER)
        assert names == ["StudioPremium", "TechMistrz", "Grupa Ekspert"]

    def test_no_list(self):
        assert extract_ranked_names("Zwykly tekst bez listy.") == []


class TestBrandPosition:
    def test_position_two(self):
        assert brand_position(RANKED_ANSWER, "Foto Kowalski") == 2

    def test_position_first(self):
        assert brand_position(RANKED_ANSWER, "StudioPremium") == 1

    def test_none_when_absent(self):
        assert brand_position(NO_BRAND_ANSWER, "Foto Kowalski") is None

    def test_none_when_no_list(self):
        assert (
            brand_position("Polecam Foto Kowalski, super firma.", "Foto Kowalski")
            is None
        )


class TestCompetitors:
    def test_excludes_brand(self):
        comps = extract_competitors(RANKED_ANSWER, "Foto Kowalski")
        assert "Foto Kowalski" not in comps
        assert "StudioPremium" in comps
        assert "ProSerwis Foto" in comps

    def test_all_when_brand_absent(self):
        comps = extract_competitors(NO_BRAND_ANSWER, "Foto Kowalski")
        assert comps == ["StudioPremium", "TechMistrz", "Grupa Ekspert"]

    def test_limit(self):
        comps = extract_competitors(NO_BRAND_ANSWER, "Foto Kowalski", limit=2)
        assert len(comps) == 2


class TestSources:
    def test_markdown_and_plain(self):
        srcs = extract_sources(WITH_URLS)
        assert "https://firma-a.pl/oferta" in srcs
        assert "https://firmab.example.com/uslugi" in srcs
        assert "https://mapy.google.com/" in srcs

    def test_trailing_punct_stripped(self):
        srcs = extract_sources("wiecej: https://x.pl/a.")
        assert "https://x.pl/a" in srcs

    def test_extra_api_sources_merged(self):
        srcs = extract_sources("tekst", extra=["https://api-source.pl"])
        assert "https://api-source.pl" in srcs

    def test_dedup(self):
        srcs = extract_sources("https://x.pl https://x.pl", extra=["https://x.pl"])
        assert srcs.count("https://x.pl") == 1


class TestAnalyzeAnswer:
    def test_full_flow_mentioned(self):
        c = analyze_answer(
            query="najlepszy fotograf slubny w Krakowie",
            provider="Perplexity",
            answer=RANKED_ANSWER,
            company="Foto Kowalski",
        )
        assert c.mentioned is True
        assert c.position == 2
        assert "StudioPremium" in c.competitors

    def test_full_flow_absent(self):
        c = analyze_answer(
            query="najlepszy fotograf",
            provider="PRZYKLAD",
            answer=NO_BRAND_ANSWER,
            company="Foto Kowalski",
            is_sample=True,
        )
        assert c.mentioned is False
        assert c.position is None
        assert c.is_sample is True
        assert len(c.competitors) == 3
