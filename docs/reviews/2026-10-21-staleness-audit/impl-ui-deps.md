# Implementer report: audit/ui-deps (commit 0ad9f61)

Worktree: <checkout>

Changed: ui/package-lock.json (1316 lines), src/anyscribe/web/static: 2 old hashed bundles removed (index-8DOmyiD9.js, index-D_q_ft8r.css), 2 new added (index-DNxc0s5e.js, index-DDX8HJux.css); index.html 4 lines; THIRD-PARTY-LICENSES.md version numbers only. ui/package.json unchanged.

Direct deps before -> after: react-router-dom/react-router 7.14.1 -> 7.18.4; react/react-dom 19.2.5 -> 19.3.1; vite 8.0.8 -> 8.3.5; tailwindcss/@tailwindcss/vite 4.2.2 -> 4.3.3; lucide-react 1.8.0 -> 1.61.0; @vitejs/plugin-react 6.0.1 -> 6.1.2; @types/react 19.2.14 -> 19.3.0; @types/react-dom 19.2.3 -> 19.3.0; @types/node 24.12.2 -> 24.19.2; eslint/@eslint/js 9.39.4 -> 9.39.5; typescript-eslint 8.58.2 -> 8.72.0; globals 17.5.0 -> 17.13.0; eslint-plugin-react-refresh 0.5.2 -> 0.5.7; typescript 6.0.3 unchanged; eslint-plugin-react-hooks 7.1.1 unchanged.

npm audit: before 11 (1 low, 1 moderate, 9 high); after 0. react-router affected range was 6.0.0 to 7.18.1.

Lint and build pass on Node 26.9.0 and Node 22.18.0. THIRD-PARTY-LICENSES.md lists only MIT and ISC (lucide-react ISC; react-dom, react-router, react, scheduler MIT; scheduler 0.27.0 -> 0.28.0). pytest tests/test_skill_license.py tests/test_web.py: 35 passed.

Determinism: two Node 26 builds identical checksums; clean npm ci + build on Node 22.18.0 byte-identical to Node 26. Rebuild after commit leaves static tree clean. Guard mutation: planted console.log in ui/src/main.tsx made git show a new JS file; reverted and clean again. No Node version strings in built JS.

Line endings: .gitattributes forces LF for ui/** and static html/css/js; generated files plain ASCII, CR count 0.

Smoke test: did not use `anyscribe ui` (startup reinstalls the skill into ~/.claude; sandbox blocked throwaway HOME). Started create_app() with uvicorn on port 8467 with PYTHONPATH=worktree src. GET / 200, /api/health 200 ({"ok":true,"version":"0.16.5"}), /settings 200; index.html references the new assets, which load (359,821 and 30,836 bytes). Headless Chromium rendered /, /settings, /history with no page or console errors. Server stopped by pid 22156.

Unexpected: npm 11 warns fsevents install script not covered by allowScripts (harmless, same as before). Not done: full test suite, Python lint, manual click-through.
