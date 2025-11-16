# src/app/app.py
import os
import psycopg2
import pandas as pd
import gradio as gr
from dotenv import load_dotenv
from functions import get_connection, show_customers, get_cleaned_info, get_info

# Load environment variables
load_dotenv()


# Simple Gradio app
'''
demo = gr.Interface(
    fn=show_customers,
    inputs=[],
    outputs="dataframe",
    title="Fintech Recommender Database Test",
    description="Displays first 5 customers from PostgreSQL"
)
'''
demo = gr.Interface(
    fn=get_cleaned_info,
    inputs=gr.Textbox(label="Customer ID"),
    outputs="dataframe",
    title="Customer Full Data Viewer",
    description="Shows customer info + their transactions + assets + markets"
)
if __name__ == "__main__":
    demo.launch()
