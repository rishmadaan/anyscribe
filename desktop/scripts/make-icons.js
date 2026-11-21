// Generates the menu bar icons and the start window icon in desktop/assets/ from the
// engine's own glyphs. Run once with: npm run make-icons (output is checked in).
//   trayTemplate.png (+@2x)         today's tray glyph, a macOS template image (no dot)
//   tray-<working|alert>-<light|dark>.png (+@2x)
//                                    the glyph with an amber (working) or red (alert) dot;
//                                    coloured, so not template: black glyph for a light
//                                    menu bar, white for a dark one
//   app-icon.png                     256 px, for the start window
'use strict';

const { app, nativeImage } = require('electron');
const fs = require('node:fs');
const path = require('node:path');

const SRC = path.join(__dirname, '..', '..', 'src', 'anyscribe', 'assets');
const OUT = path.join(__dirname, '..', 'assets');
const DOTS = { working: [0xf0, 0xa0, 0x50], alert: [0xf0, 0x60, 0x60] }; // the dashboard's amber and red

// Coverage of a disc at pixel (x, y), 4x4 supersampled, for smooth edges.
function coverage(x, y, cx, cy, r) {
  let hits = 0;
  for (let i = 0; i < 4; i++)
    for (let j = 0; j < 4; j++) {
      const dx = x + (i + 0.5) / 4 - cx;
      const dy = y + (j + 0.5) / 4 - cy;
      if (dx * dx + dy * dy <= r * r) hits++;
    }
  return hits / 16;
}

function render(glyph, size, { white = false, dot = null } = {}) {
  const img = glyph.resize({ width: size, height: size, quality: 'best' });
  const px = Buffer.from(img.toBitmap()); // BGRA, premultiplied
  const s = size / 22; // the dot is drawn for a 22 pt icon
  const [cx, cy, r, gap] = [17 * s, 17 * s, 3.5 * s, 5.2 * s];
  for (let y = 0; y < size; y++)
    for (let x = 0; x < size; x++) {
      const o = (y * size + x) * 4;
      let a = px[o + 3] / 255;
      if (dot) a *= 1 - coverage(x, y, cx, cy, gap); // clear a ring around the dot
      const glyphRGB = white ? [a, a, a] : [0, 0, 0];
      let [R, G, B, A] = [...glyphRGB, a];
      if (dot) {
        const c = coverage(x, y, cx, cy, r);
        const [dr, dg, db] = DOTS[dot].map((v) => v / 255);
        [R, G, B, A] = [R * (1 - c) + dr * c, G * (1 - c) + dg * c, B * (1 - c) + db * c, A * (1 - c) + c];
      }
      px[o] = Math.round(B * 255);
      px[o + 1] = Math.round(G * 255);
      px[o + 2] = Math.round(R * 255);
      px[o + 3] = Math.round(A * 255);
    }
  return nativeImage.createFromBitmap(px, { width: size, height: size }).toPNG();
}

app.whenReady().then(() => {
  const glyph = nativeImage.createFromPath(path.join(SRC, 'tray-icon.png'));
  fs.mkdirSync(OUT, { recursive: true });
  const write = (name, buf) => fs.writeFileSync(path.join(OUT, name), buf);
  for (const [suffix, size] of [['', 22], ['@2x', 44]]) {
    write(`trayTemplate${suffix}.png`, render(glyph, size));
    for (const dot of Object.keys(DOTS))
      for (const theme of ['light', 'dark'])
        write(`tray-${dot}-${theme}${suffix}.png`, render(glyph, size, { white: theme === 'dark', dot }));
  }
  const icon = nativeImage.createFromPath(path.join(SRC, 'app-icon.png'));
  write('app-icon.png', icon.resize({ width: 256, height: 256, quality: 'best' }).toPNG());
  console.log(`icons written to ${OUT}`);
  app.quit();
});
