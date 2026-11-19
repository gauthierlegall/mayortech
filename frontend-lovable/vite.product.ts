import {defineConfig} from 'vite';
import react from '@vitejs/plugin-react';
import tailwind from '@tailwindcss/vite';
import {fileURLToPath,URL} from 'node:url';
const backend='http://127.0.0.1:8766';
export default defineConfig({
 base:'/web/product/',publicDir:false,plugins:[react(),tailwind()],
 resolve:{alias:{'@':fileURLToPath(new URL('./src',import.meta.url))}},
 server:{fs:{allow:['..']},proxy:{
  '/api':{target:backend,changeOrigin:true,configure(proxy){proxy.on('proxyReq',(request,incoming)=>{if(['http://127.0.0.1:18766','http://127.0.0.1:18767'].includes(incoming.headers.origin||''))request.setHeader('Origin',backend);});}},
  '/native':backend,'/health':backend,
  '/web/product/native':{target:backend,rewrite:path=>path.replace('/web/product','')},
 }},
 build:{outDir:'dist',emptyOutDir:true,sourcemap:false,rollupOptions:{input:{app:fileURLToPath(new URL('./index.html',import.meta.url)),connexion:fileURLToPath(new URL('./connexion.html',import.meta.url)),inscription:fileURLToPath(new URL('./inscription.html',import.meta.url)),recovery:fileURLToPath(new URL('./mot-de-passe-oublie.html',import.meta.url)),legal:fileURLToPath(new URL('./mentions-legales.html',import.meta.url)),privacy:fileURLToPath(new URL('./confidentialite.html',import.meta.url))}}},
});
