import asyncio
import os
import re
import time
import math
import logging
import urllib.parse
import json
import requests

from aiogram import Bot, Dispatcher, types, F
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.exceptions import TelegramRetryAfter, TelegramBadRequest
from aiogram.utils.chat_action import ChatActionSender
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import Command

from google import genai
from google.genai import types as genai_types

import yt_dlp
from dotenv import load_dotenv

from i18n import _

load_dotenv()

logging.basicConfig(
    level=logging.INFO, 
    format="%(asctime)s - [%(levelname)s] - %(message)s",
    force=True
)

TELEGRAM_TOKEN = os.getenv("TG_BOT_TOKEN")
raw_keys = os.getenv("API_KEYS", "")
API_KEYS = [k.strip() for k in raw_keys.split(",") if k.strip()]

if not TELEGRAM_TOKEN or not API_KEYS:
    raise ValueError("❌ Error: TG_BOT_TOKEN or API_KEYS is not set!")

GROUP_THREAD_MAP = {}
raw_map = os.getenv("GROUP_THREAD_MAP", "") 
if raw_map:
    for g in raw_map.split(";"):
        if ":" in g:
            gid, tids = g.strip().split(":")
            GROUP_THREAD_MAP[int(gid)] = [int(t.strip()) for t in tids.split(",") if t.strip()]
        else:
            GROUP_THREAD_MAP[int(g.strip())] = []

raw_models = os.getenv("MODEL_FALLBACK_LIST", "gemini-3.1-flash-lite-preview,gemini-3-flash-preview,gemini-2.5-flash,gemini-2.5-flash-lite")
MODEL_FALLBACK_LIST = [m.strip() for m in raw_models.split(",") if m.strip()]

# Конфигурации Gemini
SIMPLE_CONFIG = genai_types.GenerateContentConfig(
    safety_settings=[
        genai_types.SafetySetting(category="HARM_CATEGORY_HATE_SPEECH", threshold="BLOCK_NONE"),
        genai_types.SafetySetting(category="HARM_CATEGORY_HARASSMENT", threshold="BLOCK_NONE"),
        genai_types.SafetySetting(category="HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold="BLOCK_NONE"),
        genai_types.SafetySetting(category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold="BLOCK_NONE"),
    ]
)
SEARCH_CONFIG = genai_types.GenerateContentConfig(
    safety_settings=SIMPLE_CONFIG.safety_settings,
    tools=[{"google_search": {}}] 
)

api_key_states = {
    k: {
        "unban_time": 0, 
        "model_unban_time": {m: 0 for m in MODEL_FALLBACK_LIST},
        "search_disabled_until": {m: 0 for m in MODEL_FALLBACK_LIST},
        "exhausted_models": set()
    } for k in API_KEYS
}
key_lock = asyncio.Lock()

bot = Bot(
    token=TELEGRAM_TOKEN, 
    default=DefaultBotProperties(
        parse_mode=ParseMode.HTML, 
        link_preview=types.LinkPreviewOptions(is_disabled=True)
    )
)
dp = Dispatcher()

# ==========================================
# УТИЛИТЫ И ПРОКСИ
# ==========================================
COOKIES_PATH = "data/cookies.txt" 
PROXY_PATH = "data/proxy.txt"
os.makedirs("data", exist_ok=True)

def get_proxy_url():
    if os.path.exists(PROXY_PATH):
        with open(PROXY_PATH, "r") as f:
            p = f.read().strip()
            if not p: return None
            parts = p.split(":")
            if len(parts) == 4: return f"http://{parts[2]}:{parts[3]}@{parts[0]}:{parts[1]}"
            elif len(parts) == 2: return f"http://{parts[0]}:{parts[1]}"
    return None

async def safe_edit(message: types.Message | types.CallbackQuery, text: str, reply_markup: InlineKeyboardMarkup = None):
    msg = message if isinstance(message, types.Message) else message.message
    try: await msg.edit_text(text, reply_markup=reply_markup)
    except: pass

class SettingsFSM(StatesGroup):
    wait_for_proxy = State()
    wait_for_cookies = State()

# ==========================================
# ГЛАВНОЕ МЕНЮ (БЕЗ КНОПКИ НАЗАД/ЗАКРЫТЬ)
# ==========================================
@dp.message(Command("start", "settings"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    if message.text == "/start": await message.answer(_("welcome_msg"))
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=_("btn_yt_cookies_menu"), callback_data="yt_cookies_menu")],
        [InlineKeyboardButton(text=_("btn_proxy_menu"), callback_data="proxy_menu")],
        [InlineKeyboardButton(text=_("btn_test_api"), callback_data="api_test_menu")]
    ])
    await message.answer("⚙️ <b>Настройки</b>", reply_markup=kb)

