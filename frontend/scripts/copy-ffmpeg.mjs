import { copyFileSync } from 'fs'
import { resolve, dirname } from 'path'
import { fileURLToPath } from 'url'

const __dirname = dirname(fileURLToPath(import.meta.url))
// ESM version required — Vite spawns workers as module type,
// so importScripts() fails and import() is used instead (needs ESM default export)
const src = resolve(__dirname, '../node_modules/@ffmpeg/core/dist/esm/')
const dest = resolve(__dirname, '../public/')

console.log('Copying FFmpeg core (ESM) files to public/...')
copyFileSync(src + '/ffmpeg-core.js',   dest + '/ffmpeg-core.js')
copyFileSync(src + '/ffmpeg-core.wasm', dest + '/ffmpeg-core.wasm')
console.log('Done.')
