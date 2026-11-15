import { resolve } from '$app/paths';

/** The site's base path: '' locally, '/<repo>' on GitHub Pages. SvelteKit 3 no longer exports `base`. */
export const base = resolve('/').replace(/\/$/, '');
