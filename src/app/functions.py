import os
import psycopg2
import pandas as pd

def get_connection():
    conn = psycopg2.connect(
        host="localhost",
        port=5434,
        database=os.getenv("POSTGRES_DB"),
        user=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD")
    )
    return conn

# Sample test query
def show_customers():
    conn = get_connection()
    df = pd.read_sql("SELECT * FROM customers LIMIT 5;", conn)
    conn.close()
    return df

def get_info(customer_id):
    query = """
    SELECT
        c.customer_id,
        c.customer_type,
        c.investment_capacity,
        c.risk_level,
        m.market_class,
        m.country,
        m.trading_days,
        m.trading_hours,
        m.description,
        m.name,
        m.market_id,
        m.exchange_id,
        a.asset_name,
        a.industry,
        a.asset_category,
        a.sector,
        a.ISIN,
        a.asset_short_name,
        a.asset_sub_category,
        t.channel,
        t.timestamp,
        t.total_value,
        t.transaction_type,
        t.units
        FROM customers c
        LEFT JOIN transactions t ON c.customer_id = t.customer_id
        LEFT JOIN assets a ON t.ISIN = a.ISIN
        LEFT JOIN markets m ON t.market_id = m.market_id
        WHERE c.customer_id = %s
        ORDER BY t.timestamp DESC;
        """
    conn = get_connection()
    df = pd.read_sql(query, conn, params=(customer_id,))
    conn.close()
    return df


def cleaning(df):
    # Handling NaN for Asset Names
    df.loc[df['isin'] == 'DE000A2TEDB8', 'asset_name'] = 'thyssenkrupp AG'
    df.loc[df['isin'] == 'LU0671501806', 'asset_name'] = 'Schroder ISF Global High Yield A Dis EUR H QV'
    df.loc[df['isin'] == 'US00214Q1040', 'asset_name'] = 'The ARK INNOVATION ETF'
    df.loc[df['isin'] == 'US0032601066', 'asset_name'] = 'abrdn Physical Platinum Shares ETF'
    df.loc[df['isin'] == 'US26924G7714', 'asset_name'] = 'ETFMG TRAVEL TECH ETF'
    df.loc[df['isin'] == 'US3814305450', 'asset_name'] = 'The Goldman Sachs Hedge Industry VIP ETF'
    df.loc[df['isin'] == 'US46090E1038', 'asset_name'] = 'Invesco QQQ'
    df.loc[df['isin'] == 'US4642863504', 'asset_name'] = 'iShares MSCI Agriculture Producers ETF'
    df.loc[df['isin'] == 'US4642864007', 'asset_name'] = 'iShares MSCI Brazil ETF'
    df.loc[df['isin'] == 'US4642871762', 'asset_name'] = 'iShares TIPS Bond ETF'
    df.loc[df['isin'] == 'US4642876555', 'asset_name'] = 'iShares Russell 2000 ETF'
    df.loc[df['isin'] == 'US4642876894', 'asset_name'] = 'iShares Russell 3000 ETF'
    df.loc[df['isin'] == 'US4642882579', 'asset_name'] = 'iShares MSCI ACWI ETF'
    df.loc[df['isin'] == 'US46429B2676', 'asset_name'] = 'iShares U.S. Treasury Bond ETF'
    df.loc[df['isin'] == 'US5007674055', 'asset_name'] = 'KraneShares Bosera MSCI China A 50 Connect Index ETF'
    df.loc[df['isin'] == 'US72201R7750', 'asset_name'] = 'PIMCO Active Bond Exchange-Traded Fund'
    df.loc[df['isin'] == 'US74347X8496', 'asset_name'] = 'ProShares Short 20+ Year Treasury'
    df.loc[df['isin'] == 'US78462F1030', 'asset_name'] = 'SPDR® S&P 500® ETF Trust'
    df.loc[df['isin'] == 'US78468R6633', 'asset_name'] = 'Bloomberg 1-3 Month US Treasury Bill Index'
    df.loc[df['isin'] == 'US81369Y5069', 'asset_name'] = 'Energy Select Sector SPDR Fund'
    df.loc[df['isin'] == 'US92189F1066', 'asset_name'] = 'VanEck Gold Miners ETF'
    df.loc[df['isin'] == 'US9219378356', 'asset_name'] = 'Vanguard Total Bond Market ETF'
    df.loc[df['isin'] == 'US9229085538', 'asset_name'] = 'Vanguard REIT ETF'
    df.loc[df['isin'] == 'US97717W8516', 'asset_name'] = 'WisdomTree Japan Hedged Equity Fund'
    df.loc[df['isin'] == 'GRF000394004', 'asset_short_name'] = 'DELEI5Y'

    df['asset_sub_category'] = df.apply(
        lambda row: 'Stock' if (row['asset_category'] == 'Stock' and pd.isna(row['asset_sub_category']))
        else row['asset_sub_category'],
        axis=1
    )

    mask = df['asset_category'].isin(['MTF', 'Bond'])

    df.loc[mask & df['sector'].isna(), 'sector'] = 'NIL'
    df.loc[mask & df['industry'].isna(), 'industry'] = 'NIL'
    mask_remaining = (
        (df['asset_category'] == 'Stock') &
        (df[['sector', 'industry']].isna().any(axis=1))
    )

    df.loc[mask_remaining, 'sector'] = 'Unknown'
    df.loc[mask_remaining, 'industry'] = 'Unknown'
    df["is_buy"] = (df["transaction_type"] == "Buy").astype(int)
    df["is_sell"] = (df["transaction_type"] == "Sell").astype(int)
    return df

def df_model(df):
    df_pos = df[df["is_buy"]==1].copy()
    df_pos["user_id"] = df_pos["customer_id"]
    df_pos["item_id"] = df_pos["isin"]
    ts = pd.to_datetime(df_pos["timestamp"], errors="coerce")
    df_pos = df_pos[ts.notna()].copy()
    df_pos["timestamp"] = ts[ts.notna()].astype("int64") // 10**9
    df_pos["rating"] = 1
    df_pos = df_pos[["user_id", "item_id", "timestamp", "rating"]].sort_values("timestamp")
    df_pos = df_pos.drop_duplicates(["user_id", "item_id"], keep="last")
    return df_pos

def get_cleaned_info(customer_id):
    df = get_info(customer_id)
    cleaned_df = cleaning(df)
    df_pos = df_model(cleaned_df)
    return df_pos
