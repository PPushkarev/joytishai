

# --- CONFIGURATION --
# streamlit run scripts/admin_panel_api.py



import streamlit as st
import pandas as pd
import requests
from datetime import datetime
import json

# --- CONFIGURATION ---
st.set_page_config(
    page_title="JyotishAI Monitor",
    page_icon="🔮",
    layout="wide"
)

# ⚠️ REPLACE WITH YOUR RAILWAY DOMAIN
# If running locally: "http://localhost:8000"
BASE_URL = "https://web-production-991f4.up.railway.app"

API_STATS_URL = f"{BASE_URL}/api/v1/analytics/stats"
API_TRIGGER_URL = f"{BASE_URL}/api/v1/admin/run-judge"

# Custom Styling
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stMetric {
        background-color: #ffffff;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    </style>
    """, unsafe_allow_html=True)


# --- APP LOGIC ---
def main():
    # --- SIDEBAR CONTROLS ---
    st.sidebar.title("🎛 Control Panel")

    # 1. Refresh Button
    if st.sidebar.button("🔄 Refresh Data", type="primary", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    st.sidebar.divider()

    # 2. Trigger Judge Button
    st.sidebar.subheader("⚙️ Actions")
    if st.sidebar.button("🔨 Run Judge Process", use_container_width=True):
        with st.spinner("Sending signal to server..."):
            try:
                res = requests.post(API_TRIGGER_URL)
                if res.status_code == 200:
                    st.toast("Judge started successfully! 🚀", icon="✅")
                    st.sidebar.success("Signal sent. Refresh in 30s.")
                else:
                    st.sidebar.error(f"Error: {res.status_code}")
            except Exception as e:
                st.sidebar.error(f"Connection Failed: {e}")

    # --- MAIN CONTENT ---
    st.title("📊 AI Quality Monitor")
    st.caption(f"Connected to: {BASE_URL}")

    # Fetch Data
    try:
        response = requests.get(API_STATS_URL, timeout=10)
        if response.status_code != 200:
            st.error(f"❌ Server Error: {response.text}")
            return
        data = response.json()
    except Exception as e:
        st.error(f"❌ Connection Failed: {e}")
        return

    # Parse Data
    stats = data.get("statistics", {})
    recent_logs = data.get("recent_evaluations", [])

    # KPI Metrics
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)

    faith_score = stats.get("avg_faithfulness", 0) or 0
    rel_score = stats.get("avg_relevancy", 0) or 0

    with kpi1:
        st.metric("Total Consultations", stats.get("total_consultations", 0))
    with kpi2:
        st.metric("Avg Faithfulness", f"{faith_score}/5",
                  delta="Good" if faith_score > 3.5 else "Low",
                  delta_color="normal" if faith_score > 3.5 else "inverse")
    with kpi3:
        st.metric("Avg Relevancy", f"{rel_score}/5",
                  delta="Good" if rel_score > 3.5 else "Low",
                  delta_color="normal" if rel_score > 3.5 else "inverse")
    with kpi4:
        st.metric("Overall Score", f"{stats.get('avg_score', 0) or 0:.2f}/5")

    st.divider()

    # Logs Table
    st.subheader("📋 Recent Evaluations")

    if recent_logs:
        table_rows = []
        for log in recent_logs:
            # Time Formatting
            ts = log.get("timestamp", "")
            try:
                dt = datetime.fromisoformat(ts.replace("Z", ""))
                ts_display = dt.strftime("%Y-%m-%d %H:%M")
            except:
                ts_display = ts

            eval_data = log.get("evaluation", {})

            table_rows.append({
                "ID": log.get("_id"),
                "Time": ts_display,
                "User Query": str(log.get("user_query"))[:60] + "...",
                "Faithfulness": eval_data.get("faithfulness"),
                "Relevancy": eval_data.get("relevancy"),
                "Judge Comment": eval_data.get("comment", "")
            })

        df = pd.DataFrame(table_rows)

        # Highlight low scores
        def highlight_bad_rows(row):
            try:
                if float(row["Faithfulness"] or 0) < 3:
                    return ['background-color: #ffcccc'] * len(row)
            except:
                pass
            return [''] * len(row)

        st.dataframe(
            df.style.apply(highlight_bad_rows, axis=1),
            use_container_width=True,
            hide_index=True
        )

        # Deep Dive Inspector
        st.divider()
        st.subheader("🔍 Deep Dive Inspector")

        selected_id = st.selectbox("Select Log ID to inspect:", df["ID"])

        if selected_id:
            log_detail = next((item for item in recent_logs if item["_id"] == selected_id), None)

            if log_detail:
                c1, c2 = st.columns(2)
                with c1:
                    st.info("📥 Input Data")
                    raw_q = log_detail.get("user_query")
                    try:
                        st.json(json.loads(raw_q))
                    except:
                        st.write(raw_q)

                with c2:
                    st.warning("⚖️ Judge's Verdict")
                    st.write(log_detail.get("evaluation"))
    else:
        st.info("No evaluated data available yet.")


if __name__ == "__main__":
    main()