# Deploy Submittal Tracker to ntxpllc.com (Hostinger)

## One-Time Setup (10 minutes)

### Step 1: Get Your Hostinger FTP Credentials

1. Log in to **hPanel** at https://hpanel.hostinger.com
2. Go to **Files** > **FTP Accounts**
3. Note your existing FTP credentials, or create a new FTP account:
   - **FTP Server**: Usually `ftp.ntxpllc.com` or shown in the FTP details page
   - **FTP Username**: Usually `u123456789` or your custom username
   - **FTP Password**: The password you set
4. If unsure, check **Files** > **FTP Accounts** > your main account

### Step 2: Add FTP Secrets to GitHub

1. Go to your GitHub repo: `https://github.com/ntxptrevor/awesome-claude-code-toolkit`
2. Click **Settings** > **Secrets and variables** > **Actions**
3. Click **New repository secret** and add these three secrets:

| Secret Name    | Value                                         |
|----------------|-----------------------------------------------|
| `FTP_SERVER`   | Your FTP server (e.g., `ftp.ntxpllc.com`)     |
| `FTP_USERNAME` | Your FTP username (e.g., `u123456789`)         |
| `FTP_PASSWORD` | Your FTP password                              |

### Step 3: Create the Target Directory on Hostinger

1. In hPanel, go to **Files** > **File Manager**
2. Navigate to `public_html/`
3. Create a new folder called `submittal-tracker`

### Step 4: Trigger the Deploy

Push to the repo or manually trigger:

1. Go to your GitHub repo > **Actions** tab
2. Select **Deploy Submittal Tracker to Hostinger**
3. Click **Run workflow**

### Step 5: Access Your App

Your app will be live at:

```
https://ntxpllc.com/submittal-tracker/
```

---

## How Auto-Deploy Works

The GitHub Actions workflow (`.github/workflows/deploy-hostinger.yml`) runs automatically when:

- You push changes to the `main` branch that touch the app files
- You manually trigger it from the Actions tab

It copies `submittal_tracker.html` as `index.html` and FTPs it to `public_html/submittal-tracker/` on Hostinger.

---

## Alternative: Manual Deploy (if you prefer)

If you'd rather not use GitHub Actions:

1. Download `tools/construction-submittals/submittal_tracker.html`
2. Log in to Hostinger hPanel
3. Go to **Files** > **File Manager**
4. Navigate to `public_html/submittal-tracker/` (create the folder if needed)
5. Upload the file and rename it to `index.html`
6. Visit `https://ntxpllc.com/submittal-tracker/`

---

## Optional: Deploy to Root Domain

If you want the app at `https://ntxpllc.com/` instead of a subdirectory:

1. Change `server-dir` in the workflow from `./public_html/submittal-tracker/` to `./public_html/`
2. Or manually upload `index.html` to `public_html/` in File Manager

---

## Optional: Add a Subdomain

To host at something like `submittals.ntxpllc.com`:

1. In hPanel, go to **Domains** > **Subdomains**
2. Create subdomain `submittals`
3. Point its document root to `public_html/submittal-tracker`
4. SSL will auto-provision via Hostinger
