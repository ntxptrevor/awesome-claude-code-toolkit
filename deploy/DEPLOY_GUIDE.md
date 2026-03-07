# Deploy Submittal Tracker to submittals.ntxpllc.com

## Hostinger Node.js Git Auto-Deploy

### Prerequisites
- Subdomain `submittals.ntxpllc.com` created in Hostinger hPanel
- GitHub repo: `ntxptrevor/awesome-claude-code-toolkit`

---

### Step 1: Set Up Node.js in hPanel

1. Log in to **hPanel** → https://hpanel.hostinger.com
2. Go to **Websites** → select `ntxpllc.com`
3. Go to **Advanced** → **Node.js**
4. Click **Create new application** and fill in:

| Field | Value |
|-------|-------|
| **Node.js version** | `18.x` (or latest LTS available) |
| **Application root** | `deploy/submittal-tracker` |
| **Application startup file** | `server.js` |
| **Application URL** | Select `submittals.ntxpllc.com` from dropdown |

5. Click **Create**

---

### Step 2: Connect Git Repository

1. Still in hPanel, go to **Advanced** → **Git**
2. Click **Create new repository** and fill in:

| Field | Value |
|-------|-------|
| **Repository URL** | `https://github.com/ntxptrevor/awesome-claude-code-toolkit.git` |
| **Branch** | `main` |
| **Repository path** | `/home/u[YOUR_ID]/domains/ntxpllc.com/public_html/submittals.ntxpllc.com` (or wherever Hostinger points the subdomain — check in **Subdomains** settings) |
| **Auto deploy** | **Enable** |

3. Click **Create**

> **Note**: If Hostinger asks for authentication, you may need to generate a GitHub Personal Access Token:
> - Go to GitHub → **Settings** → **Developer settings** → **Personal access tokens** → **Tokens (classic)**
> - Generate a token with `repo` scope
> - Use your GitHub username and the token as the password

---

### Step 3: Set Auto-Deploy Webhook (optional but recommended)

To make Hostinger pull automatically on every push:

1. In hPanel **Git** section, copy the **Webhook URL** shown for your repo
2. Go to GitHub repo → **Settings** → **Webhooks** → **Add webhook**
3. Paste the webhook URL
4. Content type: `application/json`
5. Select **Just the push event**
6. Click **Add webhook**

---

### Step 4: Verify

1. In hPanel → **Node.js**, click **Restart** on your application
2. Visit: **https://submittals.ntxpllc.com**
3. You should see the Submittal Tracker app

---

## Folder Structure on Hostinger

After Git pulls the repo, Hostinger runs `npm install` in the application root and starts `server.js`:

```
your-repo/
├── deploy/
│   └── submittal-tracker/     ← Application root
│       ├── server.js          ← Entry point (Node.js HTTP server)
│       ├── index.html         ← The full app (single file)
│       ├── package.json       ← Node config
│       └── .htaccess          ← HTTPS redirect & headers
```

The `server.js` reads `index.html` and serves it on the port Hostinger assigns via `process.env.PORT`.

---

## Updating the App

After the Git auto-deploy is connected:

1. Make changes to `tools/construction-submittals/submittal_tracker.html`
2. Copy it to `deploy/submittal-tracker/index.html`
3. Commit and push to `main`
4. Hostinger auto-pulls and restarts the Node.js app

Or just push — the GitHub Actions workflow auto-syncs the HTML to the deploy folder.

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| 502 Bad Gateway | In hPanel → Node.js, click **Restart**. Check that startup file is `server.js` |
| App not updating | Check hPanel → Git → click **Pull** manually. Verify branch is `main` |
| Git auth fails | Add a GitHub Personal Access Token (see Step 2 note above) |
| SSL not working | hPanel → SSL → ensure auto-SSL is enabled for the subdomain |
| Wrong directory | Check hPanel → Subdomains → verify document root path matches Git repo path |
| Port errors | `server.js` uses `process.env.PORT` which Hostinger sets automatically — do not hardcode |

---

## Health Check

Test the server is running:

```
curl https://submittals.ntxpllc.com/health
```

Should return: `{"status":"ok","app":"submittal-tracker"}`