@dp.callback_query(F.data == "settings_back")
async def settings_back_handler(call: types.CallbackQuery, state: FSMContext):
    await state.clear()
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=_("btn_yt_cookies_menu"), callback_data="yt_cookies_menu")],
        [InlineKeyboardButton(text=_("btn_proxy_menu"), callback_data="proxy_menu")],
        [InlineKeyboardButton(text=_("btn_test_api"), callback_data="api_test_menu")]
    ])
    await safe_edit(call, "⚙️ <b>Настройки</b>", kb)

@dp.callback_query(F.data == "close_menu")
async def close_menu(call: types.CallbackQuery):
    try: await call.message.delete()
    except: pass

# ==========================================
# ЛОГИКА ГЕНЕРАЦИИ (FETCH_MOVIE_INFO)
# ==========================================
async def fetch_movie_info(prompt: str, media_bytes: bytes | None = None, mime_type: str | None = None) -> str:
    proxy_url = get_proxy_url()
    phases = [
        {"name": "PHASE_1", "use_search": True, "use_proxy": False},
        {"name": "PHASE_2", "use_search": False, "use_proxy": False},
    ]
    if proxy_url:
        phases.append({"name": "PHASE_3", "use_search": True, "use_proxy": True})
        phases.append({"name": "PHASE_4", "use_search": False, "use_proxy": True})

    for phase in phases:
        logging.info(_(f"log_{phase['name'].lower()}"))
        for model in MODEL_FALLBACK_LIST:
            for key in API_KEYS:
                now = time.time()
                state = api_key_states[key]
                if model in state["exhausted_models"] or now < state["unban_time"] or now < state["model_unban_time"].get(model, 0): continue
                if phase["use_search"] and now < state["search_disabled_until"].get(model, 0): continue

                km = f"{key[:5]}...{key[-4:]}"
                p_addr = proxy_url if phase["use_proxy"] else None
                logging.info(_("log_attempt", phase=phase["name"], model=model, km=km, search=phase["use_search"], proxy=bool(p_addr)))

                try:
                    async with key_lock: state["unban_time"] = now + 999 
                    cl = genai.Client(api_key=key, http_options={'proxy': p_addr} if p_addr else None)
                    cnt = [prompt]
                    if media_bytes and mime_type: cnt.append(genai_types.Part.from_bytes(data=media_bytes, mime_type=mime_type))
                    
                    config = SEARCH_CONFIG if phase["use_search"] else SIMPLE_CONFIG
                    res = await cl.aio.models.generate_content(model=model, contents=cnt, config=config)
                    txt = res.text.strip() if res.text else "NOT_FOUND"

                    async with key_lock: state["unban_time"] = time.time() + 2
                    logging.info(_("log_success", model=model, phase=phase["name"]))
                    return txt

                except Exception as e:
                    err = str(e).lower()
                    async with key_lock:
                        state["unban_time"] = 0
                        if "429" in err or "resource_exhausted" in err:
                            if "daily" in err or "quota" in err:
                                if "grounding" in err or "search" in err:
                                    logging.warning(_("log_search_fail", model=model))
                                    state["search_disabled_until"][model] = time.time() + 3600
                                else:
                                    logging.warning(_("log_exhausted", model=model, km=km))
                                    state["exhausted_models"].add(model)
                            else:
                                match = re.search(r'retry in (\d+)', err)
                                wt = int(match.group(1)) + 5 if match else 25
                                state["model_unban_time"][model] = time.time() + wt
                        else:
                            logging.error(_("log_api_error", model=model, err=err[:100]))
                            state["model_unban_time"][model] = time.time() + 10
    return "⏳"

