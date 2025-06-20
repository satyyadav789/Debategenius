import os
import time
import asyncio
import requests
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, ContextTypes,
    MessageHandler, filters
)
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
MODEL = "deepseek-ai/DeepSeek-R1-0528-Qwen3-8B"

# Global toggle for debate mode
debate_mode = False

# Generate response from OpenRouter
def get_deepseek_response(prompt):
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}]
    }

    start_time = time.time()
    response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload)
    end_time = time.time()

    print(f"[⏱️] Response time: {end_time - start_time:.2f} seconds")

    if response.status_code == 200:
        return response.json()['choices'][0]['message']['content']
    else:
        print("OpenRouter API Error:", response.status_code, response.text)
        return "❌ Error: Could not get response from DeepSeek AI."

# /debate command to toggle debate mode
async def toggle_debate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global debate_mode
    debate_mode = not debate_mode
    status = "activated 🔥" if debate_mode else "deactivated 💤"
    await update.message.reply_text(f"🧠 Debate mode {status}")

# Message handler
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text

    if debate_mode:
        prompt = f"Debate the user intelligently with logic and clarity. Be persuasive and assertive.\n\nUser: {user_input}"
    else:
        prompt = user_input

    reply = get_deepseek_response(prompt)
    await update.message.reply_text(reply)

# Main bot function
async def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("debate", toggle_debate))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("✅ Bot is running...")
    await app.run_polling()

# Run the bot
if __name__ == "__main__":
    import nest_asyncio
    nest_asyncio.apply()
    asyncio.run(main())

