# The owner's ask, verbatim

## 2026-11-20, first message (the audit)

> Do a complete audit of the onboarding procedures and the onboarding user experience, and find out where a customer or a non-technical user would stumble. Find out what we can do about it and what we can improve in it.

The audit was published as a private page ("anyscribe Onboarding Audit", 41 findings: 6 stop people cold, 18 likely to quit, 17 polish) with a three-wave fix plan. Wave 1, "Let people in", listed:

- Homebrew install on a Mac
- Copyable Windows command, how to open a terminal
- ffmpeg check in the wizard and the Windows installer
- OpenAI "no credit" message
- Real key checks
- Lock the wizard during download
- "Ready!" box and Windows window closing
- "Read transcript" button, formatted view

The consent block he approved said: about ten small changes in the anyscribe repo (the two install scripts, the website page, the setup wizard and Done screen, and the error and key-check code); no new dependencies, services, accounts, keys or paid tools; install scripts and website go live when merged, app changes after a PyPI release; plain code in his repo, revertable from git.

## 2026-11-20, second message (the approval)

> I approve building wave 1. Use appropriate subagents with the appropriate model that you think would be best to execute. You be the lead of building it all. Make sure to babysit the PR when the PR is raised, and if it's mergeable, we'll merge it. All the things noted down, as you have already noted in the artifact. Tell me when the wave 1 is done and then what is left. Create a new artifact out of it.
