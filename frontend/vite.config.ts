import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The built React app is served by FastAPI under the /dashboard/ path,
// so every asset URL needs that prefix. See app/main.py for the mount.
//
// Local dev (vite dev server) and the FastAPI build flow share this base
// so the produced bundle works in both modes.
export default defineConfig({
  plugins: [react()],
  base: "/dashboard/",
});
