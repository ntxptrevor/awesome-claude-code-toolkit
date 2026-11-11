import { useEffect, useState } from "react";
import { apiJson, currentUser } from "../lib/auth";

/** Persistent live-source indicators. Glows when a source is connected, pulses ("active") while it is syncing
 *  or has edits waiting to be pushed. Polls /api/connections; shows nothing until signed in. */
const GLYPH = {
  lightfield: <path d="M12 3l2.2 5.6L20 9.3l-4.4 3.9 1.4 5.8L12 15.9 7 19l1.4-5.8L4 9.3l5.8-.7z" />,
  jobtread: <path d="M4 18V9l8-5 8 5v9h-5v-5H9v5z" />,
  gcontacts: <path d="M12 12a4 4 0 100-8 4 4 0 000 8zm0 2c-4 0-7 2-7 4.5V20h14v-1.5C19 16 16 14 12 14z" />,
};

function ago(iso) {
  if (!iso) return "never";
  const s = Math.max(0, (Date.now() - new Date(iso.replace(" ", "T") + (iso.includes("Z") || iso.includes("+") ? "" : "Z")).getTime()) / 1000);
  if (s < 90) return "just now";
  if (s < 5400) return Math.round(s / 60) + " min ago";
  if (s < 129600) return Math.round(s / 3600) + " h ago";
  return Math.round(s / 86400) + " d ago";
}

export function ConnectionStrip() {
  const [rows, setRows] = useState(null);
  const user = currentUser();
  useEffect(() => {
    if (!user) { setRows(null); return; }
    let live = true;
    const load = async () => { try { const j = await apiJson("/api/connections"); if (live) setRows(j.connections || []); } catch { /* keep last state */ } };
    load();
    const t = setInterval(load, 15000);
    return () => { live = false; clearInterval(t); };
  }, [user?.email]);
  if (!rows) return null;
  const now = Date.now();
  return (
    <ul className="conns flex items-center gap-2 m-0 p-0 list-none" aria-label="Connected sources">
      {rows.map((c) => {
        const recent = c.last_synced_at && now - new Date(c.last_synced_at.replace(" ", "T") + (/[Z+]/.test(c.last_synced_at) ? "" : "Z")).getTime() < 120000;
        const active = c.connected && (recent || c.pending > 0);
        const state = !c.connected ? "off" : active ? "active" : "on";
        const text = !c.connected ? "not connected" : active ? (c.pending > 0 ? `syncing · ${c.pending} edit${c.pending === 1 ? "" : "s"} waiting` : "syncing now") : "connected";
        return (
          <li key={c.system}>
            <span className="conn" data-state={state} role="img"
              aria-label={`${c.label}: ${text}. ${c.linked.toLocaleString()} linked, last sync ${ago(c.last_synced_at)}`}
              title={`${c.label} — ${text}\n${c.linked.toLocaleString()} linked · last sync ${ago(c.last_synced_at)}`}>
              <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor" aria-hidden="true">{GLYPH[c.system]}</svg>
              <i className="dot" aria-hidden="true" />
            </span>
          </li>
        );
      })}
    </ul>
  );
}
