import { defineConfig } from 'vite';
import { svelte } from '@sveltejs/vite-plugin-svelte';

export default defineConfig({
  plugins: [
    svelte({
      compilerOptions: { customElement: true }
    })
  ],
  build: {
    outDir: '../static',
    emptyOutDir: false,
    lib: {
      entry: './JellyfinCard.svelte',
      name: 'JellyfinCard',
      formats: ['es'],
      fileName: () => 'bundle.js'
    }
  }
});
