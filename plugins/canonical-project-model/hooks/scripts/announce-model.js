#!/usr/bin/env node
/**
 * announce-model.js  (PostToolUse: Bash, plugin-scoped)
 *
 * Fires after a Bash command. When that command was a real (non-dry-run) run of
 * assemble_model.py, it injects a short context note so the calling model picks up
 * the freshly written model-handoff.json / canonical-model.json and routes onward —
 * making the structure -> downstream handoff automatic without the user typing the
 * next command.
 *
 * It never blocks; it only adds context on a match, and stays silent otherwise.
 */

const stdinData = [];
process.stdin.on("data", (c) => stdinData.push(c));
process.stdin.on("end", () => {
  const raw = Buffer.concat(stdinData).toString().trim();
  let command = "";
  try {
    const p = JSON.parse(raw);
    command =
      (p.tool_input && (p.tool_input.command || p.tool_input.cmd)) ||
      p.command ||
      "";
  } catch (e) {
    command = raw;
  }

  // Require an actual python invocation of the assembler — not a mere mention of
  // the file (e.g. `cat assemble_model.py`), which must NOT trigger a false handoff.
  const ran = /\bpython[0-9.]*\s+\S*assemble_model\.py\b/.test(command);
  const dryRun = /--dry-run\b/.test(command);
  if (!ran || dryRun) return; // not an assemble run, or just a plan — stay silent

  console.log(
    JSON.stringify({
      hookSpecificOutput: {
        hookEventName: "PostToolUse",
        additionalContext:
          "[canonical-project-model] A Canonical Project Record was just assembled. " +
          "Read the model-handoff.json it wrote under projects/<slug>/model/ (schema: " +
          "plugins/canonical-project-model/schemas/model-handoff.schema.json). The " +
          "source of truth is canonical-model.json; the human-readable view is " +
          "project-record.md. If status is 'ready' or 'partial', proceed with the " +
          "handoff's next_step (default construction-doc-pipeline:review), having " +
          "downstream skills PULL their inputs from the canonical sections instead of " +
          "re-parsing documents. Surface anything in needs_human_review and any " +
          "'invalid' sections first.",
      },
    })
  );
});

if (process.stdin.isTTY) process.exit(0);
