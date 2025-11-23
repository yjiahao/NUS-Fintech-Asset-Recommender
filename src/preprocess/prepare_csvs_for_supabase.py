import pandas as pd
import os

# Create output directory
os.makedirs("data/supabase_upload", exist_ok=True)

print("Preparing CSVs for Supabase upload...")

# ============ CUSTOMERS ============
print("\n1. Processing customers...")
df_customers = pd.read_csv("data/raw/customer_information.csv")

# Select and rename columns exactly as SQL does
df_customers_clean = df_customers[["customerID", "customerType", "riskLevel", "investmentCapacity", "timestamp"]].copy()
df_customers_clean.columns = ["customer_id", "customer_type", "risk_level", "investment_capacity", "timestamp"]

# Remove duplicates, keeping the most recent record (matching DISTINCT ON behavior)
df_customers_clean = df_customers_clean.sort_values(['customer_id', 'timestamp'], ascending=[True, False])
df_customers_clean = df_customers_clean.drop_duplicates(subset=['customer_id'], keep='first')

df_customers_clean.to_csv("data/supabase_upload/customers.csv", index=False)
print(f"   ✓ Created customers.csv with {len(df_customers_clean)} rows")


# ============ ASSETS ============
print("\n2. Processing assets...")
df_assets = pd.read_csv("data/raw/asset_information.csv")

# Select and rename columns exactly as SQL does
df_assets_clean = df_assets[["ISIN", "assetName", "assetShortName", "assetCategory", "assetSubCategory", "marketID", "sector", "industry", "timestamp"]].copy()
df_assets_clean.columns = ["isin", "asset_name", "asset_short_name", "asset_category", "asset_sub_category", "market_id", "sector", "industry", "timestamp"]

# Remove duplicates, keeping the most recent record (matching DISTINCT ON behavior)
df_assets_clean = df_assets_clean.sort_values(['isin', 'timestamp'], ascending=[True, False])
df_assets_clean = df_assets_clean.drop_duplicates(subset=['isin'], keep='first')

df_assets_clean.to_csv("data/supabase_upload/assets.csv", index=False)
print(f"   ✓ Created assets.csv with {len(df_assets_clean)} rows")


# ============ MARKETS ============
print("\n3. Processing markets...")
df_markets = pd.read_csv("data/raw/markets.csv")

# Select and rename columns exactly as SQL does
df_markets_clean = df_markets[["exchangeID", "marketID", "name", "description", "country", "tradingDays", "tradingHours", "marketClass"]].copy()
df_markets_clean.columns = ["exchange_id", "market_id", "name", "description", "country", "trading_days", "trading_hours", "market_class"]

# No deduplication in SQL for markets, so we don't do it either

df_markets_clean.to_csv("data/supabase_upload/markets.csv", index=False)
print(f"   ✓ Created markets.csv with {len(df_markets_clean)} rows")


# ============ TRANSACTIONS ============
print("\n4. Processing transactions...")
df_transactions = pd.read_csv("data/raw/transactions.csv")

# Select and rename columns exactly as SQL does
df_transactions_clean = df_transactions[["customerID", "ISIN", "transactionID", "transactionType", "timestamp", "totalValue", "units", "channel", "marketID"]].copy()
df_transactions_clean.columns = ["customer_id", "isin", "transaction_id", "transaction_type", "timestamp", "total_value", "units", "channel", "market_id"]

# Convert units to integer
df_transactions_clean['units'] = df_transactions_clean['units'].fillna(0).astype(int)

# No deduplication in SQL for transactions, so we don't do it either

df_transactions_clean.to_csv("data/supabase_upload/transactions.csv", index=False)
print(f"   ✓ Created transactions.csv with {len(df_transactions_clean)} rows")


print("\n" + "="*60)
print("✅ All CSVs ready for Supabase upload!")
print("="*60)
print(f"\nOutput directory: data/supabase_upload/")
print("\nFiles created:")
print("  - customers.csv")
print("  - assets.csv")
print("  - markets.csv")
print("  - transactions.csv")
print("\nYou can now upload these files directly to Supabase.")
