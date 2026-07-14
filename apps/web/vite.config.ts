import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Relative base ("./") so the production bundle also loads correctly when the
// packaged Electron shell opens dist/index.html via file:// (absolute "/assets"
// paths would otherwise resolve against the filesystem root and 404).
export default defineConfig({
  plugins: [react()],
  base: "./",
  server: {
    host: "127.0.0.1",
    port: 5173,
    strictPort: true,
  },
  build: {
    outDir: "dist",
    emptyOutDir: true,
  },
});
