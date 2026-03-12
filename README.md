# FMI 1200 Creator

Batch article generator — DeepSeek + Kimi + OpenAI GPT-4o compete per article, best output wins.

## Deploy to Streamlit Cloud (5 minutes)

1. Fork or push this repo to your GitHub account
2. Go to [share.streamlit.io](https://share.streamlit.io) and sign in
3. Click **New app** → pick your repo → set **Main file path** to `app.py`
4. Click **Advanced settings → Secrets** and paste this (fill in your keys):

```toml
DEEPSEEK_API_KEY = "sk-..."
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEEPSEEK_MODEL = "deepseek-chat"
KIMI_API_KEY = "sk-..."
KIMI_BASE_URL = "https://api.moonshot.cn/v1"
KIMI_MODEL = "moonshot-v1-32k"
OPENAI_API_KEY = "sk-..."
```

5. Click **Deploy** — done.

> **Important:** Streamlit Cloud has an ephemeral filesystem. DOCX files are lost on restart.
> Always download the ZIP from the Outputs tab immediately after each batch run.
