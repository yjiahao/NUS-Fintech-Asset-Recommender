# src/app/app.py
import os
import psycopg2
import pandas as pd
import gradio as gr
from dotenv import load_dotenv
from supabase import create_client

from neumf import NeuMF
import torch

# Load environment variables
load_dotenv()

# Supabase connection
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# set up device
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
CHECKPOINT_PATH = "./models/neumf_checkpoint.pth"

# Connect to Postgres
def get_connection():
    conn = psycopg2.connect(
        host="db", # changed to db from localhost to connect to "db" in the container
        port=5432, # changed to port 5432 for use in the container, postgres running on 5432 there
        database=os.getenv("POSTGRES_DB"),
        user=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD")
    )
    return conn

# Sample test query
def show_customers():
    result = supabase.table("customers").select("*").limit(5).execute()
    df = pd.DataFrame(result.data)
    return df

def recommend_for_user(user_id, model, user2id, item2id, topK=10, device="cpu"):
    # cast user id to string
    user_key = str(user_id)
    if user_key not in user2id:
        return ["Error: user not found in training dataset"]
    
    u_idx = user2id[user_key]
    u_tensor = torch.tensor([u_idx], dtype=torch.long, device=device)
    n_items = len(item2id)
    item_tensor = torch.arange(n_items, dtype=torch.long, device=device)
    user_tensor = u_tensor.repeat(n_items)

    with torch.no_grad():
        scores = model(user_tensor, item_tensor)
    topk_idx = torch.topk(scores, topK).indices.cpu().numpy()
    id2item = {v: k for k, v in item2id.items()}
    recommended_items = [id2item[int(i)] for i in topk_idx]

    # Enrich with human-readable names from the database
    mapped = [
        {
            "ISIN": item_id,
            "name": isin_to_name.get(item_id, item_id)
        }
        for item_id in recommended_items
    ]
    return mapped

def enrich_predictions(mapped):
    isins = [item['ISIN'] for item in mapped]
    result = supabase.table("assets").select("isin, asset_name, asset_short_name").in_("isin", isins).execute()
    assets_df = pd.DataFrame(result.data)
    return assets_df

def get_purchase_history(user_id):
    # Get transactions
    transactions = supabase.table("transactions").select("*").eq("customer_id", user_id.strip()).execute().data
    
    if not transactions:
        return pd.DataFrame()
    
    # Get unique ISINs and market_ids
    isins = list(set([t["isin"] for t in transactions if t.get("isin")]))
    market_ids = list(set([t["market_id"] for t in transactions if t.get("market_id")]))
    
    # Get assets data
    assets = supabase.table("assets").select("isin, asset_name, asset_short_name, sector, industry").in_("isin", isins).execute().data
    assets_dict = {a["isin"]: a for a in assets}
    
    # Get markets data
    markets = supabase.table("markets").select("market_id, name").in_("market_id", market_ids).execute().data
    markets_dict = {m["market_id"]: m for m in markets}
    
    # Join the data
    flattened_data = []
    for t in transactions:
        asset = assets_dict.get(t.get("isin"), {})
        market = markets_dict.get(t.get("market_id"), {})
        flattened_data.append({
            "asset_name": asset.get("asset_name"),
            "asset_short_name": asset.get("asset_short_name"),
            "sector": asset.get("sector"),
            "industry": asset.get("industry"),
            "market_name": market.get("name"),
            "channel": t.get("channel"),
            "units": t.get("units"),
            "transaction_type": t.get("transaction_type"),
            "total_value": t.get("total_value"),
            "timestamp": t.get("timestamp")
        })
    
    # Sort by timestamp descending
    purchase_history = pd.DataFrame(flattened_data)
    if not purchase_history.empty:
        purchase_history = purchase_history.sort_values("timestamp", ascending=False)
    
    return purchase_history

def main(user_id):
    """
    Fetch cleaned customer info (DB), then produce model recommendations.
    If DB is unavailable, return an empty DataFrame but still return recs.
    """
    recs = recommend_for_user(
        user_id=user_id.strip("\n"),
        model=model,
        user2id=user2id,
        item2id=item2id,
        topK=10,
        device=DEVICE
    )

    recs = enrich_predictions(recs)

    purchase_history = get_purchase_history(user_id)

    return purchase_history, recs

# load model and set to eval mode
ckpt = torch.load(CHECKPOINT_PATH, map_location=DEVICE)
params = ckpt["params"]
user2id = ckpt["user2id"]
item2id = ckpt["item2id"]

model = NeuMF(
    n_users=params["n_users"],
    n_items=params["n_items"],
    eg=params["eg"],
    em=params["em"],
    layers=tuple(params["layers"])
).to(DEVICE)
model.load_state_dict(ckpt["model_state_dict"])
model.eval()

# load a map from asset id to asset name
result = supabase.table("assets").select("*").execute()
_asset_df = pd.DataFrame(result.data)
# Prefer full assetName; fallback to assetShortName; final fallback to ISIN
name_series = _asset_df["asset_name"].fillna("")  # type: ignore[index]
short_series = _asset_df.get("asset_short_name", "").fillna("")
resolved_name = name_series.where(name_series.str.len() > 0, short_series)
resolved_name = resolved_name.where(resolved_name.str.len() > 0, _asset_df["isin"])
isin_to_name = dict(zip(_asset_df["isin"], resolved_name))

# Simple Gradio app
with gr.Blocks() as demo:
    gr.Markdown("# Fintech Asset Recommendations")
    with gr.Row():
        with gr.Column(scale=3):    
            customer_id = gr.Textbox()
            button = gr.Button("See recommendations")

        with gr.Column(scale=7):
            gr.Markdown("## Your purchase history")
            purchase_history = gr.Dataframe(label="Your purchase history")

            gr.Markdown("## Your recommended assets")
            recommendations = gr.Dataframe(label="Recommended Assets (Top 10)")

    # callback for when button gets clicked
    button.click(fn=main, inputs=customer_id, outputs=[purchase_history, recommendations])

if __name__ == "__main__":
    demo.launch()