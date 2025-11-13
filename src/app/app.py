# src/app/app.py
import os
import psycopg2
import pandas as pd
import gradio as gr
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Connect to Postgres
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

# Simple Gradio app
demo = gr.Interface(
    fn=show_customers,
    inputs=[],
    outputs="dataframe",
    title="Fintech Recommender Database Test",
    description="Displays first 5 customers from PostgreSQL"
)

if __name__ == "__main__":
    demo.launch()
