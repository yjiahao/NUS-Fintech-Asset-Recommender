# src/app/app.py
import os
import psycopg2
import pandas as pd
import gradio as gr
from dotenv import load_dotenv

from neumf import NeuMF
import torch

# Load environment variables
load_dotenv()

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
    conn = get_connection()
    df = pd.read_sql("SELECT * FROM customers LIMIT 5;", conn)
    conn.close()
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
    isins = [f"'{item['ISIN']}'" for item in mapped]  # add quotes for SQL strings
    isins_str = ",".join(isins)
    query = f"""
        SELECT 
            ISIN,
            asset_name,
            asset_short_name
        FROM assets
        WHERE isin IN ({isins_str});
    """
    conn = get_connection()
    assets_df = pd.read_sql(query, conn)
    return assets_df

def get_purchase_history(user_id):
    conn = get_connection()
    sql = f'''
    SELECT 
        a.asset_name,
        a.asset_short_name,
        a.sector,
        a.industry,
        m.name AS market_name,
        t.channel,
        t.units,
        t.transaction_type,
        t.total_value,
        t.timestamp
    FROM transactions t
    JOIN assets a ON t.ISIN = a.ISIN
    JOIN markets m ON t.market_id = m.market_id
    WHERE t.customer_id = '{user_id.strip()}'
    ORDER BY t.timestamp DESC;
    '''
    purchase_history = pd.read_sql(sql, conn)
    conn.close()
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
connection = get_connection()
_asset_df = pd.read_sql("SELECT * FROM assets;", connection)
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
