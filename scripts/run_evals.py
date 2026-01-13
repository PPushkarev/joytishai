


# STARTING EVALUATE OUR AI CONSULTATION USING MODEL GPT -4

import os
import json
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from openai import AsyncOpenAI
from dotenv import load_dotenv

# Importing the prompt from your services
from app.services.prompts import EVAL_PROMPT

# Load environment variables from .env
load_dotenv()

# Initialize Clients

client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
db_client = AsyncIOMotorClient(os.getenv("MONGO_URI"))
db = db_client.joytishai_db
collection = db.ai_logs


async def evaluate_pending_logs():
    """
    Fetches logs with 'pending' status and evaluates them using an AI Judge.
    Updates the database with scores and comments.
    """
    # 1. Search for logs that haven't been evaluated yet
    cursor = collection.find({"evaluation.status": "pending"})
    logs = await cursor.to_list(length=10)

    if not logs:
        print("No logs found for evaluation.")
        return

    for log in logs:
        print(f"Evaluating log ID: {log['_id']}")

        # Prepare data for the AI Judge
        # Joins RAG context if available, otherwise provides fallback text
        context_data = " ".join(log.get("context", ["Context not provided"]))
        user_query = log.get("user_query", "")

        # Convert response object/dict to string for the prompt
        ai_response_text = str(log.get("response", ""))

        # 2. Request to the AI Judge (using gpt-4o for high reasoning accuracy)
        try:
            eval_completion = await client.chat.completions.create(
                model="gpt-4o",
                messages=[{
                    "role": "user",
                    "content": EVAL_PROMPT.format(
                        context=context_data,
                        query=user_query,
                        response=ai_response_text
                    )
                }],
                response_format={"type": "json_object"}
            )

            # Parse the JSON response from the Judge
            evaluation_results = json.loads(eval_completion.choices[0].message.content)

            # 3. Update the document in MongoDB
            await collection.update_one(
                {"_id": log["_id"]},
                {"$set": {
                    "evaluation.faithfulness": evaluation_results.get("faithfulness"),
                    "evaluation.relevancy": evaluation_results.get("relevancy"),
                    "evaluation.status": "evaluated",
                    "evaluation.comment": evaluation_results.get("comment", "")
                }}
            )
            print(f"✅ Evaluation complete for {log['_id']}: {evaluation_results}")

        except Exception as e:
            print(f"❌ Error evaluating log {log['_id']}: {e}")


if __name__ == "__main__":
    # Standard entry point for async script execution
    asyncio.run(evaluate_pending_logs())