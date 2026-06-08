import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import "./quadrl-design.css";
import "./App.css";
import "./rl-theme.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>
);
