import adapter from '@sveltejs/adapter-static';
import { sveltekit } from '@sveltejs/kit/vite';
import { vitePreprocess } from '@sveltejs/vite-plugin-svelte';
import { defineConfig } from 'vite';

export default defineConfig({
  plugins: [
    // SvelteKit 3 takes its config here; svelte.config.js is no longer read.
    sveltekit({
      preprocess: vitePreprocess(),
      // Static files only: free hosting, nothing to run on a server.
      adapter: adapter({ pages: 'build', assets: 'build', strict: true }),
      // GitHub Pages serves the site under /<repo>; set BASE_PATH there, empty locally.
      paths: { base: (process.env.BASE_PATH ?? '') as '' | `/${string}` }
    })
  ]
});
