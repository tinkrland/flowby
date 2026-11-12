import { defineConfig } from "vite";

// the page and flowby's python server are one origin as far as the browser can tell: in development
// vite forwards /api to the bridge (`bin/flowby serve`, port 8765), so the page needs no cors and the
// server never has to list an origin. in a build the same holds if both sit behind one host.
// no react plugin: vite's own esbuild compiles jsx (tsconfig: react-jsx), as it did before this file existed
export default defineConfig({
  server: {
    proxy: {
      "/api": { target: process.env.FLOWBY_API ?? "http://127.0.0.1:8765", changeOrigin: false },
    },
  },
  preview: {
    proxy: {
      "/api": { target: process.env.FLOWBY_API ?? "http://127.0.0.1:8765", changeOrigin: false },
    },
  },
});
