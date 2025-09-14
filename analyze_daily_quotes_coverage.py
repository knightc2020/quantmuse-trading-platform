#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Analyze coverage and date completeness for daily_quotes table.

Features:
- Global stats over a date range (total rows, date range autodetected if not provided)
- Per-code coverage for a provided list of codes (via --codes-file or --codes)
- Baseline trading-day count approximated by weekdays (Mon-Fri) unless dates provided externally

Usage examples:
  python analyze_daily_quotes_coverage.py
  python analyze_daily_quotes_coverage.py --start-date 2015-01-01 --end-date 2025-09-05 \
      --codes-file codes_50.txt --output coverage_50.csv
"""

import argparse
import csv
from datetime import datetime, timedelta
import os
from typing import List, Optional, Dict, Any

from dotenv import load_dotenv

# Load env for Supabase
load_dotenv()

try:
    from data_service.supabase_client import SupabaseDataClient
except Exception:
    raise SystemExit("Cannot import SupabaseDataClient. Ensure repo structure and dependencies are available.")


def business_days_between(start_date: str, end_date: str) -> int:
    """Approximate trading days count as Mon-Fri weekdays between dates inclusive."""
    s = datetime.strptime(start_date, '%Y-%m-%d')
    e = datetime.strptime(end_date, '%Y-%m-%d')
    if e < s:
        return 0
    days = 0
    cur = s
    while cur <= e:
        if cur.weekday() < 5:  # 0-4 Mon-Fri
            days += 1
        cur += timedelta(days=1)
    return days


def autodetect_date_range(client: SupabaseDataClient) -> (Optional[str], Optional[str]):
    try:
        # latest
        latest = client.client.table('daily_quotes').select('trade_date').order('trade_date', desc=True).limit(1).execute()
        # earliest
        earliest = client.client.table('daily_quotes').select('trade_date').order('trade_date', desc=False).limit(1).execute()
        start_date = earliest.data[0]['trade_date'] if earliest.data else None
        end_date = latest.data[0]['trade_date'] if latest.data else None
        return start_date, end_date
    except Exception:
        return None, None


def get_global_row_count(client: SupabaseDataClient, start_date: str, end_date: str) -> int:
    try:
        res = client.client.table('daily_quotes') \
            .select('*', count='exact') \
            .gte('trade_date', start_date) \
            .lte('trade_date', end_date) \
            .limit(1) \
            .execute()
        return int(res.count or 0)
    except Exception:
        return 0


def per_code_coverage(client: SupabaseDataClient, codes: List[str], start_date: str, end_date: str,
                      baseline_days: int) -> List[Dict[str, Any]]:
    out = []
    for code in codes:
        code = code.strip()
        if not code:
            continue
        try:
            res = client.client.table('daily_quotes') \
                .select('*', count='exact') \
                .eq('code', code) \
                .gte('trade_date', start_date) \
                .lte('trade_date', end_date) \
                .limit(1) \
                .execute()
            cnt = int(res.count or 0)
        except Exception:
            cnt = 0
        coverage = (cnt / baseline_days * 100.0) if baseline_days > 0 else 0.0
        out.append({
            'code': code,
            'rows': cnt,
            'baseline_days': baseline_days,
            'coverage_pct': round(coverage, 2),
            'missing_days': max(0, baseline_days - cnt)
        })
    return out


def save_csv(path: str, rows: List[Dict[str, Any]]):
    if not rows:
        return
    with open(path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description='Analyze coverage of daily_quotes table')
    parser.add_argument('--start-date', help='YYYY-MM-DD')
    parser.add_argument('--end-date', help='YYYY-MM-DD')
    parser.add_argument('--codes-file', help='Path to file (txt/csv) with one code per line or first column')
    parser.add_argument('--codes', help='Comma separated list of codes')
    parser.add_argument('--output', help='Optional CSV output path for per-code stats')
    parser.add_argument('--use-weekdays', action='store_true', help='Use Mon-Fri weekday count as baseline (default)')

    args = parser.parse_args()

    client = SupabaseDataClient()
    if not client.is_connected():
        print('❌ Supabase not connected. Check SUPABASE_URL/KEY')
        return 1

    # Auto detect date range if not provided
    start_date = args.start_date
    end_date = args.end_date
    if not start_date or not end_date:
        s, e = autodetect_date_range(client)
        start_date = start_date or s
        end_date = end_date or e
    if not start_date or not end_date:
        print('❌ Cannot determine date range. Provide --start-date and --end-date')
        return 1

    # Global stats
    total_rows = get_global_row_count(client, start_date, end_date)
    baseline_days = business_days_between(start_date, end_date)
    print('=== daily_quotes Coverage Summary ===')
    print(f'Date range: {start_date} ~ {end_date}')
    print(f'Approx. trading days (Mon-Fri): {baseline_days}')
    print(f'Total rows in range: {total_rows:,}')

    # Optional per-code coverage
    codes: List[str] = []
    if args.codes_file:
        try:
            import pandas as pd
            if args.codes_file.lower().endswith(('.csv', '.tsv')):
                df = pd.read_csv(args.codes_file)
                col = df.columns[0]
                codes = df[col].dropna().astype(str).tolist()
            else:
                with open(args.codes_file, 'r', encoding='utf-8') as f:
                    codes = [line.strip() for line in f if line.strip()]
        except Exception as e:
            print(f'⚠️ Failed to read codes file: {e}')
    elif args.codes:
        codes = [c.strip() for c in args.codes.split(',') if c.strip()]

    if codes:
        stats = per_code_coverage(client, codes, start_date, end_date, baseline_days)
        # Print top summary (first 10)
        print('\nPer-code coverage (first 10):')
        for row in stats[:10]:
            print(f"{row['code']}: {row['rows']} rows, {row['coverage_pct']}% ({row['missing_days']} missing)")
        if args.output:
            save_csv(args.output, stats)
            print(f'Per-code stats saved to: {args.output}')

    return 0


if __name__ == '__main__':
    raise SystemExit(main())

