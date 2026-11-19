import {defineConfig} from 'vite';
import {fileURLToPath} from 'node:url';
import {vanillaExtractPlugin} from '@vanilla-extract/vite-plugin';

export default defineConfig({
  base: '/native/',
  plugins: [vanillaExtractPlugin()],
  // Vite library mode intentionally keeps NODE_ENV for consumers; this bundle
  // is a browser application asset, so Atlaskit/React must receive a literal.
  define: {'process.env.NODE_ENV': JSON.stringify('production')},
  // Published BlockSuite packages expose their TypeScript source, including
  // standard decorators/auto-accessors; transform those dependencies as well.
  esbuild: {include: /\.[cm]?[jt]sx?$/, exclude: [], target: 'es2022', tsconfigRaw: {compilerOptions: {experimentalDecorators: false, useDefineForClassFields: false}}},
  server: {host: '127.0.0.1', port: 18765},
  build: {
    target: 'es2022', sourcemap: true,
    lib: {entry: fileURLToPath(new URL('./src/editor.ts', import.meta.url)), formats: ['es'], fileName: () => 'editor.js', cssFileName: 'style'},
    rollupOptions: {output: {chunkFileNames: 'assets/[name]-[hash].js', assetFileNames: asset => asset.names?.some(name => name.endsWith('.css')) ? 'style.css' : 'assets/[name]-[hash][extname]'}},
  },
});
