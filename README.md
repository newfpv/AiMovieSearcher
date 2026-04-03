<div align="center">

# 🎬 Ai Movie Searcher

**AI-Powered Telegram Bot for Movie Search**

<img src="https://img.shields.io/badge/Python-3.11+-blue.svg?style=for-the-badge&logo=python&logoColor=white" alt="Python">
<img src="https://img.shields.io/badge/Docker-Ready-2496ED.svg?style=for-the-badge&logo=docker&logoColor=white" alt="Docker">
<img src="https://img.shields.io/badge/aiogram-3.x-blue.svg?style=for-the-badge&logo=telegram&logoColor=white" alt="aiogram">
<img src="https://img.shields.io/badge/Google_Gemini-API-orange.svg?style=for-the-badge&logo=google&logoColor=white" alt="Gemini">
<img src="https://img.shields.io/badge/License-GPLv3-blue.svg?style=for-the-badge" alt="License">

[🇷🇺 Read in Russian](https://github.com/newfpv/AiMovieSearcher/blob/main/READMERU.md)

<img src="https://github.com/newfpv/AiMovieSearcher/blob/main/demo.gif" alt="Bot Demo" width="600">

</div>

An automated bot designed to fetch detailed information about movies, cartoons, and TV series using artificial intelligence. Powered by the latest Google Gemini neural networks, it features deep YouTube link parsing, automated API key rotation to bypass rate limits, and flexible configuration via a `.env` file.

## ✨ Features

  - **Deep YouTube Parsing:** The bot doesn't just look at the link. It automatically extracts the **video title, full description, and all available subtitles** (using `yt-dlp` and `youtube-transcript-api`). This allows it to flawlessly identify movies even from short Shorts or TikTok edits without a title.
  - **AI Processing with Google Search:** Uses Gemini's native Google Search integration. The neural network googles obscure quotes, character names, or plot details in real-time during analysis.
  - **Smart Key & Model Rotation:** Supports an unlimited list of API keys. If a key or model hits a rate limit (Error 429), the bot instantly switches to the next available option without crashing.
  - **Universal Search:** Searches not only by video links but also by plain text. You can simply write a rough plot description or a memorable character quote.
  - **Auto-Cleanup:** The bot automatically deletes the user's original message (with the link) after successfully delivering the result, keeping the group chat perfectly clean.
  - **Fully Asynchronous:** Written on the modern `aiogram 3` framework. The bot doesn't freeze and easily handles simultaneous requests from multiple users.
  - **Formatting Error Protection:** If the AI makes a mistake and outputs broken HTML, the bot automatically strips the tags and sends plain text to avoid `TelegramBadRequest` errors.
  - **Easy Localization:** Customize the UI button texts ("Trailer on YouTube", "Source") directly in the `.env` configuration file without modifying the code.
  - **Chat Whitelist:** Strictly restricts bot responses to allowed Group IDs and specific Thread IDs (topics) to prevent spam and misuse.
  - **Docker Ready:** Simple, fast, and clean deployment with a single command via `docker-compose`.

## 🧰 Tech Stack

  * **Language:** Python 3.11
  * **Framework:** aiogram 3.x
  * **AI:** Google Gemini API (Flash / Flash Lite)
  * **Parsing:** yt-dlp, youtube-transcript-api
  * **Deployment:** Docker & Docker Compose

## 🤖 How it works

1.  **Request:** The user sends a YouTube / Shorts link (or a simple text description of the movie) to the chat. The bot immediately shows a "typing..." status.
2.  **Data Collection:** If a link is detected, the bot engages the parsers. `yt-dlp` instantly extracts the original video title and description, while `youtube-transcript-api` downloads the subtitles (even auto-generated ones).
3.  **Context Formatting:** The bot merges the user's text, title, description, and up to 5,000 characters of subtitles into a single data array.
4.  **AI Analysis:** All collected text is sent to Gemini. The neural network reads the dialogues from subtitles, performs hidden Google Searches to fact-check if necessary, and determines the exact movie title.
5.  **Result Output:** The bot returns a beautifully formatted message (title, year, genre, plot synopsis), automatically generates a button for a trailer search, and provides a link to the original video. The user's original message is deleted in the process.

## 🔑 How to Get a Google API Key

Google provides free API keys for its neural networks, subject to daily limitations.

**Instructions:**

1.  Go to [Google AI Studio](https://aistudio.google.com).
2.  Sign in with your Google account.
3.  Click **"Get API key"** in the left menu.
4.  Generate and copy your key. *(Tip: It is highly recommended to generate 3-4 keys from different accounts and comma-separate them in the config to ensure stable bot performance).*

### 📊 Free Model Limits:

  - **Gemini 3 Flash:** 20 requests / day
  - **Gemini 2.5 Flash:** 20 requests / day
  - **Gemini 3.1 Flash Lite:** 500 requests / day
  - **Gemini 2.5 Flash Lite:** 20 requests / day

## 🚀 Installation & Setup

**1. Clone the repository**

```bash
git clone https://github.com/newfpv/AiMovieSearcher.git
cd AiMovieSearcher
```

**2. Configure your environment**
Rename the `.env.example` file to `.env` and fill in your actual data:

```bash
cp .env.example .env
nano .env
```

*Open the `.env` file and set your `TG_BOT_TOKEN`, `API_KEYS` (comma-separated), and UI button texts. You can also configure the `GROUP_THREAD_MAP` to restrict the bot to specific chats.*

**3. Run the bot**
Make sure you have Docker installed, then run:

```bash
docker-compose up -d --build
```

## 🛠 Customization

You can easily tweak the bot's behavior by editing the `.env` file:

  - **Change Models:** Modify the `MODEL_FALLBACK_LIST`. A full list of available Google Gemini models can be found [here](https://ai.google.dev/gemini-api/docs/models).
  - **Adjust the Prompt:** Modify the `SYSTEM_PROMPT` variable to change the response language, adjust the formatting, or add new criteria to the search results.
  - **Translate Buttons:** Change `TRAILER_BTN_TEXT` and `SOURCE_BTN_TEXT` to match your local language.

## ⚙️ Troubleshooting

  - **ModuleNotFoundError: No module named 'dotenv':** You ran the bot with an old Docker cache. Force a rebuild using `docker-compose build --no-cache` and then `docker-compose up -d`.
  - **Bot ignores messages:** Check your `GROUP_THREAD_MAP` configuration in the `.env` file. Ensure the Group IDs and Thread IDs are correct. If left completely empty, the bot will respond to everyone.
  - **API Errors (429 RESOURCE\_EXHAUSTED):** You have hit the Google API daily limits. Add more keys to the `API_KEYS` variable. The bot will automatically rotate them.

## 📄 License

This project is distributed under the GNU GPLv3 license. See the [LICENSE](https://www.google.com/search?q=LICENSE) file for details.

## ☕ Support

<div align="left"><a href="https://www.donationalerts.com/r/newfpv"><img src="https://img.shields.io/badge/Donate-Buy%20Me%20A%20Coffee-yellow.svg" alt="Donate"></a\></div\>
