"""Lead-made round 4 changes: each mutant breaks one, rebuilds, runs its scenario, restores byte for byte."""
import subprocess, sys, pathlib
W = pathlib.Path.home() / "labs/projects/anyscribe-wt/mac-2c-ui"
S = pathlib.Path(sys.argv[1])
CHECK = W / "docs/reviews/2026-11-20-mac-app-2c-ui/checks/check_ui.py"
MUTANTS = [
    ("K1-strip", "ui/src/components/MacCards.tsx",
     'reason?.replace(/^Cleanup didn\'t finish: [^.]*\\.\\s*/, "") || null', "reason",
     "r3_facts", "B2, K1:"),
    ("K3-running", "ui/src/pages/TranscribePage.tsx",
     '{engineUp ? `${waiting.length === 1 ? "It starts" : "They start in turn"} when this one finishes.` : onceUp(waiting.length)}',
     '{`${waiting.length === 1 ? "It starts" : "They start in turn"} when this one finishes.`}',
     "r3_facts", "K3: under a running job"),
    ("K3-error", "ui/src/pages/TranscribePage.tsx",  # the engine-down branch never taken: the engine-up words always
     '{engineUp\n                ? `${waiting.length === 1 ? "It waits"',
     '{true\n                ? `${waiting.length === 1 ? "It waits"',
     "r3_facts", "K3: under an error"),
    ("E1-head", "ui/src/pages/TranscribePage.tsx",  # the failed-head branch never taken (still compiles)
     'incoming[0] === lastUrl ? afterHead(waiting.length)',
     'false ? afterHead(waiting.length)',
     "r3_facts", "E1:"),
    ("K4-stop", "ui/src/components/MacCards.tsx",
     '${/[.!?]$/.test(r.reason) ? "" : "."} It is running', ' It is running',
     "r2_facts", "A3, K4:"),
]
def sh(cmd, **kw):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True, **kw)
def build():
    r = sh("npm run build", cwd=W / "ui")
    assert r.returncode == 0, r.stderr[-2000:]
def run(scen, tag):
    r = sh(f"/usr/bin/python3 {CHECK} --no-shots --only {scen} --out {S}/mut-{tag}")
    return r.stdout + r.stderr
results = []
for name, rel, old, new, scen, label in MUTANTS:
    f = W / rel
    orig = f.read_bytes()
    text = orig.decode()
    assert text.count(old) == 1, (name, text.count(old))
    f.write_text(text.replace(old, new))
    try:
        build()
        out = run(scen, name)
    finally:
        f.write_bytes(orig)
    lines = [l for l in out.splitlines() if label in l]
    killed = any(l.startswith("FAIL") or " FAIL" in l[:12] for l in lines)
    results.append((name, killed, lines[:2]))
build()
restored = run("r2_facts,r3_facts", "restored")
print("\n".join(f"{'KILLED' if k else 'SURVIVED'} {n}: {l}" for n, k, l in results))
print("restored:", [l for l in restored.splitlines() if "passed" in l][-1:])
