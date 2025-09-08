#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data_service.supabase_client import SupabaseDataClient
import logging
from datetime import datetime

logging.basicConfig(level=logging.WARNING)

def main():
    try:
        print("=" * 60)
        print("Supabase Database Check")
        print("=" * 60)
        
        client = SupabaseDataClient()
        
        tables = [
            'seat_daily',
            'money_flow', 
            'inst_flow',
            'trade_flow',
            'daily_quotes',
            'stock_basic'
        ]
        
        print(f"Check Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        total_records = 0
        existing_tables = []
        
        for table in tables:
            try:
                resp = client.client.table(table).select("*", count="exact").limit(1).execute()
                
                if hasattr(resp, 'count') and resp.count is not None:
                    count = resp.count
                    total_records += count
                    existing_tables.append((table, count))
                    print(f"[OK] {table:15} | Records: {count:>12,}")
                    
                    # Get sample record for field info
                    if count > 0:
                        sample = client.client.table(table).select("*").limit(1).execute()
                        if sample.data:
                            fields = list(sample.data[0].keys())
                            print(f"     Fields({len(fields)}): {', '.join(fields[:6])}" + 
                                  ("..." if len(fields) > 6 else ""))
                            
                            # Date range
                            if 'trade_date' in fields:
                                try:
                                    min_resp = client.client.table(table).select("trade_date").order("trade_date").limit(1).execute()
                                    max_resp = client.client.table(table).select("trade_date").order("trade_date", desc=True).limit(1).execute()
                                    
                                    if min_resp.data and max_resp.data:
                                        min_date = min_resp.data[0]['trade_date']
                                        max_date = max_resp.data[0]['trade_date']
                                        print(f"     Date Range: {min_date} ~ {max_date}")
                                except:
                                    pass
                    print()
                        
            except Exception as e:
                if "does not exist" in str(e):
                    print(f"[NO] {table:15} | Table not exists")
                else:
                    print(f"[ERR] {table:15} | Error: {str(e)[:40]}...")
        
        print("=" * 60)
        print("Summary:")
        print(f"Existing Tables: {len(existing_tables)}")
        print(f"Total Records: {total_records:,}")
        print()
        
        if existing_tables:
            print("Table Details:")
            for table, count in sorted(existing_tables, key=lambda x: x[1], reverse=True):
                pct = (count / total_records * 100) if total_records > 0 else 0
                print(f"  {table:15} | {count:>12,} ({pct:5.1f}%)")
        
        print("=" * 60)
        
        return existing_tables, total_records
        
    except Exception as e:
        print(f"Check failed: {e}")
        return [], 0

if __name__ == "__main__":
    main()