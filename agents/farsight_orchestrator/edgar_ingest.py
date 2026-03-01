"""Build a local SEC EDGAR snapshot for phase-1 deck generation.

Usage:
  python agents/farsight_orchestrator/edgar_ingest.py --tickers NVDA,MSFT,AAPL
"""

from __future__ import annotations

import argparse
import json
import time
import urllib.error
import urllib.request
from pathlib import Path

SEC_SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik}.json"
SEC_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
DEFAULT_USER_AGENT = "farsight-orchestrator/phase1 contact@example.com"


def _http_get_json(url: str, user_agent: str) -> dict:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": user_agent,
            "Accept": "application/json",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def _load_ticker_map(user_agent: str) -> dict[str, str]:
    raw = _http_get_json(SEC_TICKERS_URL, user_agent)
    mapping: dict[str, str] = {}
    for row in raw.values():
        ticker = str(row.get("ticker", "")).upper().strip()
        cik = str(row.get("cik_str", "")).strip()
        if ticker and cik:
            mapping[ticker] = cik.zfill(10)
    return mapping


def build_snapshot(tickers: list[str], user_agent: str) -> dict:
    ticker_map = _load_ticker_map(user_agent)
    output: dict = {"generated_at_unix": int(time.time()), "companies": []}

    for ticker in tickers:
        clean_ticker = ticker.upper().strip()
        cik = ticker_map.get(clean_ticker)
        if not cik:
            output["companies"].append({"ticker": clean_ticker, "error": "CIK not found"})
            continue

        url = SEC_SUBMISSIONS_URL.format(cik=cik)
        try:
            payload = _http_get_json(url, user_agent)
        except urllib.error.URLError as exc:
            output["companies"].append({"ticker": clean_ticker, "cik": cik, "error": str(exc)})
            continue

        recent = payload.get("filings", {}).get("recent", {})
        forms = recent.get("form", [])
        filing_dates = recent.get("filingDate", [])
        accession_numbers = recent.get("accessionNumber", [])
        primary_docs = recent.get("primaryDocument", [])

        filings = []
        for idx, form in enumerate(forms):
            if form not in {"10-K", "10-Q", "8-K"}:
                continue
            accession = accession_numbers[idx].replace("-", "")
            filing_url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession}/{primary_docs[idx]}"
            filings.append(
                {
                    "form": form,
                    "filing_date": filing_dates[idx],
                    "accession_number": accession_numbers[idx],
                    "primary_document": primary_docs[idx],
                    "filing_url": filing_url,
                }
            )
            if len(filings) >= 25:
                break

        output["companies"].append({"ticker": clean_ticker, "cik": cik, "filings": filings})
        time.sleep(0.2)

    return output


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tickers", default="NVDA,MSFT,AAPL", help="Comma-separated tickers")
    parser.add_argument("--user-agent", default=DEFAULT_USER_AGENT, help="SEC-compliant user agent")
    parser.add_argument(
        "--output",
        default=str(Path(__file__).resolve().parent / "data" / "edgar_snapshot.json"),
        help="Output JSON path",
    )
    args = parser.parse_args()

    tickers = [value.strip().upper() for value in args.tickers.split(",") if value.strip()]
    snapshot = build_snapshot(tickers=tickers, user_agent=args.user_agent)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(snapshot, indent=2), encoding="utf-8")
    print(f"Saved SEC snapshot to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

