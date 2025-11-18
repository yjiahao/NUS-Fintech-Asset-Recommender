import pandas as pd
import gradio as gr
from dotenv import load_dotenv
from functions import get_connection, show_customers, get_cleaned_info, get_info
from neumf import NeuMF
import torch

load_dotenv()

# Runtime device and model checkpoint path
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
ckpt_path = "src/app/neumf_checkpoint.pth"

# Load asset info (ISIN -> assetName with sensible fallbacks)
ASSET_CSV_PATH = "initialize_db/raw/asset_information.csv"
isin_to_name = {}
try:
    _asset_df = pd.read_csv(ASSET_CSV_PATH, dtype=str)
    # Prefer full assetName; fallback to assetShortName; final fallback to ISIN
    name_series = _asset_df["assetName"].fillna("")  # type: ignore[index]
    short_series = _asset_df.get("assetShortName", "").fillna("")
    resolved_name = name_series.where(name_series.str.len() > 0, short_series)
    resolved_name = resolved_name.where(resolved_name.str.len() > 0, _asset_df["ISIN"])
    isin_to_name = dict(zip(_asset_df["ISIN"], resolved_name))
except Exception:
    isin_to_name = {}

# Load NeuMF checkpoint and mappings (if available)
model = None
user2id = {}
item2id = {}
_model_load_error = None

try:
    ckpt = torch.load(ckpt_path, map_location=DEVICE)
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
except Exception as e:
    _model_load_error = str(e)

# Generate top-K item recommendations for a given user_id
def recommend_for_user(user_id, model, user2id, item2id, topK=10, device="cpu"):
    if model is None:
        return [f"Model unavailable: {_model_load_error or 'NeuMF not found or checkpoint missing'}"]
    # Cast to string since mappings typically use string keys
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
    # Enrich with human-readable names from CSV
    mapped = [
        {
            "ISIN": item_id,
            "name": isin_to_name.get(item_id, item_id)
        }
        for item_id in recommended_items
    ]
    return mapped

def full_pipeline(user_id):
    """
    Fetch cleaned customer info (DB), then produce model recommendations.
    If DB is unavailable, return an empty DataFrame but still return recs.
    """
    try:
        df = get_cleaned_info(user_id)
    except Exception as e:
        df = pd.DataFrame()
    recs = recommend_for_user(
        user_id=user_id,
        model=model,
        user2id=user2id,
        item2id=item2id,
        topK=10,
        device=DEVICE
    )
    return df, recs

demo = gr.Interface(
    fn=full_pipeline,
    inputs=gr.Textbox(label="Customer ID"),
    outputs=[
        gr.Dataframe(label="Customer Info"),
        gr.JSON(label="Recommended Assets (Top 10)")
    ],
    title="AI-Driven Investment Recommender",
    description="Enter a Customer ID to view details + model recommendations."
)

if __name__ == "__main__":
    demo.launch()
