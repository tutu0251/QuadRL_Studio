import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@rl-trainer-model": path.resolve(__dirname, "../../packages/rl-trainer-model"),
    },
  },
  server: {
    host: "0.0.0.0",
    port: 5178,
  },
});
