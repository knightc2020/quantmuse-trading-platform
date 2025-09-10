from supabase import create_client

# Supabase config
url = "https://rnnflvgioxbrfdznodel.supabase.co"
key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJubmZsdmdpb3hicmZkem5vZGVsIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTMwMDU4MjUsImV4cCI6MjA2ODU4MTgyNX0.95D04EwbpWODnFPCYQv-19su52uNjmAYP5jmGQLM7nE"

client = create_client(url, key)
print("Connected to Supabase")

# Try to get all tables using information_schema
try:
    result = client.from_('information_schema.tables').select('table_name').eq('table_schema', 'public').execute()
    print("All tables in public schema:")
    for row in result.data:
        print(f"- {row['table_name']}")
except Exception as e:
    print(f"Cannot access information_schema: {e}")
    
# Try some other possible naming conventions
possible_names = [
    'lhb_data', 'longhu', 'tiger', 'dragon', 'seat_data', 'trading_seat',
    'hot_money_data', 'top_traders', 'major_traders', 'institutional_data',
    'market_data', 'trading_records', 'daily_trading', 'seat_trading',
    'lhb_records', 'trading_list', 'big_orders', 'major_orders'
]

print("\nTrying other possible table names...")
for name in possible_names:
    try:
        result = client.table(name).select('*').limit(1).execute()
        if result.data:
            print(f"FOUND: {name}")
            print(f"Columns: {list(result.data[0].keys())}")
            break
    except:
        continue
        
print("Search completed")