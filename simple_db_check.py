from supabase import create_client
import pandas as pd

# Supabase config
url = "https://rnnflvgioxbrfdznodel.supabase.co"
key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJubmZsdmdpb3hicmZkem5vZGVsIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTMwMDU4MjUsImV4cCI6MjA2ODU4MTgyNX0.95D04EwbpWODnFPCYQv-19su52uNjmAYP5jmGQLM7nE"

client = create_client(url, key)
print("Connected to Supabase")

# Try common table names
tables = ['dragon_tiger', 'longhubang', 'lhb', 'dragon_list', 'top_list', 'trading_data', 'stock_data']

for table in tables:
    try:
        result = client.table(table).select('*').limit(1).execute()
        if result.data:
            df = pd.DataFrame(result.data)
            print(f"\nFound table: {table}")
            print(f"Columns: {list(df.columns)}")
            print(f"Sample data: {result.data[0]}")
            break
    except Exception as e:
        print(f"Table {table} not found: {str(e)[:30]}...")
        
print("Database check completed")