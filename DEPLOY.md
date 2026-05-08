# Deploy the Streamlit demo for teammate review

> Goal: send teammates a URL they can open. Three options, all $0.
>
> **Recommended**: Streamlit Community Cloud (永久 URL, 官方支持).

---

## Option 1 — Streamlit Community Cloud (recommended, 永久)

**Time**: 5 min · **Cost**: $0 · **Persistence**: 永久（除非 90 天无活动）

### Pre-flight

The demo's **Cached demo** tab works without API keys — that's enough for
teammates to preview the visual + 4 cards + chart. The **Live agent** tab
needs 3 keys (Anthropic / Kaggle / OpenWeather) — skip those during
deployment unless your team is OK paying for live API calls from teammates'
queries.

### Steps

1. **Push to public GitHub repo** (do this in Terminal):
   ```bash
   cd "/Users/skc/SunKangChun/JHU carey/Genai/genai-final project"
   git init
   git add .
   git commit -m "Initial commit"
   gh repo create priceiq-agent --public --source=. --remote=origin --push
   ```
   (Or use the GitHub web UI: "New repo" → upload files manually.)

2. **Deploy at Streamlit Community Cloud**:
   - Go to https://share.streamlit.io
   - Sign in with GitHub
   - Click **New app**
   - Select your `priceiq-agent` repo
   - Main file path: `app.py`
   - Click **Deploy**

3. **Wait ~3 min**. You'll get a URL like:
   ```
   https://priceiq-agent.streamlit.app
   ```
   Send this to teammates.

### (Optional) Enable the Live agent tab

If teammates want to test live queries, add secrets in the app's
**Settings → Secrets**:
```toml
ANTHROPIC_API_KEY  = "sk-ant-..."
KAGGLE_API_TOKEN   = "KGAT_..."
OPENWEATHER_API_KEY = "..."
```
**Warning**: every query costs ~$0.029. Estimate teammate usage before
enabling.

---

## Option 2 — Hugging Face Spaces (永久, alt)

**Time**: 5 min · **Cost**: $0 · **Persistence**: 永久

Same idea as Streamlit Cloud, different platform.

1. Sign up at https://huggingface.co
2. Click **Create new Space** → SDK: **Streamlit**
3. Push your code:
   ```bash
   cd "/Users/skc/SunKangChun/JHU carey/Genai/genai-final project"
   git init
   git remote add origin https://huggingface.co/spaces/<username>/priceiq
   git add .
   git commit -m "Initial"
   git push -u origin main
   ```
4. URL: `https://huggingface.co/spaces/<username>/priceiq`

---

## Option 3 — localtunnel (临时, fastest)

**Time**: 30 s · **Cost**: $0 · **Persistence**: 本机要一直开机

Use this if teammates only need to look once and you don't want to push to
GitHub.

```bash
# Make sure Streamlit is running first:
streamlit run app.py
# In another terminal:
npx --yes localtunnel --port 8501
```

It prints a URL like `https://shy-eel-42.loca.lt`. **Caveat**: the first
visit shows a warning page asking for a "tunnel password" — that's just
your computer's public IP. Tell teammates to visit
`https://loca.lt/mytunnelpassword` in another tab to get the IP, paste it.

The URL dies when you Ctrl+C the tunnel or shut your laptop.

---

## Pre-deployment checklist

Before pushing to any platform:

- [ ] **Confirm `.gitignore` excludes** `.streamlit/secrets.toml` (if it exists)
- [ ] **Confirm `requirements.txt` is up to date** — Streamlit Cloud reads it to build the env
- [ ] **Test locally**: `streamlit run app.py` works, **Cached demo** tab renders
- [ ] **No hardcoded API keys** in any `.py` or `.toml` file:
  ```bash
  grep -rE "sk-ant-|KGAT_|api_key\s*=" --include="*.py" --include="*.toml" .
  ```
  If anything matches, scrub it before push.

---

## What teammates see

The Streamlit Community Cloud URL renders **the same demo you've been
reviewing locally**:

- **Cached demo tab** (default) — Garden / Sports samples, 4 recommendation
  cards, 3-scenario revenue chart, horizontal trace timeline
- **Live agent tab** — only works if you set the 3 secrets

No login required for viewers — anyone with the URL can open it.

---

## Cost notes

- Streamlit Cloud: $0 forever for public apps under 1GB RAM (this app is
  ~80MB). 92% pass rate / 31s latency are not affected by hosting.
- HF Spaces: $0 for the free tier, sleep after 48h idle, wake-on-request.
- localtunnel: $0, no signup, but bandwidth limited and depends on your
  laptop being awake.

If you ever need a *paid* host (e.g. for a Live agent that handles real
load), the cheapest sane option is Render's $7/month Starter — still well
inside a course budget if needed for the final week of class.
