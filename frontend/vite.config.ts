import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";

const PROXY_PATHS = [
  "/auth",
  "/sessions",
  "/swarm/presets",
  "/swarm/runs",
  "/qveris",
  "/settings/llm",
  "/settings/data-sources",
  "/channels",
  "/mandate",
  "/live",
  "/upload",
  "/shadow-reports",
];

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const apiTarget = env.VITE_API_URL || "http://127.0.0.1:8899";
  const apiProxy = { target: apiTarget, changeOrigin: true };
  const apiProxyWithHtmlFallback = {
    ...apiProxy,
    bypass(req: { headers: { accept?: string } }) {
      if (req.headers.accept?.includes("text/html")) {
        return "/index.html";
      }
    },
  };

  return {
    plugins: [react()],
    resolve: {
      alias: { "@": path.resolve(__dirname, "./src") },
    },
    server: {
      port: 5899,
      proxy: {
        ...Object.fromEntries(PROXY_PATHS.map((p) => [p, apiProxy])),
        // SPA RunDetail page — only the two-segment ``/runs/{id}``
        // form should fall back to ``index.html`` on browser navigation.
        // ``/runs/{id}/code`` and ``/runs/{id}/pine`` are API-only and
        // must keep proxying to the backend even when Accept is text/html.
        "^/runs/[^/]+/?$": apiProxyWithHtmlFallback,
        "/runs": apiProxy,
        "/correlation": apiProxyWithHtmlFallback,
          "^/alpha(?:/|$)": apiProxy,
          "^/auto-selection(?:/|$)": apiProxy,
        // ``/mt5`` and ``/auto-trade`` are BOTH API prefixes and SPA routes
        // (``/auto-trade``, ``/auto-trade/strategy-selection``,
        // ``/mt5-integration``). Proxying them unconditionally made a browser
        // refresh return the backend's stale ``dist/index.html`` -> white page.
        // The html fallback keeps XHR/fetch on the backend while browser
        // navigation falls through to the dev-server SPA. The ``(?:/|$)``
        // guard stops ``/mt5`` from swallowing ``/mt5-integration``.
        "^/mt5(?:/|$)": apiProxyWithHtmlFallback,
        "^/auto-trade(?:/|$)": apiProxyWithHtmlFallback,
        // Same dual-purpose treatment: ``/diagnostics`` is BOTH an API
        // prefix (``/diagnostics/dashboard``, ``/diagnostics/trades``,
        // ``/diagnostics/patterns``, ...) and an SPA route namespace
        // (``/diagnostics``, ``/diagnostics/trades``, ``/diagnostics/patterns``
        // ...). Without the html fallback a browser refresh served the
        // backend's JSON 404 -> white page. The ``(?:/|$)`` guard keeps the
        // prefix from swallowing unrelated paths.
        "^/diagnostics(?:/|$)": apiProxyWithHtmlFallback,
      },
    },
    build: {
      rollupOptions: {
        output: {
          manualChunks: {
            "vendor-react": ["react", "react-dom", "react-router"],
            "vendor-charts": ["echarts"],
          },
        },
      },
    },
  };
});
