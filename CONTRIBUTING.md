# Contributing to anyscribe

Contributions are licensed under **AGPL-3.0-or-later**, unless explicitly agreed
otherwise. Submit only material you have the right to contribute, disclose
third-party material, and preserve its copyright and license notices. See
[NOTICE](NOTICE), [LICENSE](LICENSE), and [CLAUDE.md](CLAUDE.md).

## Build from source

Use Python 3.10+ and Node.js 22.12+ (the release workflow uses Node 22).
Create and activate a virtual environment, then run from the repository root:

```sh
python -m pip install -e ".[dev,mcp]" build
```

From `ui/`, run:

```sh
npm ci
npm run build
```

Back at the root, run:

```sh
python -m build
```

The frontend build writes the compiled UI and bundled JavaScript license notices
to `src/anyscribe/web/static/`. Preserve Tailwind's license in `NOTICE` when
updating it. The Python build produces a wheel and a source archive in `dist/`;
the source archive includes `ui/` and the build configuration. Do not distribute
minified JavaScript as a substitute for editable source.

## Distributing or hosting a modified version

Follow the full AGPL terms in [LICENSE](LICENSE). In particular, preserve notices,
identify your modifications and their dates, and provide the corresponding
source when required. Publish source archives alongside binary downloads using
an AGPL-compliant distribution method. Keep the source matched to each artifact.

For a modified version that users interact with remotely over a network, offer
those users its corresponding source prominently and at no charge. Update the
Web UI's **Source** link to your exact deployed source, including your changes;
linking only to upstream anyscribe is insufficient. A future hosted MCP surface
must also present an accessible source offer. Keep credentials and user data out
of source archives.

For upstream releases, publish both the wheel and matching source archive to
PyPI, keep the matching Git tag, and link the release notes to that version's
source. Earlier MIT releases keep their original permissions. Do not overwrite
their tags or artifacts when publishing the first AGPL release.
