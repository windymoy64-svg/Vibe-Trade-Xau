import { useState } from "react";
import { Copy, RefreshCw, Shield, CheckCircle2, AlertCircle, KeyRound } from "lucide-react";

type TokenType = "mcp" | "api" | "webhook";

interface TokenConfig {
  id: string;
  name: string;
  type: TokenType;
  prefix: string;
  expiryHours: number;
}

const tokenConfigs: TokenConfig[] = [
  { id: "t1", name: "MCP Access Token", type: "mcp", prefix: "ngpk_", expiryHours: 168 },
  { id: "t2", name: "API Key", type: "api", prefix: "vpk_", expiryHours: 720 },
  { id: "t3", name: "Webhook Secret", type: "webhook", prefix: "whsk_", expiryHours: 8760 },
];

export function EaTokenGenerator() {
  const [generatedTokens, setGeneratedTokens] = useState<Map<string, string>>(new Map());
  const [copiedId, setCopiedId] = useState<string | null>(null);

  const generateToken = (config: TokenConfig) => {
    const chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789";
    let token = config.prefix;
    for (let i = 0; i < 32; i++) {
      token += chars.charAt(Math.floor(Math.random() * chars.length));
    }
    setGeneratedTokens((prev) => new Map(prev).set(config.id, token));
    setCopiedId(null);
  };

  const copyToClipboard = (token: string, id: string) => {
    navigator.clipboard.writeText(token);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  return (
    <div className="space-y-4">
      <h3 className="font-semibold flex items-center gap-2">
        <KeyRound className="h-5 w-5 text-primary" />
        Token Generator
      </h3>
      <p className="text-xs text-muted-foreground">Generate unique tokens for MCP authentication and API access</p>

      <div className="space-y-3">
        {tokenConfigs.map((config) => {
          const generated = generatedTokens.get(config.id);
          return (
            <div key={config.id} className="rounded-lg border bg-card p-4">
              <div className="flex items-start justify-between">
                <div>
                  <p className="font-medium text-sm">{config.name}</p>
                  <div className="mt-1 flex items-center gap-2 text-xs text-muted-foreground">
                    <span className={`inline-flex items-center rounded px-1.5 py-0.5 font-semibold ${
                      config.type === "mcp" ? "bg-sky-500/10 text-sky-500" :
                      config.type === "api" ? "bg-emerald-500/10 text-emerald-500" :
                      "bg-amber-500/10 text-amber-500"
                    }`}>
                      {config.type.toUpperCase()}
                    </span>
                    <span>Expires in {config.expiryHours}h</span>
                  </div>
                </div>
                <button
                  onClick={() => generateToken(config)}
                  disabled={!!generated}
                  className="inline-flex items-center gap-1 rounded-md border bg-card px-2 py-1 text-xs font-medium hover:bg-muted disabled:opacity-50"
                >
                  <RefreshCw className="h-3 w-3" />
                  Generate
                </button>
              </div>

              {generated && (
                <div className="mt-3">
                  <div className="flex items-center gap-2 rounded-md border bg-muted/50 px-3 py-2 font-mono text-xs break-all">
                    <span className="text-muted-foreground">{generated.slice(0, 8)}</span>
                    <span className="text-muted">••••••••</span>
                    <span className="text-muted-foreground">{generated.slice(-8)}</span>
                    <button
                      onClick={() => copyToClipboard(generated, config.id)}
                      className="ml-auto inline-flex items-center gap-1 text-muted-foreground hover:text-foreground"
                    >
                      {copiedId === config.id ? (
                        <>
                          <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500" />
                          Copied
                        </>
                      ) : (
                        <>
                          <Copy className="h-3.5 w-3.5" />
                          Copy
                        </>
                      )}
                    </button>
                  </div>
                  <p className="mt-2 text-[10px] text-muted-foreground flex items-center gap-1">
                    <Shield className="h-3 w-3" />
                    Store securely - token shown only once after generation
                  </p>
                </div>
              )}

              {!generated && (
                <div className="mt-3 flex items-center gap-2 text-xs text-muted-foreground">
                  <AlertCircle className="h-3.5 w-3.5" />
                  Click generate to create a new token
                </div>
              )}
            </div>
          );
        })}
      </div>

      <div className="rounded-lg border border-amber-500/20 bg-amber-500/5 p-4">
        <div className="flex items-start gap-2">
          <AlertCircle className="h-4 w-4 text-amber-500 mt-0.5" />
          <div className="text-xs text-amber-700">
            <p className="font-medium">Security Notice</p>
            <p className="mt-1">
              Tokens are displayed only once after generation. Save them securely before leaving this page.
              Regenerating a token will invalidate the previous one immediately.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
