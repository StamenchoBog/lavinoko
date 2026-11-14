import adapter from '@sveltejs/adapter-static';
import { vitePreprocess } from '@sveltejs/vite-plugin-svelte';

/** @type {import('@sveltejs/kit').Config} */
export default {
  preprocess: vitePreprocess(),
  kit: {
    // Static files only: free hosting, nothing to run on a server.
    adapter: adapter({ pages: 'build', assets: 'build', fallback: undefined, strict: true }),
    // GitHub Pages serves the site under /<repo>; set BASE_PATH there, empty locally.
    paths: { base: process.env.BASE_PATH ?? '' }
  }
};
