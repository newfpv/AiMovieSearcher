import asyncio
import os
import re
import time
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.exceptions import TelegramRetryAfter
from google import genai
from google.genai import types as genai_types

logging.basicConfig(level=logging.INFO)

TELEGRAM_TOKEN = os.getenv("TG_BOT_TOKEN")
raw_keys = os.getenv("API_KEYS", "")
API_KEYS = [k.strip() for k in raw_keys.split(",") if k.strip()]

if not TELEGRAM_TOKEN or not API_KEYS:
    raise ValueError("❌ Error: TG_BOT_TOKEN or API_KEYS is not set in docker-compose.yml!")

GROUP_THREAD_MAP = {}
raw_map = os.getenv("GROUP_THREAD_MAP", "") 
if raw_map:
    groups = raw_map.split(";")
    for g in groups:
        g = g.strip()
        if not g:
            continue
        if ":" in g:
            gid, tids = g.split(":")
            GROUP_THREAD_MAP[int(gid.strip())] = [int(t.strip()) for t in tids.split(",") if t.strip()]
        else:
            GROUP_THREAD_MAP[int(g)] = []

MODEL_FALLBACK_LIST = [
    "gemini-3-flash-preview", 
    "gemini-2.5-flash",
    "gemini-3.1-flash-lite-preview",
    "gemini-2.5-flash-lite"
]

SAFE_CONFIG = genai_types.GenerateContentConfig(
    safety_settings=[
        genai_types.SafetySetting(category="HARM_CATEGORY_HATE_SPEECH", threshold="BLOCK_NONE"),
        genai_types.SafetySetting(category="HARM_CATEGORY_HARASSMENT", threshold="BLOCK_NONE"),
        genai_types.SafetySetting(category="HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold="BLOCK_NONE"),
        genai_types.SafetySetting(category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold="BLOCK_NONE"),
    ]
)

api_key_states = {k: {"unban_time": 0, "exhausted_models": set()} for k in API_KEYS}
key_lock = asyncio.Lock()

async def fetch_movie_info(prompt: str) -> str:
    start_t = time.time()
    
    while True:
        if time.time() - start_t > 60:
            return "⏳ Sorry, all keys and models are currently overloaded. Please try again later."

        selected_key = None
        selected_model = None

        async with key_lock:
            now = time.time()
            for model in MODEL_FALLBACK_LIST:
                for key, state in api_key_states.items():
                    if now >= state["unban_time"] and model not in state["exhausted_models"]:
                        selected_key = key
                        selected_model = model
                        state["unban_time"] = now + 999
                        break
                if selected_key:
                    break

        if not selected_key:
            await asyncio.sleep(1)
            continue

        key_mask = f"{selected_key[:6]}...{selected_key[-4:]}"
        logging.info(f"🚀 Request: {selected_model} | Key: {key_mask}")

        try:
            client = genai.Client(api_key=selected_key)
            
            response = await asyncio.to_thread(
                lambda: client.models.generate_content(
                    model=selected_model,
                    contents=prompt,
                    config=SAFE_CONFIG
                )
            )
            
            result_text = response.text.strip() if response.text else "⚠️ Empty response from AI."
            
            async with key_lock:
                api_key_states[selected_key]["unban_time"] = time.time() + 3
            
            return result_text
            
        except Exception as e:
            err_msg = str(e).lower()
            async with key_lock:
                if any(x in err_msg for x in ['429', 'resource_exhausted', 'quota']):
                    logging.warning(f"💀 Limit reached ({selected_model}) on key {key_mask}.")
                    api_key_states[selected_key]["exhausted_models"].add(selected_model)
                    api_key_states[selected_key]["unban_time"] = time.time() 
                elif any(x in err_msg for x in ['404', 'not_found']):
                    logging.warning(f"⚠️ Model {selected_model} is unavailable for key {key_mask}.")
                    api_key_states[selected_key]["exhausted_models"].add(selected_model)
                    api_key_states[selected_key]["unban_time"] = time.time()
                else:
                    logging.error(f"❌ Error on key {key_mask}: {err_msg[:80]}")
                    api_key_states[selected_key]["unban_time"] = time.time() + 10

bot = Bot(token=TELEGRAM_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

def extract_url(text: str) -> str | None:
    urls = re.findall(r'(https?://[^\s]+)', text)
    return urls[0] if urls else None

@dp.message(F.text)
async def handle_msg(message: types.Message):
    chat_id = message.chat.id
    thread_id = message.message_thread_id

    if GROUP_THREAD_MAP and chat_id not in GROUP_THREAD_MAP:
        return

    if GROUP_THREAD_MAP:
        allowed_threads = GROUP_THREAD_MAP[chat_id]
        if allowed_threads and thread_id not in allowed_threads:
            return

    user_text = message.text
    url = extract_url(user_text)
    clean_title = re.sub(r'https?://[^\s]+', '', user_text).strip()

    if not clean_title:
        return

    prompt = f"""Find information about the movie, cartoon, or TV series based on the following query: "{clean_title}".
Output the response STRICTLY in this HTML format, without asterisks or extra words:

<b><u>Title (Year)</u></b>
<b>Type, Genre:</b> values as plain text
<b>Description:</b> description text as plain text"""

    try:
        try:
            await bot.send_chat_action(chat_id=chat_id, action="typing", message_thread_id=thread_id)
        except Exception:
            pass
            
        reply_text = await fetch_movie_info(prompt)

        if url and not reply_text.startswith("⏳"):
            reply_text += f"\n\n🔗 <a href='{url}'>Link to watch</a>"

        while True:
            try:
                await message.answer(
                    reply_text, 
                    disable_web_page_preview=False
                )
                break
            except TelegramRetryAfter as e:
                logging.warning(f"⏳ Flood control (SendMessage). Waiting {e.retry_after} seconds...")
                await asyncio.sleep(e.retry_after)
        
        try:
            await message.delete()
        except TelegramRetryAfter:
            pass
        except Exception as e:
            logging.error(f"Failed to delete message: {e}")

    except Exception as e:
        logging.error(f"Critical error in handler: {e}")

async def main():
    logging.info(f"Bot started! Configured allowed IDs: {len(GROUP_THREAD_MAP)}")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())