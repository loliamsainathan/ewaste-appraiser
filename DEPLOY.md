# Deploying for a permanent URL

The sandbox tunnels (Cloudflare quick tunnels, localhost.run) hand out a random
hostname that is recycled every few minutes or hours. They cannot give a
permanent address. Deploying the app fixes that for good.

Everything needed is already in this folder:

    Procfile          start command (Railway / Fly / Heroku style)
    render.yaml       Render blueprint
    requirements.txt  dependencies
    runtime.txt       Python version

---

## Option A - Render (simplest, free)

1. Make a free account at https://render.com
2. Push this folder to a GitHub repo
   (`.aikey` is gitignored, so your key will not be uploaded)
3. In Render: **New -> Blueprint**, pick your repo.
   It reads `render.yaml` and sets everything up.
4. When it asks for `AI_API_KEY`, paste your Gemini key and mark it secret.
5. Deploy. You get a fixed URL like `https://ewaste-appraiser.onrender.com`

## Option B - Railway (free tier)

1. Account at https://railway.app
2. **New Project -> Deploy from GitHub**, pick the repo
3. Railway reads the `Procfile` automatically
4. Add these variables:
   - `AI_PROVIDER` = `gemini`
   - `AI_API_KEY`  = your Gemini key
5. Generate a domain in Settings -> Networking

## Option C - Fly.io

1. `curl -L https://fly.io/install.sh | sh`
2. `fly launch`  (say no to creating a Dockerfile, it uses the Procfile)
3. `fly secrets set AI_PROVIDER=gemini AI_API_KEY=your-key`
4. `fly deploy`

---

## Notes

- **Free tiers sleep after ~15 min idle.** The first load after sleeping takes
  ~30 s to wake up. Everything after that is instant. Paid plans don't sleep.
- **Scan history resets on redeploy** on free tiers because the disk is
  temporary. The valuation logic is unaffected.
- **Without `AI_API_KEY` the app still works** - it falls back to the offline
  colour/texture estimate and shows an "AI unavailable" notice on the scan.
- Get or rotate a Gemini key at https://aistudio.google.com/apikey

## Security

Your current Gemini key was pasted into chat several times, so treat it as
public. **Mint a new one** at the link above before deploying anything you care
about, and only ever put it in the host's environment-variable settings.
