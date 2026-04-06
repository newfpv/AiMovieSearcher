import json
import os
import logging
from dotenv import load_dotenv

load_dotenv()

LANG_FILE = os.getenv("LANG_FILE", "language.json")
translations = {}

try:
    with open(LANG_FILE, "r", encoding="utf-8") as f:
        translations = json.load(f)
    logging.info(f"✅ Файл локализации загружен: {LANG_FILE}")
except Exception as e:
    logging.error(f"❌ Ошибка загрузки файла локализации {LANG_FILE}: {e}")

def _(key: str, **kwargs) -> str:
    text = translations.get(key, key)
    if kwargs:
        try:
            return text.format(**kwargs)
        except KeyError as e:
            logging.warning(f"⚠️ Пропущен ключ форматирования {e} для строки '{key}'")
            return text
    return text