
# ADMIN DASHBOARD TO EVAULATE AI СONSULTATIONS
# streamlit run C:\Users\User\PycharmProjects\joytishai\scripts\admin_panel.py


import streamlit as st
from motor.motor_asyncio import AsyncIOMotorClient
import asyncio
import pandas as pd
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()






# Page Configuration
st.set_page_config(
    page_title="JyotishAI | Quality Monitor",
    page_icon="📊",
    layout="wide"
)

# Custom Styling
st.markdown("""
    <style>
    .main {
        background-color: #f5f7f9;
    }
    .stMetric {
        background-color: #ffffff;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    </style>
    """, unsafe_allow_html=True)


# Async Data Fetcher
async def fetch_logs():
    client = AsyncIOMotorClient(os.getenv("MONGO_URI"))
    db = client.joytishai_db
    collection = db.ai_logs
    # Fetch last 50 logs sorted by newest first
    cursor = collection.find().sort("timestamp", -1).limit(50)
    return await cursor.to_list(length=50)


# Main Application Logic
def main():
    st.sidebar.title("Navigation")
    app_mode = st.sidebar.selectbox("Choose a view", ["Dashboard", "Settings"])

    if app_mode == "Dashboard":
        st.title("📊 AI Quality Control Dashboard")
        st.caption("Monitoring LLM Faithfulness, Relevancy, and Hallucinations")

        # Fetch data
        try:
            logs = asyncio.run(fetch_logs())
        except Exception as e:
            st.error(f"Database Connection Error: {e}")
            return

        if not logs:
            st.info("No logs found in the database.")
            return

        # Prepare DataFrame
        data_rows = []
        for log in logs:
            evaluation = log.get("evaluation", {})
            data_rows.append({
                "Log ID": str(log["_id"]),
                "Timestamp": log.get("timestamp"),
                "User Query": str(log.get("user_query"))[:75] + "...",
                "Faithfulness": evaluation.get("faithfulness"),
                "Relevancy": evaluation.get("relevancy"),
                "Status": evaluation.get("status"),
                "Judge Verdict": evaluation.get("comment", "No comment")
            })

        df = pd.DataFrame(data_rows)

        # 1. Key Performance Indicators (KPIs)
        kpi1, kpi2, kpi3 = st.columns(3)

        avg_faith = df["Faithfulness"].dropna().mean()
        avg_rel = df["Relevancy"].dropna().mean()
        total_logs = len(df)

        with kpi1:
            st.metric("Avg Faithfulness", f"{avg_faith:.2f} / 5", delta=None)
        with kpi2:
            st.metric("Avg Relevancy", f"{avg_rel:.2f} / 5", delta=None)
        with kpi3:
            st.metric("Processed Logs", total_logs)

        st.divider()

        # 2. Main Log Table
        st.subheader("Latest Consultantion Logs")

        # Styling function for low scores
        def color_scores(val):
            if isinstance(val, (int, float)):
                if val <= 2: return 'background-color: #ffcccc; color: black;'
                if val >= 4: return 'background-color: #ccffcc; color: black;'
            return ''

        styled_df = df.style.applymap(color_scores, subset=['Faithfulness', 'Relevancy'])
        st.dataframe(styled_df, use_container_width=True)

        # 3. Deep Dive Inspector
        st.divider()
        st.subheader("🔍 Deep Dive Inspector")

        selected_id = st.selectbox("Select a Log ID to inspect", df["Log ID"])

        if selected_id:
            log_detail = next(item for item in logs if str(item["_id"]) == selected_id)

            col_left, col_right = st.columns(2)

            with col_left:
                st.info("📥 **Input (User Data)**")
                st.json(log_detail.get("user_query"))
                st.markdown("---")
                st.markdown("**RAG Context (Knowledge Base):**")
                st.write(log_detail.get("context", "No context provided"))

            with col_right:
                st.success("📤 **Output (AI Response)**")
                st.json(log_detail.get("response"))

                st.warning("⚖️ **Judge's Reasoning**")
                eval_info = log_detail.get("evaluation", {})
                st.write(f"**Status:** {eval_info.get('status')}")
                st.write(f"**Comment:** {eval_info.get('comment')}")


if __name__ == "__main__":
    main()