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
        
        print("Checking money_flow table specifically...")
        
        # Try different approaches to get count
        approaches = [
            ("Method 1: Basic count", lambda: client.client.table("money_flow").select("*", count="exact").limit(0).execute()),
            ("Method 2: Count with specific field", lambda: client.client.table("money_flow").select("trade_date", count="exact").limit(0).execute()),
            ("Method 3: Simple select first", lambda: client.client.table("money_flow").select("trade_date").limit(10).execute()),
        ]
        
        for desc, method in approaches:
            try:
                print(f"\n{desc}:")
                result = method()
                
                if hasattr(result, 'count') and result.count is not None:
                    print(f"  Count: {result.count:,}")
                elif hasattr(result, 'data') and result.data:
                    print(f"  Got {len(result.data)} sample records")
                    if result.data:
                        print(f"  Sample fields: {list(result.data[0].keys())}")
                else:
                    print(f"  Result: {result}")
                    
            except Exception as e:
                print(f"  Error: {e}")
        
        # Try to get table info differently
        print(f"\nTrying table existence check...")
        try:
            # Just try to select one field with limit 1
            test = client.client.table("money_flow").select("trade_date").limit(1).execute()
            print(f"Table exists, sample data: {test.data}")
        except Exception as e:
            print(f"Table check error: {e}")
            
    except Exception as e:
        print(f"Overall error: {e}")

if __name__ == "__main__":
    main()