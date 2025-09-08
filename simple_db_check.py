import os
from supabase import create_client
import pandas as pd
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