# Implementer report, round 3 fix: audit/skill-cli-text commit 5298f43 (parent 44fec4c)

Six files, 17+, 15-. All six items FIXED, none wrong.
1. Segment timestamps: elevenlabs.py:88-103 and deepgram.py:177-190 group word timings into ~30-word segments. Changed cli/onboard.py:181, SKILL.md:203 row, both cells of providers.md:89 Timestamps row, providers.md:143 and :149, troubleshooting.md:166 first sentence.
2. Local default vs saved diarize: resolve.py:53-62 confirms. Recipe text replaces SKILL.md:134 and commands.md:554; providers.md ~219 now "Does not change provider, quality or diarize." followed by the recipe.
3. OpenAI recovery message: retry lines no longer contain a filename; key setup line kept; f-string prefixes dropped on plain strings. No test asserts the message.
4. Install entry points: providers.md:199 now "Installation is **opt-in** through anyscribe local setup, onboarding with the local provider, or the Web UI's local setup flow."
5. Groq long-file note appended; groq.py unchanged.
6. SKILL.md:348 "(and, on older installs, a leftover Instagram password)".

Checks: pytest 485 passed, 1 skipped (incl. test_skill_license; SKILL.md lines 1-14 untouched); ruff check passed; ruff format --check openai.py, onboard.py already formatted; check-docs exit 0. Grep for word-level/word timestamps/Word-level in skill, cli, web/routes: nothing; wider search found only the elevenlabs.py:84 comment "Build segments from word-level data" (raw response, accurate, left).

Rendered OpenAI error with a dummy 30 MB file named MY_SECRET_BASENAME.mp3, diarize=True: the two retry lines are "then retry your original URL or file path with -p deepgram --diarize (replacing any existing provider flag)" and "Or transcribe without speaker labels (long files chunk automatically): retry your original input with -p openai and without --diarize; if diarize is on in config, first run: anyscribe config set diarize false". The filename does not appear; the previous commit's message did include it.

Not done: React blurb under ui/; docs/user. CI not yet run on 5298f43.