# ==========================================
# ПРОКСИ И ТЕСТЫ
# ==========================================
@dp.callback_query(F.data == "proxy_menu")
async def proxy_menu(call: types.CallbackQuery, state: FSMContext):
    p = get_proxy_url() or "❌"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=_("btn_proxy_add"), callback_data="proxy_add")],
        [InlineKeyboardButton(text=_("btn_proxy_delete"), callback_data="proxy_delete")],
        [InlineKeyboardButton(text=_("btn_proxy_test"), callback_data="proxy_test")],
        [InlineKeyboardButton(text=_("btn_back"), callback_data="settings_back")]
    ])
    await safe_edit(call, _("proxy_menu_text", proxy=p), kb)

@dp.callback_query(F.data == "proxy_test")
async def proxy_test(call: types.CallbackQuery, state: FSMContext):
    p_url = get_proxy_url()
    if not p_url: await call.answer("❌", show_alert=True); return
    await safe_edit(call, _("proxy_test_running"))
    start = time.time()
    try:
        r = await asyncio.to_thread(requests.get, "https://www.google.com", proxies={"http":p_url, "https":p_url}, timeout=15)
        spd = round(time.time() - start, 2)
        status = _("proxy_test_ok", speed=spd) if r.status_code == 200 else _("proxy_test_fail", error=r.status_code)
    except Exception as e: status = _("proxy_test_fail", error=str(e)[:50])
    await safe_edit(call, status, InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=_("btn_back"), callback_data="proxy_menu")]]))

@dp.callback_query(F.data == "proxy_add")
async def proxy_add(call: types.CallbackQuery, state: FSMContext):
    await safe_edit(call, _("proxy_add_prompt"), InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=_("btn_cancel"), callback_data="proxy_menu")]]))
    await state.set_state(SettingsFSM.wait_for_proxy)

@dp.message(SettingsFSM.wait_for_proxy)
async def proxy_handler(message: types.Message, state: FSMContext):
    t = message.text.strip()
    if len(t.split(":")) not in [2, 4]: await message.answer(_("proxy_invalid_format")); return
    with open(PROXY_PATH, "w") as f: f.write(t)
    await message.answer(_("proxy_updated")); await state.set_state(None); await cmd_start(message, state)

@dp.callback_query(F.data == "proxy_delete")
async def proxy_delete(call: types.CallbackQuery, state: FSMContext):
    if os.path.exists(PROXY_PATH): os.remove(PROXY_PATH)
    await call.answer(_("proxy_deleted_alert")); await proxy_menu(call, state)

@dp.callback_query(F.data == "api_test_menu")
async def api_test_menu(call: types.CallbackQuery, state: FSMContext):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=_("btn_start_test_no_proxy"), callback_data="api_test:no")],
        [InlineKeyboardButton(text=_("btn_start_test_proxy"), callback_data="api_test:yes")],
        [InlineKeyboardButton(text=_("btn_back"), callback_data="settings_back")]
    ])
    await safe_edit(call, _("api_test_text"), kb)

@dp.callback_query(F.data.startswith("api_test:"))
async def api_test_start(call: types.CallbackQuery, state: FSMContext):
    use_p = call.data.split(":")[1] == "yes"
    p_url = get_proxy_url() if use_p else None
    total, cur = len(API_KEYS) * len(MODEL_FALLBACK_LIST), 0
    res_map = {i: [] for i in range(len(API_KEYS))}

    for i, key in enumerate(API_KEYS):
        cl = genai.Client(api_key=key, http_options={'proxy': p_url} if p_url else None)
        for model in MODEL_FALLBACK_LIST:
            cur += 1; pct = int((cur / total) * 100); bar = "▓" * (pct // 10) + "░" * (10 - (pct // 10))
            cur_txt = ""
            for idx, lines in res_map.items():
                if lines: cur_txt += f"🔑 <b>Key {idx+1}</b>\n" + "\n".join(lines) + "\n\n"
            await safe_edit(call, _("api_test_running", progress=f"[{bar}] {pct}%", step=f"Key {i+1} -> {model}", results=cur_txt))
            try:
                r = await cl.aio.models.generate_content(model=model, contents="Hi", config=SIMPLE_CONFIG)
                st = "🟢 OK" if r.text else "🟡 Empty"
            except Exception as e:
                err = str(e).lower()
                st = "⏳ RPM" if "429" in err else "💀 RPD" if "quota" in err else "🔴 Err"
            res_map[i].append(f"└ {model}: {st}"); await asyncio.sleep(0.4)
    fin = ""
    for i, lines in res_map.items(): fin += f"🔑 <b>Key {i+1}</b>\n" + "\n".join(lines) + "\n\n"
    await safe_edit(call, _("api_test_result_final", results=fin), InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=_("btn_back"), callback_data="api_test_menu")]]))

