# FluxLab GEO/AEO audyt

Sprawdza, czy sztuczna inteligencja (ChatGPT, Perplexity, Google AI Overviews)
poleca Twoja firme, gdy klient pyta ja zakupowo, np. "najlepszy fotograf slubny
w Krakowie". Coraz wiecej ludzi kupuje uslugi na podstawie odpowiedzi AI, a nie
z wynikow Google. Jesli AI wymienia konkurencje zamiast Ciebie, tracisz klientow,
o ktorych nawet nie wiesz.

Zanim AI kogokolwiek poleci, musi móc przeczytać stronę. To sprawdzicie online, bez instalacji i bez rejestracji: [fluxlab.pl/widocznosc-w-ai](https://fluxlab.pl/widocznosc-w-ai) (dostęp dla botów AI, treść bez JavaScriptu, dane uporządkowane, llms.txt).

To narzedzie CLI generuje 5-10 realnych zapytan zakupowych, odpytuje modele AI,
sprawdza czy marka jest cytowana, na ktorej pozycji, kto jest polecany zamiast
niej i z jakich zrodel korzysta AI. Wynik to gotowy, jednostronicowy mini-audyt PDF
z dowodem (fragmentem realnej odpowiedzi AI).

## Co robi

- Generator zapytan: nazwa firmy + branza + miasto -> lista zapytan zakupowych.
- Odpytanie AI: Perplexity (model z dostepem do sieci, najlepszy sygnal GEO) lub OpenAI.
- Parser cytowan: czy marka jest wspomniana, pozycja na liscie, konkurenci, zrodla.
- Raport: jednostronicowy PDF (przez `google-chrome-stable --headless`), po polsku.
- Tryb fallback (PRZYKLAD): dziala end-to-end bez kluczy API, na deterministycznych
  przykladowych odpowiedziach (wyraznie oznaczone), do dema i testow.

## Wymagania

- Python 3.10+
- `google-chrome-stable` (lub `chromium`) w PATH, tylko do generowania PDF
- Klucze API sa opcjonalne (bez nich dziala tryb PRZYKLAD)

## Instalacja

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e .
```

## Klucze API

Klucze wylacznie ze zmiennych srodowiskowych, ZERO w kodzie:

```bash
export PERPLEXITY_API_KEY="..."   # preferowany
export OPENAI_API_KEY="..."       # alternatywa
```

Gdy zadnego klucza nie ma (albo dodasz `--sample`), narzedzie uzywa trybu PRZYKLAD.

## Uzycie

```bash
# Audyt na zywo (jesli ustawiony klucz API), inaczej tryb PRZYKLAD:
python -m fluxlab_geo.cli --firma "Foto Kowalski" --branza "fotograf slubny" \
    --miasto "Krakow" --pdf out/mini_audyt.pdf

# Wymuszony tryb PRZYKLAD (demo, bez zuzycia API):
python -m fluxlab_geo.cli --firma "Foto Kowalski" --branza "fotograf slubny" \
    --miasto "Krakow" --sample --pdf out/mini_audyt.pdf

# Wynik jako JSON (do dalszej automatyzacji):
python -m fluxlab_geo.cli --firma "X" --branza "hydraulik" --miasto "Gdansk" --json
```

Po instalacji dostepna jest tez komenda `fluxlab-geo`.

Przykladowy wynik: [`out/sample_mini_audyt.pdf`](out/sample_mini_audyt.pdf).

## Jak to dziala

1. `queries.py` sklada zapytania zakupowe (generyczne + markowe).
2. `providers.py` odpytuje Perplexity/OpenAI albo zwraca deterministyczny PRZYKLAD.
3. `citations.py` analizuje odpowiedz: wzmianka, pozycja, konkurenci, zrodla.
4. `audit.py` agreguje wynik (wskaznik widocznosci, srednia pozycja, top konkurenci).
5. `report.py` renderuje HTML i konwertuje do PDF przez headless Chrome.

## Testy

```bash
pip install pytest
python -m pytest -q
```

Testy pokrywaja generator zapytan i parser cytowan. CI (GitHub Actions) uruchamia
je na Pythonie 3.10, 3.11 i 3.12.

## Cennik

- Mini-audyt: gratis (probka jak w `out/sample_mini_audyt.pdf`).
- Pelny audyt + playbook wdrozenia: 1500-2500 zl (wieksza pula zapytan, oba modele,
  analiza zrodel cytowanych przez AI, konkretne rekomendacje co zmienic).
- Monitoring widocznosci w AI: 400-600 zl / miesiac (cykliczny pomiar i alert, gdy
  konkurencja zaczyna wypierac marke z odpowiedzi).

## Prywatnosc danych klienta

Realne raporty (`out/*.pdf`, `out/*.html`) i dane klientow sa w `.gitignore` i nigdy
nie trafiaja do repozytorium. Do repo commitowany jest wylacznie przykladowy PDF.

## Uwaga metodologiczna

GEO = Generative Engine Optimization, AEO = Answer Engine Optimization. Odpowiedzi
modeli AI sa niedeterministyczne i moga zmieniac sie w czasie, dlatego audyt jest
zdjeciem stanu na dany dzien i ma najwieksza wartosc w powtarzalnym monitoringu.

FluxLab, automatyzacja procesow i wdrozenia AI dla malych firm. https://fluxlab.pl
