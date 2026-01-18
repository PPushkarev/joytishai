# app/services/judge_engine.py
#

import json
import logging
import os

from motor.motor_asyncio import AsyncIOMotorClient
from openai import AsyncOpenAI

from app.services.prompts import EVAL_PROMPT

# Configure Logger
logger = logging.getLogger(__name__)

# Initialize OpenAI Client (Single instance)
openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))


async def execute_judge_cycle(mongo_uri: str):
    """
    Core Logic for the AI Judge.
    Fetches 'pending' logs from MongoDB and evaluates them using GPT-4o.
    """
    # Create a fresh DB connection (works for both API and Script)
    client = AsyncIOMotorClient(mongo_uri)
    db = client.joytishai_db
    collection = db.ai_logs

    logger.info("👨‍⚖️ [JUDGE ENGINE] Starting evaluation cycle...")
    print("👨‍⚖️ AI Judge started working...")

    # Fetch 5 oldest pending logs to process
    cursor = (
        collection.find({"evaluation.status": "pending"}).sort("timestamp", 1).limit(5)
    )
    logs = await cursor.to_list(length=5)

    if not logs:
        msg = "💤 No pending logs found. Judge is going back to sleep."
        logger.info(msg)
        print(msg)
        return {"status": "idle", "processed": 0}

    count = 0
    for log in logs:
        try:
            # 1. Prepare Data
            # Handle list or string context
            context_list = log.get("context", []) or []
            context_str = (
                " ".join(context_list)
                if isinstance(context_list, list)
                else str(context_list)
            )

            # Handle query serialization
            query_raw = log.get("user_query", "")
            if isinstance(query_raw, dict):
                query_str = json.dumps(query_raw, ensure_ascii=False)
            else:
                query_str = str(query_raw)

            response_text = str(log.get("response", ""))

            # 2. Call GPT-4o
            completion = await openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "user",
                        "content": EVAL_PROMPT.format(
                            context=context_str, query=query_str, response=response_text
                        ),
                    }
                ],
                response_format={"type": "json_object"},
            )

            # 3. Parse and Save Results
            result = json.loads(completion.choices[0].message.content)

            # Calculate average score (Faithfulness + Relevancy / 2)
            avg_score = (result.get("faithfulness", 0) + result.get("relevancy", 0)) / 2

            await collection.update_one(
                {"_id": log["_id"]},
                {
                    "$set": {
                        "evaluation.faithfulness": result.get("faithfulness"),
                        "evaluation.relevancy": result.get("relevancy"),
                        "evaluation.status": "evaluated",
                        "evaluation.comment": result.get("comment"),
                        "evaluation.score": avg_score,
                    }
                },
            )
            print(f"✅ Evaluated Log ID: {log['_id']} | Score: {avg_score}")
            count += 1

        except Exception as e:
            logger.error(f"❌ Error processing log {log['_id']}: {e}")
            print(f"❌ Error: {e}")
            # Mark as error to prevent infinite loops on bad data
            await collection.update_one(
                {"_id": log["_id"]},
                {
                    "$set": {
                        "evaluation.status": "error",
                        "evaluation.error_msg": str(e),
                    }
                },
            )

    return {"status": "success", "processed": count}
