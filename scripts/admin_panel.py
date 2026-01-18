import json
from datetime import datetime

import pandas as pd
import requests
import streamlit as st

# --- CONFIGURATION ---
st.set_page_config(page_title="JyotishAI Monitor", page_icon="🔮", layout="wide")

# ⚠️ ВАЖНО: УБЕДИСЬ, ЧТО ЭТО ТВОЙ АКТУАЛЬНЫЙ ДОМЕН RAILWAY
BASE_URL = "https://web-production-991f4.up.railway.app"

# Эндпоинты
API_STATS_URL = f"{BASE_URL}/api/v1/analytics/stats"
API_TRIGGER_URL = f"{BASE_URL}/api/v1/admin/run-judge"

# Custom Styling
st.markdown(
    """
    <style>
    .main { background-color: #f5f7f9; }
    .stMetric {
        background-color: #ffffff;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    .stExpander {
        background-color: #ffffff;
        border-radius: 5px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


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
        st.metric(
            "Avg Faithfulness",
            f"{faith_score}/5",
            delta="Good" if faith_score > 3.5 else "Low",
            delta_color="normal" if faith_score > 3.5 else "inverse",
        )
    with kpi3:
        st.metric(
            "Avg Relevancy",
            f"{rel_score}/5",
            delta="Good" if rel_score > 3.5 else "Low",
            delta_color="normal" if rel_score > 3.5 else "inverse",
        )
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

            table_rows.append(
                {
                    "ID": log.get("_id"),
                    "Time": ts_display,
                    "User Query": str(log.get("user_query"))[:60] + "...",
                    "Faithfulness": eval_data.get("faithfulness"),
                    "Relevancy": eval_data.get("relevancy"),
                    "Judge Comment": eval_data.get("comment", ""),
                }
            )

        df = pd.DataFrame(table_rows)

        # Highlight low scores
        def highlight_bad_rows(row):
            try:
                if float(row["Faithfulness"] or 0) < 3:
                    return ["background-color: #ffcccc"] * len(row)
            except:
                pass
            return [""] * len(row)

        st.dataframe(
            df.style.apply(highlight_bad_rows, axis=1),
            use_container_width=True,
            hide_index=True,
        )

        # --- FORENSIC INSPECTOR (Глубокий анализ) ---
        st.divider()
        st.header("🕵️‍♂️ Deep Dive Inspector (Forensics)")
        st.caption("Compare Raw Inputs -> Prepared Prompt -> AI Response.")

        selected_id = st.selectbox("Select Log ID to inspect:", df["ID"])

        if selected_id:
            # Находим полный объект лога
            log = next(
                (item for item in recent_logs if item["_id"] == selected_id), None
            )

            if log:
                # === СЕКЦИЯ 1: ПОТОК ДАННЫХ (3 КОЛОНКИ) ===
                st.subheader("1. Data Flow Analysis")
                c1, c2, c3 = st.columns(3)

                # КОЛОНКА 1: СЫРЫЕ ДАННЫЕ (API)
                with c1:
                    st.info("📥 1. Raw API Data")
                    st.caption("From Frontend (Python Object)")
                    raw_q = log.get("user_query")

                    if isinstance(raw_q, (dict, list)):
                        st.json(raw_q, expanded=False)
                    else:
                        st.code(str(raw_q), language="python")

                # КОЛОНКА 2: ОЧИЩЕННЫЕ ДАННЫЕ (ТО, ЧТО УШЛО В GPT)
                with c2:
                    st.warning("⚙️ 2. Clean Input (Prompt)")
                    st.caption("Converted text for AI. If empty = old log.")

                    # Пытаемся достать новое поле
                    formatted_input = log.get(
                        "formatted_input", "⚠️ Not saved (Old Log)"
                    )
                    st.text_area("Prompt Content", formatted_input, height=350)

                # КОЛОНКА 3: RAG КОНТЕКСТ
                with c3:
                    # ИСПРАВЛЕНО ЗДЕСЬ: st.secondary -> st.success
                    st.success("📚 3. RAG Context")
                    st.caption("Found in Knowledge Base.")
                    context_data = log.get("context")

                    if not context_data:
                        st.error("⚠️ Context is EMPTY!")
                    elif isinstance(context_data, list):
                        for i, chunk in enumerate(context_data):
                            with st.expander(f"Fragment #{i + 1}", expanded=False):
                                st.write(chunk)
                    else:
                        st.text_area("Full Context", str(context_data), height=350)

                st.divider()

                # === СЕКЦИЯ 2: ВЫХОДНЫЕ ДАННЫЕ ===
                st.subheader("2. AI Output & Verdict")
                c_out1, c_out2 = st.columns([2, 1])

                # КОЛОНКА 1: ОТВЕТ ИИ
                with c_out1:
                    st.success("🤖 AI Generated Response")
                    st.write(log.get("response"))

                # КОЛОНКА 2: ОЦЕНКА СУДЬИ
                with c_out2:
                    st.markdown("### ⚖️ Judge's Verdict")
                    eval_data = log.get("evaluation", {})

                    m1, m2 = st.columns(2)
                    m1.metric("Faithfulness", f"{eval_data.get('faithfulness', 0)}/5")
                    m2.metric("Relevancy", f"{eval_data.get('relevancy', 0)}/5")

                    st.markdown("**Judge's Comment:**")
                    st.info(eval_data.get("comment", "No comment"))

                    # Кнопка просмотра всего JSON
                    with st.expander("📂 SHOW FULL LOG (RAW JSON)"):
                        st.json(log)

    else:
        st.info("No evaluated data available yet. Click 'Run Judge Process'.")


if __name__ == "__main__":
    main()
