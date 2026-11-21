"""Mutation test for the spec's four guards (run with /usr/bin/python3).

For each mutant: write it into ui/src, rebuild, run the scenarios that guard it,
and require the named checks to FAIL. Then restore the file byte for byte,
rebuild, and run the same scenarios again, requiring them to PASS.
Prints a table and writes mutants.json beside this script.
"""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
WT = HERE.parents[3]
UI = WT / "ui"

# (name, file under ui/, [(old, new), ...], scenarios, checks that must fail: matched by prefix)
MUTANTS = [
    # guard 1: nothing app-only renders without the bridge
    ("bridge/settings", "src/pages/SettingsPage.tsx", [("{desktop ? (\n        <ThisMac", "{desktop || location.pathname ? (\n        <ThisMac")],
     # ThisMac needs the bridge, so without the guard the browser's Settings page crashes: Startup is gone
     "browser", ["Startup section as today"]),
    ("bridge/drag-strip", "src/components/Layout.tsx", [("{isMac && <div className=\"app-drag", "{true && <div className=\"app-drag")],
     "browser", ["no drag strip"]),
    ("bridge/drop-listener", "src/components/Layout.tsx",
     [("    if (!desktop) return;\n    const bridge = desktop;", "    const bridge = desktop!;"),
      ("const off = bridge.onOpenFile((path) => add([path]));", "const off = desktop ? bridge.onOpenFile((path) => add([path])) : () => {};")],
     "browser", ["dragging a file shows no overlay"]),
    ("bridge/shutdown", "src/components/Layout.tsx", [("{desktop ? null : !confirmShutdown ? (", "{!confirmShutdown ? (")],
     "app_layout", ["app: no Shutdown button"]),
    ("bridge/first-launch", "src/App.tsx", [("  useEffect(() => {\n    if (!desktop) return;\n    Promise.all",
     "  useEffect(() => {\n    if (!desktop) { setAsked({ oldLauncherAsked: false, terminalAsked: false }); return; }\n    Promise.all")],
     "browser", ["Shutdown button present"]),
    # guard 2: addToPath is never called without the person's yes
    ("addToPath/settings-row", "src/components/ThisMac.tsx",
     [('<button onClick={() => setFlow(true)} disabled={!!busy} className={SMALL_BTN}>Add it for me</button>',
       '<button onClick={() => void bridge.terminal.addToPath()} disabled={!!busy} className={SMALL_BTN}>Add it for me</button>')],
     "settings", ["GUARD addToPath: the row's button only asks"]),
    ("addToPath/after-turn-on", "src/components/MacCards.tsx",
     [("const turnOn = (replace: boolean) => act(() => desktop!.terminal.turnOn({ replace }));",
       "const turnOn = (replace: boolean) => act(async () => { const s = await desktop!.terminal.turnOn({ replace }); if (s.state === \"path-missing\") await desktop!.terminal.addToPath(); return s; });")],
     "first_launch", ["GUARD addToPath: not called before the yes"]),
    # guard 3: the first-launch questions never repeat once marked
    ("repeat/launcher-flag", "src/App.tsx", [("!!asked && !asked.oldLauncherAsked && !!launcher?.installed", "!!asked && !!launcher?.installed")],
     "first_launch,first_launch_marked", ["GUARD repeat: not asked again after reload", "GUARD repeat: both marked, nothing asked"]),
    ("repeat/terminal-flag", "src/App.tsx", [("!!asked && !asked.terminalAsked && !askLauncher", "!!asked && !askLauncher")],
     "first_launch,first_launch_marked", ["GUARD repeat: neither question again after reload", "GUARD repeat: both marked, nothing asked"]),
    ("repeat/keep-marks", "src/components/MacCards.tsx",
     [("  const keep = async () => {\n    await markAsked(\"oldLauncherAsked\");\n    onDone();", "  const keep = async () => {\n    onDone();")],
     "first_launch", ["GUARD repeat: not asked again after reload"]),
    ("repeat/terminal-marks", "src/App.tsx", [("  const terminalAnswered = () => {\n    void markAsked(\"terminalAsked\");\n", "  const terminalAnswered = () => {\n")],
     "first_launch", ["GUARD repeat: neither question again after reload"]),
    ("repeat/removal-result-once", "src/desktop.ts", [("  if (r && savedAt >= n.at) {\n    if (afterReload) note(null);", "  if (r && savedAt >= n.at) {")],
     "removal_reload", ["C7: closed with Escape, not shown again after another reload"]),
    ("repeat/removal-result-newer", "src/desktop.ts", [("  if (r && savedAt >= n.at) {", "  if (r && (savedAt >= n.at || savedAt < n.at)) {")],
     "first_launch", ["AMEND2: an older lastRemoval is never shown"]),
    # round 1 guards
    ("r1/outage-note", "src/components/EngineBanner.tsx", [("        session.set(OUTAGE, { job: watching.current, at: Date.now() });\n", "")],
     "banner", ["C1: after the reload, running again names the watched job"]),
    ("r1/asked-restart-no-outage", "src/components/EngineBanner.tsx",
     [('} else if ((wasRunning || s.state === "restarting") && !asked && !session.get(OUTAGE)) {', '} else if ((wasRunning || s.state === "restarting") && !session.get(OUTAGE)) {')],
     "banner", ["F2: no Running again after Settings' restart"]),
    ("r1/queue-before-ack", "src/components/Layout.tsx", [("      session.set(QUEUE, q);\n      setIncoming(q);\n      navigate", "      setIncoming(q);\n      navigate")],
     "open_file", ["C3: B survives the reload and is submitted by its path"]),
    ("r1/removal-note-consumed", "src/components/MacCards.tsx", [("  const done = onDone && (() => {\n    removalConsumed();\n", "  const done = onDone && (() => {\n    void removalConsumed;\n")],
     "removal_reload", ["[component] C7: the note is kept while the result card is open, gone once it is closed"]),
    ("r1/no-pieces-branch", "src/components/MacCards.tsx",
     [("  if (!result.pieces) {", "  if (!result.pieces && result.ok) {"), ("  const pieces = result.pieces;\n", "  const pieces = result.pieces!;\n")],
     "removal_reload", ["C2: a kept result with no pieces shows its reason, Try again and Close"]),
    ("r1/readiness-gate-card", "src/components/MacCards.tsx", [("  if (!runsOurs(status))\n", "  if (!runsOurs(status) && Date.now() < 0)\n")],
     "first_launch", ["C5: shell not asked: 'The anyscribe command is added'"]),
    ("r1/readiness-gate-row", "src/components/ThisMac.tsx", [('    if (terminal.state === "on" && !runsOurs(terminal)) {', '    if (terminal.state === "on" && !runsOurs(terminal) && Date.now() < 0) {')],
     "settings", ["C5: Settings row for a shell not asked"]),
    ("r1/quiet-answer-marks", "src/App.tsx", [("  const launcherKept = () => {\n    void markAsked(\"oldLauncherAsked\");\n", "  const launcherKept = () => {\n")],
     "first_launch", ["C6: a click outside the launcher question is Keep both"]),
    ("r1/mark-failure-shown", "src/desktop.ts", [("  if (r && r.ok === false) {", "  if (r && r.ok === false && Date.now() < 0) {")],
     "first_launch", ["C6: a failed save is shown with its reason"]),
    # round 2 guards (fix-plan-r2.md "Checks")
    ("r2/queue-accepted-only", "src/pages/TranscribePage.tsx", [("void handleSubmit(path).then((ok) => ok && doneIncoming(path));", "void handleSubmit(path).then(() => doneIncoming(path));")],
     "r2_facts", ["A1: refused A, B waiting: the stored queue is exactly [A, B]"]),
    ("r2/queue-error-pause", "src/pages/TranscribePage.tsx", [('phase === "running" || phase === "error" || !engineUp) return;', 'phase === "running" || !engineUp) return;')],
     "r2_facts", ["A1: refused A, B waiting: the stored queue is exactly [A, B]"]),
    ("r2/queue-running-gate", "src/pages/TranscribePage.tsx", [('phase === "running" || phase === "error" || !engineUp) return;', 'phase === "running" || phase === "error") return;')],
     "r2_facts", ["G1: engine down: nothing posted, no failure, B kept"]),
    ("r2/new-drops-head-only", "src/components/Layout.tsx", [("    if (q[0] !== path) return; // only the head: a failed typed link never takes a waiting file\n", "    void path;\n")],
     "r2_facts", ["A1: New after a typed link's failure keeps B"]),
    ("r2/note-not-mine", "src/desktop.ts", [("  return ownCalls > 0;\n", "  return ownCalls > 0 || !!readNote();\n")],
     "r2_facts", ["[component] A2/G7: with the removal's card still open"]),
    ("r2/unmatched-clear", "src/desktop.ts", [('  note(null);\n  return "refused";', '  return "refused";')],
     "r2_facts", ["A2: after the reload, the unmatched note is gone"]),
    ("r2/no-shape-clear", "src/desktop.ts", [("  const r = await own(() => desktop!.oldLauncher.remove());\n", "  const r = await own(() => desktop!.oldLauncher.remove());\n  if (!r.ok && !r.pieces) note(null);\n")],
     "r2_facts", ["A2: a thrown removal settled just before the reload"]),
    ("r2/reason-always", "src/components/MacCards.tsx", [("        {reason && <p>{reason /*", "        {!result.startAtLoginCarriedOver && reason && <p>{reason /*")],
     "r2_facts", ["A3/G3: carried over and the engine reason: both shown"]),
    ("r2/stopped-branch", "src/components/EngineBanner.tsx", [('  if (status.stoppedRestarting || status.state === "stopped") {', "  if (status.stoppedRestarting) {")],
     "r2_facts", ["G2: the stopped engine gets its red card"]),
    # round 3 (fix-plan-r3.md "Checks")
    ("r3/doomed-flag", "src/pages/TranscribePage.tsx", [('(engine?.state === "running" && !isDoomed())', '(engine?.state === "running" && (isDoomed() || true))')],
     "r3_facts", ["H1: exactly one POST, body B, sent by the reloaded page"]),
    ("r3/doomed-first-read", "src/desktop.ts", [("  desktop.engineStatus().then(seen).catch(() => undefined);", "  desktop.engineStatus().then((s) => { engineNow = s.state; }).catch(() => undefined);")],
     "r3_facts", ["H1: a page that first read 'restarting' is doomed too"]),
    ("r3/no-note-skip", "src/App.tsx",
     [('    if (!desktop || !noteAtLoad || engine?.state !== "running" || settled.current) return;', '    if (!desktop || engine?.state !== "running" || settled.current) return;'),
      ("    const at = noteAtLoad.at;\n", ""),
      ("resolveRemoval(l, engineRunningNow(), true, at)", 'resolveRemoval(l, engineRunningNow(), true, JSON.parse(localStorage.getItem("anyscribe_launcher_removing") || "{}").at)')],
     "r3_facts", ["B1: no note at load, no recovery read"]),
    ("r3/at-match", "src/desktop.ts", [("  if (!n || n.at !== at || !engineRunning) return null;", "  if (!n || (n.at !== at && false) || !engineRunning) return null;")],
     "r3_facts", ["B1: the stored note is the click's"]),
    ("r3/doomed-recovery", "src/App.tsx", [("        if (isDoomed()) return; // the reloaded page settles it; the Terminal card stays held here\n", "")],
     "r3_facts", ["Doomed recovery: no card and the note unchanged"]),
    ("r3/terminal-hold", "src/App.tsx", [("!askLauncher && !removed && removalChecked;", "!askLauncher && !removed && (removalChecked || true);")],
     "r3_facts", ["H3: terminal.status calls are [] until OK"]),
    ("r3/checklist-reason", "src/components/MacCards.tsx", [("      {reason && <p>{reason /* the bridge's own words, above the generic advice (B2) */}</p>}\n", "")],
     "r3_facts", ["B2: the checklist card shows the bridge's reason X"]),
    ("r3/stub-settles-after-running", "../docs/reviews/2026-11-20-mac-app-2c-ui/checks/stub.js",
     [('        window.__emit({ state: "running" });\n        await new Promise((res) => setTimeout(res, 20));\n        sessionStorage.setItem("__stub_remove_settled_engine", engine.state); // B3: checked by the checker\n        return r;',
       '        sessionStorage.setItem("__stub_remove_settled_engine", engine.state);\n        setTimeout(() => window.__emit({ state: "running" }), 20);\n        return r;')],
     "r3_facts", ["B3: the engine read 'running' when remove() settled"]),
    ("r3/idle-line", "src/pages/TranscribePage.tsx", [("          <URLInput onSubmit={handleSubmit} disabled={!config} />\n          {waitingForEngine}", "          <URLInput onSubmit={handleSubmit} disabled={!config} />")],
     "r3_facts", ["H2: idle view names the waiting file"]),
    ("r3/completed-line", "src/pages/TranscribePage.tsx", [("          <ResultCard result={result} onReset={reset} />\n          {waitingForEngine}", "          <ResultCard result={result} onReset={reset} />")],
     "r3_facts", ["H2: completed view names the waiting file"]),
    # guard 4: Restart engine is disabled while transcriptions run
    ("restart/disabled", "src/components/ThisMac.tsx", [("disabled={restartBlocked || busy === \"engine\"}", "disabled={busy === \"engine\"}")],
     "settings", ["GUARD restart: disabled while transcriptions run", "GUARD restart: a click while disabled calls nothing"]),
    ("restart/pending-counts", "src/desktop.ts", [('j.status === "pending" || j.status === "running"', 'j.status === "running"')],
     "settings", ["engine with jobs line"]),
]


