"""Generowanie mini-audytu HTML i konwersja do PDF przez google-chrome-stable."""

from __future__ import annotations

import html
import shutil
import subprocess
import tempfile
from datetime import date
from pathlib import Path

from .audit import AuditResult


def _pct(value: float) -> str:
    return f"{value * 100:.0f}%".replace(".", ",")


def _verdict(score: float) -> tuple[str, str]:
    """Zwraca (etykieta, kolor) oceny widocznosci."""
    if score >= 0.6:
        return "Dobra widocznosc", "#0b8a3e"
    if score >= 0.3:
        return "Slaba widocznosc", "#c47f00"
    return "Marka niewidoczna w AI", "#c0392b"


def render_html(result: AuditResult) -> str:
    today = date.today().strftime("%d.%m.%Y")
    r = result
    verdict, vcolor = _verdict(r.visibility_score)
    avg_pos = (
        "brak" if r.avg_position is None else f"{r.avg_position:.1f}".replace(".", ",")
    )

    # Tabela zapytan.
    rows = ""
    for i, c in enumerate(r.citations, 1):
        if c.mentioned:
            pos = f"#{c.position}" if c.position else "wspomniana"
            status = f"<span class='ok'>TAK ({pos})</span>"
        else:
            status = "<span class='bad'>NIE</span>"
        comps = ", ".join(html.escape(x) for x in c.competitors[:3]) or "-"
        rows += (
            f"<tr><td class='n'>{i}</td>"
            f"<td class='q'>{html.escape(c.query)}</td>"
            f"<td class='prov'>{html.escape(c.provider)}</td>"
            f"<td class='st'>{status}</td>"
            f"<td class='cmp'>{comps}</td></tr>"
        )

    # Konkurenci zbiorczo.
    comp_html = ""
    for name, cnt in r.top_competitors:
        comp_html += (
            f"<tr><td class='term'>{html.escape(name)}</td>"
            f"<td class='num'>{cnt}</td></tr>"
        )
    if not comp_html:
        comp_html = (
            "<tr><td colspan='2'>Brak wyraznych konkurentow w odpowiedziach.</td></tr>"
        )

    # Dowod: pierwsza odpowiedz, w ktorej marki nie ma.
    proof = next((c for c in r.citations if not c.mentioned), None)
    if proof is None:
        proof = r.citations[0] if r.citations else None
    proof_html = ""
    if proof is not None:
        snippet = proof.answer.strip()
        if len(snippet) > 460:
            snippet = snippet[:460].rstrip() + " [...]"
        proof_html = (
            f"<div class='proofq'>Zapytanie: <b>{html.escape(proof.query)}</b> "
            f"({html.escape(proof.provider)})</div>"
            f"<pre class='proof'>{html.escape(snippet)}</pre>"
        )

    sample_banner = ""
    if r.is_sample:
        sample_banner = (
            "<div class='sample'>DOKUMENT PRZYKLADOWY. Odpowiedzi AI zostaly "
            "wygenerowane w trybie fallback (brak kluczy API), sluza wylacznie "
            "demonstracji dzialania narzedzia. To nie jest pomiar realnego klienta.</div>"
        )

    return f"""<!doctype html>
<html lang="pl">
<head>
<meta charset="utf-8">
<title>Mini-audyt GEO/AEO widocznosci w AI</title>
<style>
  @page {{ size: A4; margin: 9mm 12mm; }}
  * {{ box-sizing: border-box; }}
  body {{ font-family: -apple-system, "Segoe UI", Arial, sans-serif; color: #1a1a1a;
         font-size: 11px; line-height: 1.4; margin: 0; }}
  h1 {{ font-size: 19px; margin: 0 0 2px; }}
  h2 {{ font-size: 12.5px; margin: 9px 0 4px; color: #5b3fd6;
        border-bottom: 2px solid #5b3fd6; padding-bottom: 2px; }}
  .brand {{ color: #5b3fd6; font-weight: 700; }}
  .meta {{ color: #666; font-size: 10px; margin-bottom: 12px; }}
  .hero {{ background: {vcolor}; color: #fff; border-radius: 10px; padding: 11px 16px;
           margin: 6px 0 4px; }}
  .hero .big {{ font-size: 26px; font-weight: 800; line-height: 1.1; }}
  .hero .sub {{ font-size: 11px; opacity: .94; margin-top: 3px; }}
  .cards {{ display: flex; gap: 9px; margin: 11px 0; }}
  .card {{ flex: 1; border: 1px solid #e2e2e2; border-radius: 8px; padding: 9px 11px; }}
  .card .v {{ font-size: 16px; font-weight: 700; }}
  .card .l {{ font-size: 9px; color: #666; text-transform: uppercase; letter-spacing: .3px; }}
  table {{ width: 100%; border-collapse: collapse; margin-top: 4px; }}
  th, td {{ text-align: left; padding: 4px 6px; border-bottom: 1px solid #eee;
           vertical-align: top; }}
  th {{ background: #f5f3fb; font-size: 9px; text-transform: uppercase; color: #555; }}
  td.num, th.num {{ text-align: right; }}
  td.n {{ color: #999; width: 16px; }}
  td.q {{ font-weight: 600; }}
  td.prov {{ color: #666; font-size: 10px; }}
  td.cmp {{ color: #444; font-size: 10px; }}
  .ok {{ color: #0b8a3e; font-weight: 700; }}
  .bad {{ color: #c0392b; font-weight: 700; }}
  .term {{ font-weight: 600; }}
  .proofq {{ font-size: 10px; color: #555; margin: 2px 0 4px; }}
  pre.proof {{ background: #faf9fe; border: 1px solid #e6e1f7; border-radius: 6px;
      padding: 8px 10px; font-size: 9.5px; line-height: 1.35; white-space: pre-wrap;
      font-family: "SFMono-Regular", Consolas, monospace; color: #333; margin: 0; }}
  .note {{ font-size: 9px; color: #888; margin-top: 6px; }}
  .cta {{ margin-top: 9px; background: #f5f3fb; border: 1px solid #e6e1f7;
      border-radius: 8px; padding: 8px 11px; font-size: 10px; }}
  .footer {{ margin-top: 9px; padding-top: 6px; border-top: 1px solid #ddd;
             font-size: 9px; color: #777; display: flex; justify-content: space-between; }}
  .sample {{ background: #fff3cd; border: 1px solid #ffe08a; color: #7a5b00;
             padding: 4px 8px; border-radius: 5px; font-size: 9.5px; display: block;
             margin-bottom: 8px; }}
</style>
</head>
<body>
  {sample_banner}
  <h1>Mini-audyt <span class="brand">GEO / AEO</span>: widocznosc w odpowiedziach AI</h1>
  <div class="meta">Firma: <b>{html.escape(r.company)}</b> &nbsp;|&nbsp;
     Branza: {html.escape(r.industry)} &nbsp;|&nbsp; Miasto: {html.escape(r.city)}
     &nbsp;|&nbsp; Data: {today} &nbsp;|&nbsp; Zrodlo: {html.escape(r.provider_label)}
     &nbsp;|&nbsp; FluxLab, fluxlab.pl</div>

  <div class="hero">
    <div class="big">{verdict}: {r.mentions}/{r.total} zapytan ({_pct(r.visibility_score)})</div>
    <div class="sub">Tyle razy sztuczna inteligencja wymienila Twoja firme, gdy klient
       pytal o usluge zakupowo. W pozostalych odpowiedziach AI polecila konkurencje.</div>
  </div>

  <div class="cards">
    <div class="card"><div class="v">{r.mentions}/{r.total}</div><div class="l">Wzmianki marki</div></div>
    <div class="card"><div class="v">{_pct(r.visibility_score)}</div><div class="l">Wskaznik widocznosci</div></div>
    <div class="card"><div class="v">{avg_pos}</div><div class="l">Srednia pozycja na liscie</div></div>
    <div class="card"><div class="v">{len(r.top_competitors)}</div><div class="l">Konkurenci w AI</div></div>
  </div>

  <h2>Wyniki zapytan zakupowych</h2>
  <table>
    <thead><tr><th class="n"></th><th>Zapytanie klienta do AI</th><th>Model</th>
      <th>Marka w odpowiedzi</th><th>Kto zamiast niej</th></tr></thead>
    <tbody>{rows}</tbody>
  </table>

  <h2>Kto wygrywa Twoje zapytania w AI</h2>
  <table>
    <thead><tr><th>Konkurent polecany przez AI</th><th class="num">W ilu odpowiedziach</th></tr></thead>
    <tbody>{comp_html}</tbody>
  </table>

  <h2>Dowod: przyklad odpowiedzi AI</h2>
  {proof_html}

  <div class="cta">
    <b>Co dalej.</b> Ten dokument to darmowy mini-audyt (probka). Pelny audyt GEO/AEO
    obejmuje wieksza pule zapytan, oba modele (Perplexity + ChatGPT), analize zrodel,
    ktore cytuje AI, oraz playbook wdrozenia (co konkretnie zmienic na stronie i w sieci,
    zeby AI zaczela polecac Twoja firme). Kontakt: fluxlab.pl.
  </div>

  <div class="footer">
    <span>FluxLab, GEO/AEO i automatyzacja dla malych firm, fluxlab.pl</span>
    <span>GEO = Generative Engine Optimization, AEO = Answer Engine Optimization</span>
  </div>
</body>
</html>"""


def html_to_pdf(html_content: str, output_pdf: str | Path) -> Path:
    """Konwertuje HTML do PDF przez google-chrome-stable --headless --print-to-pdf."""
    chrome = (
        shutil.which("google-chrome-stable")
        or shutil.which("google-chrome")
        or shutil.which("chromium")
    )
    if not chrome:
        raise RuntimeError("Nie znaleziono google-chrome-stable/chromium w PATH.")

    output_pdf = Path(output_pdf).resolve()
    output_pdf.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.NamedTemporaryFile(
        "w", suffix=".html", delete=False, encoding="utf-8"
    ) as f:
        f.write(html_content)
        tmp_html = f.name

    try:
        with tempfile.TemporaryDirectory() as profile:
            cmd = [
                chrome,
                "--headless",
                "--no-sandbox",
                "--disable-gpu",
                f"--user-data-dir={profile}",
                "--no-pdf-header-footer",
                f"--print-to-pdf={output_pdf}",
                f"file://{tmp_html}",
            ]
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=90)
        if not output_pdf.exists():
            raise RuntimeError(
                f"Chrome nie wygenerowal PDF. stderr: {proc.stderr[:500]}"
            )
    finally:
        Path(tmp_html).unlink(missing_ok=True)
    return output_pdf
