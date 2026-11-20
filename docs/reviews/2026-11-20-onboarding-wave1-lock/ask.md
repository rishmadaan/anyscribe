# The owner's ask, verbatim

## 2026-11-20, the wave 1 approval (PR #26)

> I approve building wave 1. Use appropriate subagents with the appropriate model that you think would be best to execute. You be the lead of building it all. Make sure to babysit the PR when the PR is raised, and if it's mergeable, we'll merge it. All the things noted down, as you have already noted in the artifact. Tell me when the wave 1 is done and then what is left. Create a new artifact out of it.

## 2026-11-20, his answers after the wave 1 review reached its cap (questions as asked, answers as chosen)

1. Question: "Onboarding wave 1 (PR #26): 7 of the 8 fixes passed review and all checks are green. The 8th, locking the setup wizard during the model download, still has 2 rare edge cases and one wrong sentence after the 3-round review cap. They live in the app, which customers only get with a PyPI release. Merge now, or one more review round first?"
   Answer: **"Merge now (Recommended)"**, whose description read: "The installer and website fixes go live today. I finish the lock in a small follow-up PR, with its own review, before any PyPI release, so the leftovers never reach a customer."
2. Question: "During a model download in the setup wizard, should closing the wizard be impossible, or allowed after a warning? (The warning would read: 'Close setup? The download carries on in the background; your choices are saved only when you click Finish.')"
   Answer: **"Allowed after a warning (Recommended)"**, whose description read: "The reviewers' pick. It can never trap anyone and removes this whole class of edge cases. The cost: someone who confirms loses the choices they made on those screens."

This PR is that follow-up. PR #26 merged as b70c2a5.
