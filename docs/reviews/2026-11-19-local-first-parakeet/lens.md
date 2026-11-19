# Lens: code PR + screen

## Code PR
- His goal as invariants: (1) a new user with no API key gets a working local transcript; (2) Parakeet never writes gibberish silently for a language it doesn't cover; (3) existing users' settings never change without their choice; (4) nothing is terminal-only or web-only; (5) no owner data in the public repo.
- Try to break each guard with concrete inputs: language=auto with Hindi audio; language=hi explicit; language=en explicit with Hindi audio; language=ur / pa / ta; tiny not cached; only distil cached; only a half-downloaded turbo cached; parakeet-v2 with French audio; a 2-second file; a file with 40 s of silence then speech; batch of mixed English and Hindi files (model cache reuse across switches).
- Install paths: pipx, venv with pip, uv-tool venv without pip, system python with PEP 668; an existing v0.18.3 install with faster-whisper + av 19 already present upgrading to this.
- Platform: macOS Apple silicon (onnxruntime picks CoreML by default), Windows (memory detection, paths), Linux.
- Tests that cannot fail; tests whose fixtures touch the real HOME or HF cache.
- Docs and spec that claim more than the code does; spec that was wrong and got built anyway.
- The same pattern elsewhere: any other place a model id list, a size, or "recommended" is hard-coded.

## Screen
- Can every number on a card be known? (ratings and minutes are from one reference desktop; does the screen say so?)
- States: nothing downloaded, downloading, half-downloaded, download failed, only the language helper missing, delete the only model, default not downloaded yet ("pending default").
- Walk his jobs: brand-new user with no keys sets up and transcribes an English YouTube link; a Hindi voice note; an existing turbo user opens Settings after upgrading; choosing "A mix".
- Anything hover-only; status shown by colour alone; 390 px layout.
- A key-free user must never see an API-key warning.
