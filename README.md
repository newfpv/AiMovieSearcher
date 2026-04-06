<div align="center">

# 🎬 Ai Movie Searcher

**AI-based Telegram bot for movie search**

<img src="https://img.shields.io/badge/Python-3.11+-blue.svg?style=for-the-badge&logo=python&logoColor=white" alt="Python">
<img src="https://img.shields.io/badge/Docker-Ready-2496ED.svg?style=for-the-badge&logo=docker&logoColor=white" alt="Docker">
<img src="https://img.shields.io/badge/aiogram-3.x-blue.svg?style=for-the-badge&logo=telegram&logoColor=white" alt="aiogram">
<img src="https://img.shields.io/badge/Google_Gemini-API-orange.svg?style=for-the-badge&logo=google&logoColor=white" alt="Gemini">
<img src="https://img.shields.io/badge/License-GPLv3-blue.svg?style=for-the-badge" alt="License">


[Translate to Russian](https://github.com/newfpv/AiMovieSearcher/blob/main/READMERU.md)


<img src="https://github.com/newfpv/AiMovieSearcher/blob/main/demo.gif" alt="Bot Demo" width="600"> 

</div>

An automated bot created to search for detailed information about movies, cartoons, and TV series using artificial intelligence. It works on the basis of the latest Google Gemini neural networks. The bot can search for movies by text, YouTube links, voice messages, video clips, and even screenshots!

It has smart API key rotation, built-in settings menu, proxy support, and easy customization via configuration files.

-----

## ✨ Features

  * **Multimodal search (NEW):** The bot analyzes more than just text. Send him a picture (a frame from a movie), a voice message with the soundtrack humming, a video circle with a fragment of dialogue — Gemini will recognize the media files and find the right movie.
  * **Deep parsing of YouTube + Cookies:** Automatically extracts video title, description and subtitles. Supports file upload `cookies.txt "directly through Telegram to bypass YouTube's blockages and access videos with restrictions.
  * **Built-in settings menu (NEW):** The `/start` or `/settings` commands open a convenient Inline menu. You can manage proxies, download cookies, and run a smart API key test directly in the chat.
  * **Smart key and proxy rotation (NEW):** Maintains a list of API keys. If the key catches the limit, the bot switches to the next one. If all keys are temporarily blocked, the bot automatically activates the "Last Chance" mode and makes requests through a proxy.
  * **Multilingualism (Localization):** All the texts of the buttons, answers, and menus are stored in the 'language' file.json`. Change the language of the bot without interfering with the code.
  * **AI Processing with Google Search:** Uses built-in integration with Google Search. The neural network googles non-obvious details in real time right during the analysis.
  * **Whitelist of chats:** Restricts the bot's responses to only allowed group IDs and specific branches (topics) to prevent spam.
  * **Docker support:** Simple, fast and clean deployment with a single command while saving local data (proxy, cookies).

-----

## 🧰 Technology stack

  * **Language:** Python 3.11
* **Framework:** aiogram 3.x
* **AI:** Google GenAI SDK (Flash / Flash Lite)
  * **Parsing:** yt-dlp, requests
  * **Deployment:** Docker & Docker Compose

-----

## 🤖 How it works

1. **Request:** The user sends a text, link, picture, voice or a circle.
2. **Data collection:** If a YouTube link is found, the bot uses yt-dlp (and your cookies) to extract metadata and subtitles.
3. **Neural network analysis:** The collected text or media file is sent to Gemini. There is a multi-stage search (including access to Google Search, if necessary).
4. **Output of the result:** The bot returns a beautifully designed message (title, year, genre, plot plot), generates a button for the trailer and a link to the source. The user's original message is deleted to keep the chat clean.

-----

## 🔑 How to get a Google API Key

1. Go to [Google AI Studio](https://aistudio.google.com)
2. Log in using your Google account and click **"Get API key"**.
3. Generate and copy your key. *(Tip: It is strongly recommended to create 3-4 keys from different accounts and specify them separated by commas in the config for stable operation).*

-----

## 🚀 Installation and launch

**1. Cloning the repository**

```bash
git clone https://github.com/newfpv/AiMovieSearcher.git
cd AiMovieSearcher
```

**2. Setting up the environment**
Rename the `.env.example` file to `.env` and fill it in with your current data:

```bash
cp .env.example .env
nano .env
```

Specify your `TG_BOT_TOKEN', `API_KEYS' (separated by commas) and configure `GROUP_THREAD_MAP' if necessary.

**3. Launching the bot via Docker**

```bash
docker-compose up -d --build
```

-----

## 🔄 Update from the old version (Update Guide)

The new version of the bot has received a global update: added support for media files, a multilingual system (`language.json`), built-in settings menu and YouTube blocking protection.

To upgrade without errors and crashes, follow these instructions carefully.:

**Step 1. Download the latest code**

```bash
git pull origin main
```

*(Or simply replace the old files with new ones if you downloaded the archive).*

**Step 2. Update the configuration (.env)**
The logic of the environment variables has changed:

  * **Deleted:** `TRAILER_BTN_TEXT` and `SOURCE_BTN_TEXT'. All text is configured via `language.json`.
  * **Added:** The variable `LANG_FILE=language.json` for language selection.
  * **The prompt has been updated:** Instructions for working with images have been added to `SYSTEM_PROMPT`. Be sure to update your prompt by copying the current one from the '.env.example` file.

**Step 3. Check docker-compose.yml**
The bot now saves the proxy settings and cookies to the 'data` folder. Make sure that your file contains `docker-compose.yml` has this block:

```yaml
    volumes:
      - ./data:/app/data
      - ./:/app
```

**Step 4. Rebuild the Docker container**
The bot has a completely updated list of dependencies (new `google-genai'). **It is necessary** to rebuild the image from scratch:

```bash
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

Send the command `/start` or `/settings' to the chat to open a new control panel.

-----

## ⚙️ Problem solving

  * **API errors (429 RESOURCE\_EXHAUSTED):** You have reached your daily limits. Add more keys to `API_KEYS'. Open the menu `/settings` -\> "API Test" to check which keys are currently alive.
  * **YouTube does not provide subtitles or videos:** Google has started blocking server requests. Open the menu `/settings` -\> "YouTube Cookie Settings" and download the file `cookies.txt ` from your account (instructions for receiving are inside the bot itself).
  * **Keys are sent to the ban by IP:** Open `/settings` -\> "Proxy Settings" and add a working HTTP/SOCKS proxy. The bot will use it when local requests start being blocked.

-----

## 📄 License

This project is distributed under the GNU GPLv3 license.

## ☕ Support

<div align="left"><a href="https://www.donationalerts.com/r/newfpv"><img src="https://img.shields.io/badge/Donate-Buy%20Me%20A%20Coffee-yellow.svg" alt="Donate"></a\></div\>
