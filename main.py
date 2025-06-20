import os
import time
import asyncio
import nest_asyncio
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    MessageHandler,
    CommandHandler,
    filters,
)
import requests
from dotenv import load_dotenv

# Load .env
load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# Memory for context (session-based)
conversation_history = {}
debate_mode = {}

# Handle /debate toggle
async def toggle_debate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    debate_mode[user_id] = not debate_mode.get(user_id, False)
    status = "enabled" if debate_mode[user_id] else "disabled"
    await update.message.reply_text(f"🗣️ Debate mode is now {status}.")

# Query OpenRouter (DeepSeek or GPT-4)
def call_openrouter_api(messages, model="deepseek-chat"):
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": model,
        "messages": messages,
    }
    start = time.time()
    response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload)
    latency = time.time() - start
    if response.status_code == 200:
        text = response.json()['choices'][0]['message']['content']
        return text, latency
    return "⚠️ AI error: Could not get response.", latency

# Main handler
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_input = update.message.text

    # Get context
    if user_id not in conversation_history:
        conversation_history[user_id] = []
    conversation_history[user_id].append({"role": "user", "content": user_input})

    # Optional debate mode prompt
    if debate_mode.get(user_id, False):
        conversation_history[user_id].insert(0, {
            "role": "system",
            "content": "You are a debate agent. Argue clearly, persuasively, and take a strong stance."
        })

    reply, latency = call_openrouter_api(conversation_history[user_id])

    # Limit history size
    if len(conversation_history[user_id]) > 10:
        conversation_history[user_id] = conversation_history[user_id][-10:]

    conversation_history[user_id].append({"role": "assistant", "content": reply})

    await update.message.reply_text(f"{reply}\n\n⏱️ Response time: {latency:.2f}s")

# Run bot
async def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("debate", toggle_debate))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("Bot is running...")
    await app.run_polling()

if __name__ == "__main__":
    nest_asyncio.apply()
    asyncio.run(main())