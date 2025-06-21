import os
import time
import asyncio
import requests
import nest_asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, CommandHandler, filters
from dotenv import load_dotenv

# Load .env
load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
SERPER_API_KEY = os.getenv("SERPER_API_KEY")

# Memory and debate mode
memory = {}
debate_mode = {}

# OpenRouter (GPT-4 Vision) API call
def call_openrouter(prompt, image_base64=None):
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "openai/gpt-4-vision-preview",
        "messages": [{"role": "user", "content": [{"type": "text", "text": prompt}]}],
        "temperature": 0.7
    }
    response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=data)
    return response.json()["choices"][0]["message"]["content"]

# Web search via Serper
def web_search(query):
    headers = {"X-API-KEY": SERPER_API_KEY}
    json_data = {"q": query}
    response = requests.post("https://google.serper.dev/search", headers=headers, json=json_data)
    result = response.json()
    if "organic" in result:
        return result["organic"][0]["snippet"]
    return "No search results found."

# Command to toggle debate mode
async def debate_toggle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    debate_mode[user_id] = not debate_mode.get(user_id, False)
    status = "activated" if debate_mode[user_id] else "deactivated"
    await update.message.reply_text(f"Debate mode {status}.")

# Handle user messages
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    memory.setdefault(user_id, []).append({"user": text})

    if debate_mode.get(user_id, False):
        text = f"Debate this statement logically and persuasively: {text}"

    # Optional: Add search if keyword present
    if "search:" in text.lower():
        query = text.split("search:", 1)[1].strip()
        result = web_search(query)
        await update.message.reply_text(result)
        return

    start = time.time()
    reply = call_openrouter(text)
    end = time.time()

    memory[user_id].append({"bot": reply})
    await update.message.reply_text(f"{reply}\n\n🕒 Response time: {round(end - start, 2)}s")

# Main function
async def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CommandHandler("debate", debate_toggle))

    print("Bot is running...")
    await app.run_polling()

# Entry point
if __name__ == "__main__":
    nest_asyncio.apply()
    asyncio.run(main())