def build():
    r = subprocess.run(["npm", "run", "build"], cwd=UI, capture_output=True, text=True)
    if r.returncode:
        sys.exit("build failed:\n" + r.stdout[-2000:] + r.stderr[-2000:])


def run(scenario):
    out = Path(tempfile.mkdtemp(prefix="mut-"))
    subprocess.run([sys.executable, str(HERE / "check_ui.py"), "--no-shots", "--only", scenario, "--out", str(out)],
                   capture_output=True, text=True)
    return {x["check"]: x for x in json.loads((out / "results.json").read_text())}


def find(res, prefix):
    hits = [x for c, x in res.items() if c.startswith(prefix)]
    return hits[0] if hits else None


rows = []
only = sys.argv[1:]  # optional mutant names
for name, rel, edits, scenario, must_fail in MUTANTS:
    if only and name not in only:
        continue
    f = UI / rel
    original = f.read_bytes()
    text = original.decode()
    for old, new in edits:
        assert text.count(old) == 1, f"{name}: target not found once in {rel}"
        text = text.replace(old, new)
    f.write_text(text)
    try:
        build()  # a mutant that does not compile stops the run: fix the mutant, never count it
        res = run(scenario)
    finally:
        f.write_bytes(original)
    killed = {c: bool(find(res, c)) and not find(res, c)["ok"] for c in must_fail}
    crashed = [x for x in res.values() if x["check"] == "scenario ran to the end"]
    build()
    res2 = run(scenario)
    restored = {c: bool(find(res2, c)) and find(res2, c)["ok"] for c in must_fail}
    all_pass = all(x["ok"] for x in res2.values())
    row = {"mutant": name, "file": rel, "scenario": scenario, "killed": killed,
           "mutant_details": {c: (find(res, c) or {}).get("detail", "(check not reached)") for c in must_fail},
           "crash": crashed[0]["detail"] if crashed else None, "restored_pass": restored, "restored_scenario_all_pass": all_pass}
    rows.append(row)
    ok = all(killed.values()) and all(restored.values()) and all_pass
    print(f"{'OK ' if ok else 'BAD'} {name}: killed={killed} restored={restored} scenario_all_pass={all_pass}")

# a run of named mutants writes its own file and leaves the full run's file alone
# a run of named mutants writes its own file (MUT_TAG names it) and leaves the full run's file alone
tag = os.environ.get("MUT_TAG", "part2")
(HERE / (f"mutants-{tag}.json" if only else "mutants.json")).write_text(json.dumps(rows, indent=1))
bad = [r for r in rows if not (all(r["killed"].values()) and all(r["restored_pass"].values()) and r["restored_scenario_all_pass"])]
print(f"\n{len(rows) - len(bad)} of {len(rows)} mutants killed and restored cleanly")
sys.exit(1 if bad else 0)
