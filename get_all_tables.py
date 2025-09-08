import os
from supabase import create_client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Supabase config from environment
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")

if not url or not key:
    raise ValueError("请在.env文件中设置SUPABASE_URL和SUPABASE_KEY")

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