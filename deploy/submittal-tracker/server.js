const express = require("express");
const path = require("path");

const app = express();
const PORT = process.env.PORT || 3000;

// Security headers
app.use((req, res, next) => {
  res.set({
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "SAMEORIGIN",
    "X-XSS-Protection": "1; mode=block",
    "Referrer-Policy": "strict-origin-when-cross-origin",
  });
  next();
});

// Health check
app.get("/health", (req, res) => {
  res.json({ status: "ok", app: "submittal-tracker" });
});

// Serve static files from this directory
app.use(express.static(path.join(__dirname), { maxAge: "1h" }));

// SPA fallback — all routes serve index.html
app.get("*", (req, res) => {
  res.sendFile(path.join(__dirname, "index.html"));
});

app.listen(PORT, () => {
  console.log(`Submittal Tracker running on port ${PORT}`);
});
