from supabase import create_client
import pandas as pd

# Supabase config
url = "https://rnnflvgioxbrfdznodel.supabase.co"
key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJubmZsdmdpb3hicmZkem5vZGVsIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTMwMDU4MjUsImV4cCI6MjA2ODU4MTgyNX0.95D04EwbpWODnFPCYQv-19su52uNjmAYP5jmGQLM7nE"

client = create_client(url, key)
print("Connected to Supabase")

# Check each table
tables = ["inst_flow", "trade_flow", "block_trade", "broker_pick", "seat_daily", "money_flow"]

for table in tables:
    print(f"\n{'='*50}")
    print(f"Table: {table}")
    print(f"{'='*50}")
    
    try:
        # Get sample data
        result = client.table(table).select('*').limit(3).execute()
        
        if result.data:
            df = pd.DataFrame(result.data)
            print(f"Columns ({len(df.columns)}): {list(df.columns)}")
            print(f"\nSample data:")
            for i, row in enumerate(result.data[:2]):
                print(f"Row {i+1}: {row}")
                
            # Try to get count
            try:
                count_result = client.table(table).select('*', count='exact').execute()
                print(f"\nTotal records: {len(count_result.data) if count_result.data else 'Unknown'}")
            except:
                print(f"Cannot get count for {table}")
                
        else:
            print(f"Table {table} exists but has no data")
            
    except Exception as e:
        print(f"Error accessing table {table}: {e}")

print(f"\n{'='*50}")
print("Exploration completed")
print(f"{'='*50}")