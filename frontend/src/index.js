import React from "react";
import ReactDOM from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import "@/index.css";
import App from "@/App";

// Benign ResizeObserver notifications (fired by React Flow's NodeResizer) surface
// as an uncaught-error overlay in dev. They are safe to ignore — swallow only that
// specific message so the CRA overlay does not interrupt canvas interaction.
const RO_ERR = /ResizeObserver loop (limit exceeded|completed with undelivered notifications)/;
window.addEventListener("error", (e) => {
  if (e.message && RO_ERR.test(e.message)) {
    e.stopImmediatePropagation();
    const overlay = document.getElementById("webpack-dev-server-client-overlay");
    if (overlay) overlay.style.display = "none";
  }
});

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 60_000,
      refetchOnWindowFocus: false,
    },
  },
});

const root = ReactDOM.createRoot(document.getElementById("root"));
root.render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <App />
    </QueryClientProvider>
  </React.StrictMode>,
);
