import gradio as gr

def recommend(user_id):
    # Dummy output for now
    return [f"Recommended item {i} for user {int(user_id)}" for i in range(1, 6)]

demo = gr.Interface(
    fn=recommend,
    inputs=gr.Number(label="User ID"),
    outputs=gr.JSON(label="Recommendations"),
    title="Asset Recommendation App",
    description="Enter your user ID to see sample recommendations."
)

if __name__ == "__main__":
    demo.launch()
