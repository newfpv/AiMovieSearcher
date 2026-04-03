import asyncio
import os
import re
import time
import logging
import urllib.parse

from aiogram import Bot, Dispatcher, types, F
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.exceptions import TelegramRetryAfter, TelegramBadRequest
from aiogram.utils.chat_action import ChatActionSender

from google import genai
from google.genai import types as genai_types

import yt_dlp
from youtube_transcript_api import YouTubeTranscriptApi
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)

TELEGRAM_TOKEN = os.getenv("TG_BOT_TOKEN")
raw_keys = os.getenv("API_KEYS", "")
API_KEYS = [k.strip() for k in raw_keys.split(",") if k.strip()]

if not TELEGRAM_TOKEN or not API_KEYS:
    raise ValueError("❌ Error: TG_BOT_TOKEN or API_KEYS is not set!")

GROUP_THREAD_MAP = {}
raw_map = os.getenv("GROUP_THREAD_MAP", "") 
if raw_map:
    groups = raw_map.split(";")
    for g in groups:
        g = g.strip()
        if ":" in g:
            gid, tids = g.split(":")
            GROUP_THREAD_MAP[int(gid.strip())] = [int(t.strip()) for t in tids.split(",") if t.strip()]
        else:
            GROUP_THREAD_MAP[int(g)] = []

raw_models = os.getenv("MODEL_FALLBACK_LIST", "gemini-3.1-flash-lite-preview,gemini-3-flash-preview,gemini-2.5-flash,gemini-2.5-flash-lite")
MODEL_FALLBACK_LIST = [m.strip() for m in raw_models.split(",") if m.strip()]

DEFAULT_PROMPT = """Use Google Search to find the movie/TV show title based on quotes.

INPUT DATA:
{query}

INSTRUCTIONS:
1. Find the movie using details: character names, unique phrases, and situations from the subtitles.
2. YOUR RESPONSE WILL BE INSERTED INTO CODE. ANY TEXT OTHER THAN HTML TAGS WILL BREAK THE SYSTEM.
3. STRICTLY PROHIBITED: writing "I found", "Here is the result", or duplicating blocks.
4. In the description — only a brief plot synopsis without spoilers.

OUTPUT STRICTLY AND ONLY THIS BLOCK:
<b><u>Title (Year)</u></b>
<b>Type, Genre:</b> values
<b>Description:</b> plot synopsis"""

raw_prompt = os.getenv("SYSTEM_PROMPT", DEFAULT_PROMPT)
SYSTEM_PROMPT_TEMPLATE = raw_prompt.replace("\\n", "\n")

TRAILER_BTN_TEXT = os.getenv("TRAILER_BTN_TEXT", "Trailer on YouTube")
SOURCE_BTN_TEXT = os.getenv("SOURCE_BTN_TEXT", "Source")