# ==========================================
# ПАРСИНГ YOUTUBE
# ==========================================
def extract_youtube_id(url: str) -> str | None:
    m = re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11}).*", url)
    return m.group(1) if m else None

def parse_subtitles_text(raw: str, ext: str) -> str:
    if not raw: return ""
    cl = ""
    try:
        if ext == 'json3':
            data = json.loads(raw)
            for ev in data.get('events', []):
                for seg in ev.get('segs', []):
                    u = seg.get('utf8', '').replace('\n', ' ')
                    if u.strip(): cl += u + " "
        else:
            for ln in raw.split('\n'):
                if '-->' in ln or ln.startswith(('WEBVTT', 'Kind:', 'Language:')): continue
                c_ln = re.sub(r'<[^>]+>', '', ln.strip())
                if c_ln and not c_ln.isdigit(): cl += c_ln + " "
    except Exception: return raw[:5000]
    return re.sub(r'\s+', ' ', cl).strip()

def fetch_youtube_data_sync(url: str):
    vid = extract_youtube_id(url)
    if not vid: return f"URL: {url}"
    opts = {
        'quiet': True, 'skip_download': True, 'no_warnings': True,
        'cookiefile': COOKIES_PATH if os.path.exists(COOKIES_PATH) else None,
        'subtitleslangs': ['ru', 'en'], 'subtitlesformat': 'json3/vtt/best',
        'writesubtitles': True, 'writeautomaticsub': True,
        'extractor_args': {'youtube': ['player_client=android,web']}
    }
    ctx = ""
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            inf = ydl.extract_info(url, download=False)
            ctx += _("yt_video_title", title=inf.get('title', ''))
            ctx += _("yt_video_desc", description=inf.get('description', '')[:1000])
            req = inf.get('requested_subtitles')
            if req:
                for lang in ['ru', 'en']:
                    if lang in req:
                        s = req[lang]
                        r = requests.get(s['url'], timeout=10)
                        if r.status_code == 200:
                            ctx += _("yt_subs_text", text=parse_subtitles_text(r.text, s.get('ext', 'json3'))[:5000])
                            break
    except Exception as e: logging.error(f"yt-dlp error: {e}")
    return ctx

