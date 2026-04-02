# Ai Movie Searcher  
**AI-Powered Telegram Bot for Movie Search**

An automated bot designed to fetch detailed information about movies, cartoons, and TV series using artificial intelligence. Powered by the latest Google Gemini neural networks, it features API key rotation to bypass rate limits and flexible settings to restrict operations to specific chats and threads.

[🇷🇺 Перевести на русский язык](https://github.com/newfpv/AiMovieSearcher/blob/main/READMERU.md)

![Demo](https://github.com/newfpv/AiMovieSearcher/blob/main/demo.gif)
## ✨ Features
- **AI Parsing:** Delivers structured descriptions, release years, types, and genres based on a single title query.
- **Smart Key Rotation:** Supports a list of multiple API keys. If a key or model hits a rate limit, the bot automatically switches to the next available one.
- **Modern Models:** Optimized for the latest Gemini generations (Flash and Flash Lite). 
- **Chat Whitelist:** Restricts bot responses to specifically allowed group and thread IDs.
- **Docker Ready:** Simple and fast deployment via `docker-compose`.

## 🔑 How to Get a Google API Key
Google provides free API keys for their neural networks, subject to requests-per-minute limitations.

**Instructions:**
1. Go to [Google AI Studio](https://aistudio.google.com).
2. Sign in with your Google account.
3. Look at the bottom-left corner of the screen and click **"Get API key"**.
4. Generate and copy your key. *(Tip: It is highly recommended to generate multiple keys from different accounts to ensure stable bot performance).*

### 📊 Free Model Limits:
- **Gemini 3 Flash:** 20 requests / day
- **Gemini 2.5 Flash:** 20 requests / day
- **Gemini 3.1 Flash Lite:** 500 requests / day
- **Gemini 2.5 Flash Lite:** 20 requests / day

## 🛠 Customization
You can easily tweak the bot's behavior by editing the source code:
- **Change Models:** You can replace the default models with others. A full list of available Google Gemini models can be found [here](https://ai.google.dev/gemini-api/docs/models).
- **Adjust the Prompt:** Modify the AI prompt inside the code to change the response language, adjust the formatting, or add new criteria to the search results.


## 🚀 Installation & Setup

**1. Clone the repository**
```bash
git clone [https://github.com/newfpv/AiMovieSearcher.git](https://github.com/newfpv/AiMovieSearcher.git)
cd AiMovieSearcher
```

**2. Configure your variables**
Open the `docker-compose.yml` file and find the `environment` section. Just replace the placeholders with your actual data:

```yaml
    environment:
      - TG_BOT_TOKEN=YOUR_BOTFATHER_TOKEN
      - API_KEYS=KEY_1,KEY_2,KEY_3 # Separate multiple keys with commas
      - GROUP_THREAD_MAP=12345678;-1234567643224:5 
```

**How `GROUP_THREAD_MAP` works:**
* `12345678` -> Works in direct messages with this user ID.
* `-1002` -> Works in the entire group `-1002`.
* `-1001:45` -> Works ONLY in thread `45` of group `-1001`.
* *Separate different IDs with a semicolon (`;`). If you want the bot to answer everyone, just leave this variable empty.*

**3. Run the bot**
```bash
docker-compose up -d --build
```

## ⚙️ Troubleshooting

  - **Bot replies "Sorry, keys are overloaded"** You have hit the Google API limits. Add more keys to the `API_KEYS` variable or wait a minute.
  - **Bot ignores messages:** Check your `GROUP_THREAD_MAP` configuration. Ensure the Group IDs and Thread IDs are correct. If left completely empty, the bot will respond to everyone.
  - **Flood control exceeded warning in logs:** Telegram is rate-limiting the bot's message sending. The bot will automatically wait the required time and retry; it will not crash.

## ☕ Support

\<div align="left"\>\<a href="https://www.donationalerts.com/r/newfpv"\>\<img src="https://img.shields.io/badge/Donate-Buy%20Me%20A%20Coffee-yellow.svg" alt="Donate"\>\</a\>\</div\>
