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
        
        print("Estimating money_flow table size...")
        
        # Get date range
        try:
            min_resp = client.client.table("money_flow").select("trade_date").order("trade_date").limit(1).execute()
            max_resp = client.client.table("money_flow").select("trade_date").order("trade_date", desc=True).limit(1).execute()
            
            if min_resp.data and max_resp.data:
                min_date = min_resp.data[0]['trade_date']
                max_date = max_resp.data[0]['trade_date']
                print(f"Date range: {min_date} ~ {max_date}")
                
                # Calculate rough trading days
                from datetime import datetime
                start = datetime.strptime(min_date, '%Y-%m-%d')
                end = datetime.strptime(max_date, '%Y-%m-%d')
                total_days = (end - start).days
                trading_days = int(total_days * 0.7)  # Rough estimate
                
                print(f"Estimated trading days: {trading_days}")
                
        except Exception as e:
            print(f"Date range error: {e}")
        
        # Sample different time periods to estimate
        test_dates = ['2024-01-02', '2023-01-03', '2022-01-04', '2021-01-04', '2020-01-02']
        
        daily_samples = []
        for date in test_dates:
            try:
                resp = client.client.table("money_flow").select("trade_date").eq("trade_date", date).limit(10000).execute()
                count = len(resp.data) if resp.data else 0
                daily_samples.append((date, count))
                print(f"Sample date {date}: ~{count} records")
                if count >= 10000:
                    print("  (Hit limit, actual count likely higher)")
            except Exception as e:
                print(f"Error checking {date}: {e}")
        
        # Estimate total based on samples
        if daily_samples:
            avg_daily = sum(count for _, count in daily_samples) / len(daily_samples)
            if max(count for _, count in daily_samples) >= 10000:
                avg_daily = avg_daily * 2  # Adjust for truncated samples
                
            estimated_total = int(avg_daily * trading_days) if 'trading_days' in locals() else 0
            print(f"\nEstimation:")
            print(f"Average daily records: ~{avg_daily:,.0f}")
            print(f"Estimated total records: ~{estimated_total:,}")
            
    except Exception as e:
        print(f"Overall error: {e}")

if __name__ == "__main__":
    main()