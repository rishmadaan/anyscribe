# The owner's ask (verbatim)

## First message, 2026-11-19

> Can you pull the recent version of this repo and comprehensively test through all the local transcription options that we have? Maybe even search the internet and find out if there are new local transcription models available which might be better at the job.
>
> I'd like to run a full end-to-end test and take the full send skill's essence by Theo to do this in a new branch (where we basically make any scribe perfectly ready for local transcription, so that nobody has to worry about API keys or anything like that). If they choose to actually settle with a little bit hit on the accuracy, I would say we can put a very similar way how spokenly their transcription model choices and default pickers, the UX of it I mena

## Consent answers, 2026-11-19 (after seeing the benchmark, the proposal and the mockup)

Build scope:

> Full plan, plus we should also add UX features like actually suggesting to the user and walking them through the setup of why they would need to set up a particular model or another model.

Finish line:

> Merge and then ask, but use only Claude models for the most part. You can get OpenAI models to be used as well, however, not in loops, because the OpenAI reset just happened today. I don't want to burn through all of that in one day.

"Merge and then ask" means: merge the reviewed PR into main, then ask before publishing a release to PyPI.
