// Minimal Vite config for the placeholder SPA.
// base: "./" -> relative asset URLs, so the bundle resolves regardless of the
// path it is served under (StaticFiles mount, tunnel, subpath).
export default {
  base: "./",
  build: {
    outDir: "dist",
    emptyOutDir: true,
  },
};
