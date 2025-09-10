from supabase import create_client

# Supabase config
url = "https://rnnflvgioxbrfdznodel.supabase.co"
key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJubmZsdmdpb3hicmZkem5vZGVsIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTMwMDU4MjUsImV4cCI6MjA2ODU4MTgyNX0.95D04EwbpWODnFPCYQv-19su52uNjmAYP5jmGQLM7nE"

client = create_client(url, key)

# Test 2024 data
tables = ['seat_daily', 'inst_flow', 'trade_flow']

for table in tables:
    print(f"\n=== {table} ===")
    try:
        # Try recent 2024 data
        result = client.table(table).select('*').gte('trade_date', '2024-01-01').lte('trade_date', '2024-12-31').limit(5).execute()
        
        if result.data:
            print(f"Found {len(result.data)} records in 2024")
            print(f"Latest date: {result.data[0].get('trade_date', 'N/A')}")
            print(f"Sample: {result.data[0]}")
            
            # Get latest date for this table
            latest = client.table(table).select('trade_date').order('trade_date', desc=True).limit(1).execute()
            if latest.data:
                print(f"Latest date in table: {latest.data[0]['trade_date']}")
        else:
            print("No 2024 data found")
            
    except Exception as e:
        print(f"Error: {e}")

print("\n=== Summary ===")
print("Testing completed")