import { defineConfig } from 'vite';
import { svelte } from '@sveltejs/vite-plugin-svelte';

export default defineConfig({
    plugins: [
        svelte({
            compilerOptions: {
                customElement: true, // Assuming you are compiling to Web Components
            }
        })
    ],
    build: {
        outDir: '../static',
        emptyOutDir: true,
        lib: {
            entry: 'AcoustIDCard.svelte', // Point this to your AcoustID svelte file
            name: 'AcoustIDPlugin',
            fileName: () => 'bundle.js',
            formats: ['iife']
        }
    }
});