SAFE_CONFIG = genai_types.GenerateContentConfig(
    safety_settings=[
        genai_types.SafetySetting(category="HARM_CATEGORY_HATE_SPEECH", threshold="BLOCK_NONE"),
        genai_types.SafetySetting(category="HARM_CATEGORY_HARASSMENT", threshold="BLOCK_NONE"),
        genai_types.SafetySetting(category="HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold="BLOCK_NONE"),
        genai_types.SafetySetting(category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold="BLOCK_NONE"),
    ],
    tools=[{"google_search": {}}] 
)

api_key_states = {k: {"unban_time": 0, "exhausted_models": set()} for k in API_KEYS}
key_lock = asyncio.Lock()

def extract_youtube_id(url: str) -> str | None:
    patterns = [r"(?:v=|\/)([0-9A-Za-z_-]{11}).*", r"youtu\.be\/([0-9A-Za-z_-]{11})", r"shorts\/([0-9A-Za-z_-]{11})"]
    for p in patterns:
        match = re.search(p, url)
        if match: return match.group(1)
    return None

def fetch_youtube_data_sync(url: str) -> str:
    """Synchronous function: fetches title/description via yt-dlp, and subs via youtube-transcript-api"""
    video_id = extract_youtube_id(url)
    if not video_id: return f"URL: {url}"
    
    context = ""

    ydl_opts = {
        'quiet': True,
        'skip_download': True,
        'no_warnings': True,
        'extract_flat': False
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            title = info.get('title', '')
            description = info.get('description', '')
            
            context += f"Video Title: {title}\n"
            if description:
                context += f"Video Description: {description[:1000]}\n"
            logging.info(f"✅ Title and description fetched via yt-dlp for {video_id}")
    except Exception as e:
        logging.error(f"❌ yt-dlp error for {video_id}: {e}")

    try:
        ytt_api = YouTubeTranscriptApi()
        transcript_list = ytt_api.list(video_id)
        transcript = transcript_list.find_transcript(['ru', 'en'])
        transcript_data = transcript.fetch()
        
        clean_subs = " ".join([segment.text for segment in transcript_data])
        clean_subs = clean_subs.replace('\n', ' ').strip()
        
        context += f"\nSubtitles: {clean_subs[:5000]}"
        logging.info(f"✅ Subtitles successfully downloaded for {video_id} (language: {transcript.language})")
        
    except Exception as e:
        logging.warning(f"⚠️ Subtitles for {video_id} are missing or unavailable. Reason: {e}")
        
    return context


async def fetch_movie_info(prompt: str) -> str:
    start_time = time.time()
    timeout = 55

    while time.time() - start_time < timeout:
        selected_key = None
        selected_model = None
        now = time.time()

        async with key_lock:
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

        key_mask = f"{selected_key[:5]}...{selected_key[-4:]}"
        
        try:
            client = genai.Client(api_key=selected_key)
            
            response = await client.aio.models.generate_content(
                model=selected_model,
                contents=prompt,
                config=SAFE_CONFIG
            )

            if response.candidates and response.candidates[0].grounding_metadata:
                logging.info(f"🔎 Model {selected_model} used Google Search for the response.")

            result_text = response.text.strip() if response.text else "NOT_FOUND"

            async with key_lock:
                api_key_states[selected_key]["unban_time"] = time.time() + 2 
            
            return result_text

        except Exception as e:
            err_str = str(e).lower()
            async with key_lock:
                if "429" in err_str or "resource_exhausted" in err_str:
                    logging.warning(f"💀 Limit for {selected_model} on key {key_mask} exhausted.")
                    api_key_states[selected_key]["exhausted_models"].add(selected_model)
                    api_key_states[selected_key]["unban_time"] = time.time() 
                
                elif "400" in err_str or "invalid" in err_str:
                    logging.error(f"❌ Request error on key {key_mask}: {e}")
                    api_key_states[selected_key]["unban_time"] = time.time() + 5
                    return "NOT_FOUND" 
                
                else:
                    logging.error(f"⚠️ API error on key {key_mask} ({selected_model}): {e}")
                    api_key_states[selected_key]["unban_time"] = time.time() + 10

    return "⏳"

bot = Bot(token=TELEGRAM_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

@dp.message(F.text)
async def handle_msg(message: types.Message):
    if GROUP_THREAD_MAP and message.chat.id not in GROUP_THREAD_MAP: return
    if GROUP_THREAD_MAP and GROUP_THREAD_MAP.get(message.chat.id) and message.message_thread_id not in GROUP_THREAD_MAP[message.chat.id]: return

    async with ChatActionSender.typing(bot=bot, chat_id=message.chat.id, message_thread_id=message.message_thread_id):
        url_pattern = r'(?:https?://)?(?:www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b(?:[-a-zA-Z0-9()@:%_\+.~#?&//=]*)'
        url_match = re.search(url_pattern, message.text)
        clean_text = re.sub(url_pattern, '', message.text).strip()

        context = ""
        if url_match:
            try:
                context = await asyncio.to_thread(fetch_youtube_data_sync, url_match.group(0))
            except Exception as e:
                logging.error(f"YouTube parsing error: {e}")

        query = f"{clean_text}\n{context}".strip()
        if not query: return

        prompt = SYSTEM_PROMPT_TEMPLATE.replace("{query}", query)

        logging.info(f"\n{'='*40}\n🚀 SENDING TO GEMINI:\n{prompt}\n{'='*40}")

        try:
            reply = await fetch_movie_info(prompt)
            logging.info(f"📩 RESPONSE FROM GEMINI:\n{reply}")

            if "NOT_FOUND" in reply or not reply or reply == "⏳":
                try:
                    await bot.set_message_reaction(chat_id=message.chat.id, message_id=message.message_id, reaction=[types.ReactionTypeEmoji(emoji="🤷‍♂️")])
                except: pass
                return

            if "<b>" in reply:
                reply = reply[reply.find("<b>"):]

            movie_title = ""
            title_tag = re.search(r'<u>(.*?)</u>', reply)
            if title_tag:
                movie_title = title_tag.group(1)
            else:
                movie_title = reply.split('\n')[0].replace('<b>','').replace('</b>','').strip()

            if movie_title:
                q = urllib.parse.quote(f"Trailer {movie_title}")
                reply += f"\n\n🎬 <a href='https://www.youtube.com/results?search_query={q}'>{TRAILER_BTN_TEXT}</a>"
            
            if url_match:
                reply += f"\n🔗 <a href='{url_match.group(0)}'>{SOURCE_BTN_TEXT}</a>"

            while True:
                try:
                    await message.answer(reply, disable_web_page_preview=True)
                    break
                except TelegramRetryAfter as e:
                    await asyncio.sleep(e.retry_after)
                except TelegramBadRequest as e:
                    logging.error(f"HTML markup error: {e}")
                    clean_reply = re.sub(r'<[^>]*>', '', reply)
                    await message.answer(clean_reply, parse_mode=None, disable_web_page_preview=True)
                    break
            
            try: await message.delete()
            except: pass

        except Exception as e:
            logging.error(f"Critical handler error: {e}")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())