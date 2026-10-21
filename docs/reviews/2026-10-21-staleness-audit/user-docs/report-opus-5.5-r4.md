FIT REVIEW: PR #17 (audit/user-docs), round 4 (cap), head f83851e. Reviewer: Opus 5.5, effort high (Claude lane; first attempt stopped on the Claude session limit, resumed after the reset).

VERDICT: GOOD TO GO. All seven round-3 items really fixed (each traced to code: config_cmd.py:40-58/:283-305 and resolve.py:105-112 for planned vs used model; languages.py:357-364, routes/config.py:175-176, LanguageInput.tsx for the Groq picker; vault/index.py:136-153 and rm.py:53-56 for rm paths; --json present on transcribe, batch, config/show/list-keys, logs, all five model subcommands; routes/config.py:292-300 for the key test; main.py:56-63/:193-194 for the skill install). Landing/docs equal to a fresh render on 7/7 pages (in-memory, markdown 3.10.3, check_links clean); check-docs exit 0; git diff --check clean; CI green on f83851e (two read-only gh calls, disclosed). Counts recounted: 100/89/92/23.

NEW: none at blocker or should-fix.
D1. nit. CONFIRMED. providers.md:476: after the Groq exception, the next paragraph still opens "OpenRouter is the exception:"; suggest "OpenRouter works differently:". (Lead: declined as a follow-up to keep the merged text fully reviewed.)
D2. nit (optional). "run plan" / "substitution notes" phrasing slightly opaque for newcomers; optional plainer wording for configuration.md:64-65. (Lead: declined, follow-up.)

PENDING OWNER CHECKS: whether OpenRouter's /models rejects a bad key with 401 (if so the docs under-claim, the safe direction); landing tone if he wants it louder.

INSPECTED: brief, impl r4, ledger-r3, own r3 report, git show f83851e; cli/config_cmd.py, rm.py, main.py, local_cmd.py, --json flags across cli/*.py; core/resolve.py; providers/__init__.py, languages.py, groq.py, openai.py; vault/index.py; config/paths.py; web/routes/config.py; ui LanguageInput.tsx, SettingsPage.tsx, TranscribePage.tsx; scripts; ci.yml; README, docs/user, landing and rendered HTML; PR #18 branch for the skill rm examples.
