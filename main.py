import os
import time
import asyncio
import requests
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, ContextTypes,
    CommandHandler, MessageHandler, filters
)
from dotenv import load_dotenv
import nest_asyncio

# Load environment variables
load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
SERPER_API_KEY = os.getenv("SERPER_API_KEY")

# In-memory session state
user_state = {}

# Debate mode toggle
def is_debate_mode(chat_id):
    return user_state.get(chat_id, {}).get("debate", False)

def set_debate_mode(chat_id, value: bool):
    user_state.setdefault(chat_id, {})["debate"] = value

# GPT-4-Vision (text only mode here)
async def query_openrouter_gpt(prompt: str):
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "openrouter/gpt-4-vision-preview",
        "messages": [
            {"role": "system", "content": "You are a helpful and intelligent assistant."},
            {"role": "user", "content": prompt}
        ]
    }

    start = time.time()
    response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload)
    latency = time.time() - start
    print(f"[INFO] Response time: {latency:.2f} seconds")

    if response.status_code == 200:
        return response.json()["choices"][0]["message"]["content"]
    else:
        print("OpenRouter Error:", response.status_code, response.text)
        return "Sorry, I couldn't reach the AI."

# Serper Web Search
async def web_search(query: str):
    headers = {
        "X-API-KEY": SERPER_API_KEY,
        "Content-Type": "application/json"
    }
    data = {"q": query}
    response = requests.post("https://google.serper.dev/search", headers=headers, json=data)

    if response.status_code == 200:
        results = response.json().get("organic", [])
        output = "\n\n".join([f"{r['title']}\n{r['link']}" for r in results[:3]])
        return output or "No results found."
    else:
        print("Serper API Error:", response.status_code, response.text)
        return "Web search failed."

# Main reply logic
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text
    chat_id = update.effective_chat.id

    if user_input.lower().startswith("search "):
        query = user_input[7:]
        result = await web_search(query)
        await update.message.reply_text(result)
        return

    prompt = user_input
    if is_debate_mode(chat_id):
        prompt = f"You are in debate mode. Argue your point clearly and logically.\nDebate this: {user_input}"

    reply = await query_openrouter_gpt(prompt)
    await update.message.reply_text(reply)

# Command handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hello! I'm your AI bot. Use /debate to toggle debate mode. Type 'search <topic>' to search the web.")

async def toggle_debate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    current = is_debate_mode(chat_id)
    set_debate_mode(chat_id, not current)
    await update.message.reply_text(f"Debate mode is now {'ON' if not current else 'OFF'}.")

# App start
async def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("debate", toggle_debate))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("Bot is running...")
    await app.run_polling()

if __name__ == "__main__":
    nest_asyncio.apply()
    asyncio.run(main())