# ==========================================
# ОБРАБОТЧИК СООБЩЕНИЙ
# ==========================================
@dp.message(F.text | F.photo | F.voice | F.video_note | F.audio)
async def handle_msg(message: types.Message, state: FSMContext):
    if await state.get_state() is not None: return
    if GROUP_THREAD_MAP and message.chat.id not in GROUP_THREAD_MAP: return
    if GROUP_THREAD_MAP and GROUP_THREAD_MAP.get(message.chat.id) and message.message_thread_id not in GROUP_THREAD_MAP[message.chat.id]: return

    async with ChatActionSender.typing(bot=bot, chat_id=message.chat.id):
        raw_text, mb, mt = (message.text or message.caption or ""), None, None
        if message.photo:
            f = await bot.get_file(message.photo[-1].file_id)
            mb = (await bot.download_file(f.file_path)).read(); mt = "image/jpeg"
        elif message.voice:
            f = await bot.get_file(message.voice.file_id)
            mb = (await bot.download_file(f.file_path)).read(); mt = "audio/ogg"
        elif message.video_note:
            f = await bot.get_file(message.video_note.file_id)
            mb = (await bot.download_file(f.file_path)).read(); mt = "video/mp4"
        elif message.audio:
            f = await bot.get_file(message.audio.file_id)
            mb = (await bot.download_file(f.file_path)).read(); mt = "audio/mpeg"

        url_match = re.search(r'(https?://[^\s]+)', raw_text)
        context = await asyncio.to_thread(fetch_youtube_data_sync, url_match.group(0)) if url_match else ""
        clean_text = re.sub(r'https?://[^\s]+', '', raw_text).strip()
        query = f"{clean_text}\n{context}".strip()
        
        if not query and not mb: return
        if not query: query = _("prompt_image") if mt == "image/jpeg" else _("prompt_audio_video")

        prompt = _("prompt_system_default", query=query)
        logging.info(f"\n{'='*60}\n🚀 SENDING TO GEMINI:\n{prompt}\n{'='*60}")
        reply = await fetch_movie_info(prompt, mb, mt)
        
        if "NOT_FOUND" in reply or reply == "⏳":
            try: await bot.set_message_reaction(chat_id=message.chat.id, message_id=message.message_id, reaction=[types.ReactionTypeEmoji(emoji="🤷‍♂️")])
            except: pass
            return

        movie_title = ""
        tag_match = re.search(r'<u>(.*?)</u>', reply)
        if tag_match: movie_title = tag_match.group(1)
        else: movie_title = reply.split('\n')[0].replace('<b>','').replace('</b>','')

        if movie_title:
            q = urllib.parse.quote(f"{_('btn_trailer')} {movie_title}")
            reply += f"\n\n🎬 <a href='https://www.youtube.com/results?search_query={q}'>{_('btn_trailer')}</a>"
        if url_match: reply += f"\n🔗 <a href='{url_match.group(0)}'>{_('btn_source')}</a>"

        try:
            await message.answer(reply); await message.delete()
        except:
            await message.answer(re.sub(r'<[^>]*>', '', reply), parse_mode=None)

# ==========================================
# КУКИ МЕНЮ
# ==========================================
@dp.callback_query(F.data == "yt_cookies_menu")
async def yt_cookies_menu(call: types.CallbackQuery, state: FSMContext):
    has = os.path.exists(COOKIES_PATH)
    status = _("yt_status_loaded") if has else _("yt_status_missing")
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=_("btn_yt_cookies_upload"), callback_data="yt_cookies_upload")],
        [InlineKeyboardButton(text=_("btn_yt_cookies_delete"), callback_data="yt_cookies_delete")] if has else [],
        [InlineKeyboardButton(text=_("btn_back"), callback_data="settings_back")]
    ])
    await safe_edit(call, _("yt_cookies_menu_text", status=status), kb)

@dp.callback_query(F.data == "yt_cookies_upload")
async def yt_cookies_upload(call: types.CallbackQuery, state: FSMContext):
    await safe_edit(call, _("yt_upload_prompt"), InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=_("btn_cancel"), callback_data="yt_cookies_menu")]]))
    await state.set_state(SettingsFSM.wait_for_cookies)

@dp.message(SettingsFSM.wait_for_cookies, F.document)
async def yt_cookies_doc_handler(message: types.Message, state: FSMContext):
    if not message.document.file_name.endswith('.txt'):
        await message.answer(_("yt_invalid_format")); return
    f = await bot.get_file(message.document.file_id)
    await bot.download_file(f.file_path, COOKIES_PATH)
    await message.answer(_("yt_cookies_updated"))
    await state.set_state(None); await cmd_start(message, state)

@dp.callback_query(F.data == "yt_cookies_delete")
async def yt_cookies_delete(call: types.CallbackQuery, state: FSMContext):
    if os.path.exists(COOKIES_PATH): os.remove(COOKIES_PATH)
    await call.answer(_("yt_cookies_deleted_alert")); await yt_cookies_menu(call, state)

async def main(): await dp.start_polling(bot)

if __name__ == "__main__": asyncio.run(main())