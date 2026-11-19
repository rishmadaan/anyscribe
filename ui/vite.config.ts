import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { appendFileSync, readFileSync } from 'node:fs'

// The generated notice lists bundled JavaScript only; append the credits for
// the local engines and model weights (Parakeet's CC BY 4.0 needs attribution).
const modelNotices = {
  name: 'model-notices',
  closeBundle() {
    appendFileSync(
      '../src/anyscribe/web/static/THIRD-PARTY-LICENSES.md',
      readFileSync('model-notices.md', 'utf8'),
    )
  },
}

export default defineConfig({
  plugins: [react(), tailwindcss(), modelNotices],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8457',
        changeOrigin: true,
      },
    },
  },
  build: {
    license: { fileName: 'THIRD-PARTY-LICENSES.md' },
    outDir: '../src/anyscribe/web/static',
    emptyOutDir: true,
  },
})
