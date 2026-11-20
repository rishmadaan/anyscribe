**NOT YET.** The implementation covers the approved wave 1 scope, but the download lock can be bypassed, recovery can claim the wrong model is ready, and key-check results can advance an edited key without checking it.

Reviewed `feat/onboarding-wave1` at `8d632214835e865c44484515452f0bbaec7ccdfc`, against `7ab1539`. “CONFIRMED” below means confirmed by source trace, not by running the application.

1. **C1 | blocker | CONFIRMED: the cloud path can leave and close the wizard during a download.**

   Where: [OnboardingWizard.tsx:730](~/labs/projects/anyscribe-wt/wave1/ui/src/components/OnboardingWizard.tsx:730), also lines 631–634 and 862–867.

   Choose a cloud provider, enable local transcription as a backup, and start downloading. The checkbox remains enabled. Unchecking it exposes **Skip, next**, which has no `settingUp` guard. Clicking it unmounts the local step; its cleanup calls `onRunning(false)`, unlocking Escape, outside click, and **Skip for now** while the backend download continues. Closing then loses the unsaved wizard choices.

   Fix: disable the checkbox during setup and guard every route out of the step against an active setup. Verify this exact cloud-backup path, including closing from Workspace after attempting to skip.

2. **C2 | blocker | CONFIRMED: 409 recovery can label an undownloaded model “ready.”**

   Where: [OnboardingWizard.tsx:687](~/labs/projects/anyscribe-wt/wave1/ui/src/components/OnboardingWizard.tsx:687), also lines 656–660 and 975–978. Backend definition: [local_setup.py:328](~/labs/projects/anyscribe-wt/wave1/src/anyscribe/core/local_setup.py:328).

   Select Turbo in the wizard, then start Small from another tab before pressing Download. The wizard receives 409 and watches Small, but retains Turbo in `form.localModel`. When Small finishes, `s.set_up` becomes true because it means **any model is runnable**. The wizard advances and its summary says **Turbo · ready**, although Turbo was never downloaded. Finish can then start that missing download synchronously through the save endpoint.

   Fix: explicitly reconcile the selected model with `setup_last_model` when adopting another setup. Before advancing or saying “ready,” verify the particular model being summarized is runnable.

3. **C3 | should-fix | CONFIRMED: an old key’s successful check can advance a newly edited key.**

   Where: [OnboardingWizard.tsx:466](~/labs/projects/anyscribe-wt/wave1/ui/src/components/OnboardingWizard.tsx:466), also lines 444–463 and 488–491.

   Press Next with key A, then edit the input to key B while the request waits. The input remains editable. When A is accepted, the pending `handleNext` calls `onNext()` without checking whether A is still the current value. B proceeds unchecked. The `check.key === value` comparison protects the displayed result, but does not protect this automatic navigation. Back is also active while the request waits, allowing a late response to navigate after leaving the step.

   Fix: discard obsolete responses before updating state or navigating. Bind requests to the provider, key, and current step, or disable editing and navigation while checking.

4. **C4 | should-fix | CONFIRMED: Windows can still print “ready” after losing ffmpeg from PATH.**

   Where: [install.ps1:364](~/labs/projects/anyscribe-wt/wave1/install.ps1:364). Trace also passes through lines 119–129, 289, and 46–50.

   Start PowerShell with ffmpeg and ffprobe available through a session-only PATH entry. `Test-Ffmpeg` records `$script:FfmpegOk = $true`. Later, `Install-Anyscribe` unconditionally calls `Refresh-Path`, replacing PATH with the registry values and dropping that entry. The final banner uses the cached boolean without checking again. Desktop setup can succeed without checking ffmpeg, so the banner can say **anyscribe is ready!** while transcription cannot find it.

   Fix: recheck both binaries after the final PATH change and before launching desktop mode and reporting readiness. The existing isolated `Test-Ffmpeg`/`Write-Result` proof does not exercise this intervening PATH replacement.

5. **C5 | nit | CONFIRMED: source links containing parentheses are truncated.**

   Where: [TranscriptBody.tsx:16](~/labs/projects/anyscribe-wt/wave1/ui/src/components/TranscriptBody.tsx:16).

   `writer.py` preserves the original URL. For `[source](https://example.com/audio_(final).mp3)`, the renderer stops the URL at the first `)`, creating a broken link and leaving `.mp3)` as visible text. This limitation is acknowledged in the builder’s proof; it is not a security bypass.

   Fix: parse balanced parentheses in link destinations. The separate Source button retains the full URL, which limits the impact.

The scope and instrument are appropriate for the owner’s approved request. No architectural replacement or new dependency is needed. The lead’s **“Not checked yet”** correction is accurate: Sarvam’s key is saved only at Finish.

By inspection, ordinary 429s remain retryable, no-credit errors bypass retry, the revised key checks use fixed provider HTTPS endpoints, and the renderer constructs React elements with HTTP(S)-only links. I found no changed-code path that persists the typed key before Finish. Tailnet code, Host-check middleware, version files, release script, and `.github/` have no changes in this diff. The settled declined finding was not reopened.

**Pending owner checks:** none that only the owner can confirm. Native Mac and Windows verification remains engineering work, not an assignment to him.

**Verification limits and inspection:** I read the complete packet, declined list, lead-made commit, changed source and documentation diff, relevant callers, `vault/writer.py`, mutation outputs, installer log evidence, server logs, and all supplied screenshots. Generated bundles and generated documentation were reviewed through their sources, as instructed.

I ran these permitted checks successfully:

```text
bash -n ~/labs/projects/anyscribe-wt/wave1/install.sh
git -C ~/labs/projects/anyscribe-wt/wave1 diff --check 7ab1539..8d63221
```

The brief prohibited runtime checks, so I did not independently run:

```text
cd ~/labs/projects/anyscribe-wt/wave1 && pytest -q
cd ~/labs/projects/anyscribe-wt/wave1 && ruff check src tests scripts
cd ~/labs/projects/anyscribe-wt/wave1/ui && npm run lint && npm run build
cd ~/labs/projects/anyscribe-wt/wave1 && python scripts/build-docs.py && python scripts/check-docs.py
gh pr checks 26 --repo rishmadaan/anyscribe
```

Exact-SHA CI, native macOS installation, Windows PowerShell 5.1, registry PATH refresh, and a real desktop installation remain unverified here. The saved `app-ffmpeg-after-setup-1440.png` shows an empty modal panel, so it does not visually substantiate that particular recovery state. The Sarvam screenshots predate the lead’s wording correction.