import pytest

from fluxlab_geo.queries import generate_queries, is_branded_query


class TestGenerateQueries:
    def test_count_within_range(self):
        qs = generate_queries("Foto Kowalski", "fotograf slubny", "Krakow")
        assert 5 <= len(qs) <= 10

    def test_limit_clamped_low(self):
        qs = generate_queries("X", "hydraulik", "Gdansk", limit=1)
        assert len(qs) >= 5

    def test_limit_clamped_high(self):
        qs = generate_queries("X", "hydraulik", "Gdansk", limit=99)
        assert len(qs) <= 10

    def test_contains_generic_intent(self):
        qs = generate_queries("Foto Kowalski", "fotograf slubny", "Krakow")
        assert any("najlepszy fotograf slubny w krakow" in q.lower() for q in qs)

    def test_contains_branded(self):
        qs = generate_queries("Foto Kowalski", "fotograf slubny", "Krakow")
        assert any("foto kowalski opinie" == q.lower() for q in qs)

    def test_industry_and_city_present(self):
        qs = generate_queries("Firma", "elektryk", "Poznan")
        for q in qs[:3]:
            low = q.lower()
            assert "elektryk" in low and "poznan" in low

    def test_no_duplicates(self):
        qs = generate_queries("Firma", "elektryk", "Poznan")
        assert len(qs) == len({q.lower() for q in qs})

    def test_deterministic(self):
        a = generate_queries("Firma", "elektryk", "Poznan")
        b = generate_queries("Firma", "elektryk", "Poznan")
        assert a == b

    def test_whitespace_normalized(self):
        qs = generate_queries("  Firma  ", "  elektryk  ", "  Poznan  ")
        assert all("  " not in q for q in qs)

    def test_missing_industry_raises(self):
        with pytest.raises(ValueError):
            generate_queries("Firma", "", "Poznan")

    def test_missing_city_raises(self):
        with pytest.raises(ValueError):
            generate_queries("Firma", "elektryk", "")

    def test_empty_company_only_generic(self):
        qs = generate_queries("", "elektryk", "Poznan")
        assert len(qs) >= 5
        assert all("elektryk" in q.lower() for q in qs)

    def test_no_em_dash_in_queries(self):
        qs = generate_queries("Foto Kowalski", "fotograf slubny", "Krakow")
        for q in qs:
            assert "—" not in q and "–" not in q


class TestIsBrandedQuery:
    def test_branded_true(self):
        assert is_branded_query("Foto Kowalski opinie", "Foto Kowalski")

    def test_branded_false(self):
        assert not is_branded_query("najlepszy fotograf w Krakowie", "Foto Kowalski")

    def test_empty_company(self):
        assert not is_branded_query("cokolwiek", "")
