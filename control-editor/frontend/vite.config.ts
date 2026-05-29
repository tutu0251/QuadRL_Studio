import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@control-model": path.resolve(__dirname, "../../packages/control-model"),
    },
  },
  server: {
    host: "0.0.0.0",
    port: 5175,
  },
});
