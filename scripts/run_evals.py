# STARTING EVALUATE OUR AI CONSULTATION USING MODEL GPT -4
# scripts/run_evals.py

import asyncio
import os
import sys

from dotenv import load_dotenv

# Add project root to system path so we can import 'app'
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.judge_engine import execute_judge_cycle

# Load .env variables (Locally)
load_dotenv()

if __name__ == "__main__":
    print("🚀 Starting Manual Judge Execution...")

    uri = os.getenv("MONGO_URI")

    if not uri:
        print("❌ CRITICAL ERROR: MONGO_URI is missing in .env file.")
    else:
        # Re-use the EXACT same logic as the API
        asyncio.run(execute_judge_cycle(uri))
        print("🏁 Execution finished.")
