#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data_service.supabase_client import SupabaseDataClient
import logging

logging.basicConfig(level=logging.WARNING)

def main():
    try:
        client = SupabaseDataClient()
        
        # Common table names to check
        common_tables = [
            'seat_daily',      # Known to exist
            'money_flow',      # Known to exist (large)
            'inst_flow',       # Known to exist 
            'trade_flow',      # Known to exist
            'daily_quotes',    # Missing - for daily stock data
            'stock_basic',     # Missing - for stock basic info
            'financial_data',  # Check if exists
            'market_data',     # Check if exists
            'dragon_tiger',    # Alternative name?
            'stock_info',      # Alternative name?
            'quotes',          # Alternative name?
            'daily_data',      # Alternative name?
        ]
        
        print("=" * 60)
        print("Complete Table Existence Check")
        print("=" * 60)
        
        existing = []
        missing = []
        errors = []
        total_estimated = 0
        
        for table in common_tables:
            try:
                # Quick existence check
                resp = client.client.table(table).select("*").limit(1).execute()
                
                if resp.data is not None:
                    # Table exists, try to get count or estimate
                    try:
                        count_resp = client.client.table(table).select("*", count="exact").limit(0).execute()
                        if hasattr(count_resp, 'count') and count_resp.count is not None:
                            count = count_resp.count
                            print(f"[EXISTS] {table:15} | Records: {count:>10,}")
                            existing.append((table, count))
                            total_estimated += count
                        else:
                            # Count failed, try estimation for large tables
                            if table == 'money_flow':
                                estimated = 2_500_000  # From previous estimate
                                print(f"[EXISTS] {table:15} | Records: ~{estimated:>9,} (est)")
                                existing.append((table, estimated))
                                total_estimated += estimated
                            else:
                                print(f"[EXISTS] {table:15} | Records: Unknown (count timeout)")
                                existing.append((table, 0))
                    except:
                        print(f"[EXISTS] {table:15} | Records: Count failed")
                        existing.append((table, 0))
                else:
                    missing.append(table)
                    print(f"[MISSING] {table}")
                    
            except Exception as e:
                if "does not exist" in str(e):
                    missing.append(table)
                    print(f"[MISSING] {table}")
                else:
                    errors.append((table, str(e)))
                    print(f"[ERROR] {table:15} | {str(e)[:40]}...")
        
        print("=" * 60)
        print("SUMMARY:")
        print(f"Existing tables: {len(existing)}")
        print(f"Missing tables: {len(missing)}")
        print(f"Error tables: {len(errors)}")
        print(f"Estimated total records: {total_estimated:,}")
        print()
        
        if existing:
            print("EXISTING TABLES (sorted by size):")
            for table, count in sorted(existing, key=lambda x: x[1], reverse=True):
                if count > 0:
                    pct = (count / total_estimated * 100) if total_estimated > 0 else 0
                    print(f"  {table:15} | {count:>12,} ({pct:5.1f}%)")
                else:
                    print(f"  {table:15} | Unknown size")
        
        if missing:
            print(f"\nMISSING TABLES ({len(missing)}):")
            for table in missing:
                print(f"  {table}")
                
        return existing, missing, total_estimated
        
    except Exception as e:
        print(f"Check failed: {e}")
        return [], [], 0

if __name__ == "__main__":
    main()