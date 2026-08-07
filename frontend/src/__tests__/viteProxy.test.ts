import fs from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";

describe("Vite API proxy config", () => {
  const configPath = path.resolve(__dirname, "../../vite.config.ts");
  const config = fs.readFileSync(configPath, "utf8");

  it("proxies channel runtime endpoints", () => {
    expect(config).toContain('"/channels"');
  });

  it("proxies settings endpoints", () => {
    expect(config).toContain('"/settings/llm"');
    expect(config).toContain('"/settings/data-sources"');
  });

  it("proxies authentication endpoints", () => {
    expect(config).toContain('"/auth"');
  });

  it("gives /diagnostics the html fallback so browser refresh serves the SPA", () => {
    // /diagnostics is BOTH an API prefix (/diagnostics/dashboard, /diagnostics/trades, ...)
    // and a SPA route namespace (/diagnostics, /diagnostics/trades, ...). Without the html
    // fallback, a hard refresh on /diagnostics gets proxied straight to the backend, which
    // has no matching HTML route, producing a blank white page instead of the SPA shell.
    expect(config).toContain('"^/diagnostics(?:/|$)": apiProxyWithHtmlFallback');
    expect(config).not.toContain('"/diagnostics"');
  });

  it("serves SPA html for /mt5 and /auto-trade router refresh", () => {
    expect(config).toContain('"^/mt5(?:/|$)"');
    expect(config).toContain('"^/auto-trade(?:/|$)"');
  });
});
