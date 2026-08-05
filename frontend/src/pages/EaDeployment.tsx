import { useState } from "react";
import { Shield, Download, Copy, CheckCircle, Clock, AlertCircle } from "lucide-react";

interface EADeploymentData {
  eaName: string;
  version: string;
  downloadUrl: string;
  installationSteps: string[];
  status: "ready" | "installing" | "active" | "error";
  lastDeployed?: string;
}

const mockDeploymentData: EADeploymentData = {
  eaName: "VibeTrading XAUUSD Bot v1.2",
  version: "1.2.0",
  downloadUrl: "/downloads/vibetrading-ea-v1.2.mq4",
  installationSteps: [
    "Copy .mq4 file to MetaTrader 5 \\MQL5\\Experts\\ directory",
    "Restart MT5 terminal or click Refresh in Navigator",
    "Enable AutoTrading in MT5 (top toolbar)",
    "Drag EA to XAUUSD chart",
    "Configure settings: Risk %, TP distance, SL buffer",
    "Press 'Connect' to establish MCP bridge at 127.0.0.1:22346",
    "Verify connection status shows 'Connected'",
  ],
  status: "ready",
  lastDeployed: "2026-08-04T10:30:00Z",
};

export default function EaDeploymentPage() {
  const [copied, setCopied] = useState(false);
  const [stepIndex, setStepIndex] = useState<number | null>(null);

  const handleCopyInstallationGuide = () => {
    navigator.clipboard.writeText(mockDeploymentData.installationSteps.join("\n"));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleMarkComplete = (index: number) => {
    if (window.confirm(`Mark step ${index + 1} as complete?`)) {
      setStepIndex(index);
    }
  };

  return (
    <div className="container mx-auto p-6 space-y-6">
      <header className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-slate-900">EA Deployment</h1>
        <button
          onClick={handleCopyInstallationGuide}
          disabled={copied}
          className={`inline-flex items-center gap-2 px-4 py-2 rounded-lg transition-colors ${
            copied
              ? "bg-emerald-100 text-emerald-700 cursor-default"
              : "bg-blue-600 hover:bg-blue-700 text-white"
          }`}
        >
          {copied ? (
            <>
              <CheckCircle className="w-4 h-4" />
              Copied!
            </>
          ) : (
            <>
              <Copy className="w-4 h-4" />
              Copy Guide
            </>
          )}
        </button>
      </header>

      <section className="bg-white rounded-lg shadow-sm border border-slate-200 p-6">
        <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <Shield className="w-5 h-5 text-blue-600" />
          Active EA Instance
        </h2>
        
        <div className="grid md:grid-cols-3 gap-4">
          <div className="p-4 bg-slate-50 rounded-lg">
            <h3 className="font-medium text-slate-700">EA Name</h3>
            <p className="text-xl font-bold text-slate-900 mt-1">{mockDeploymentData.eaName}</p>
          </div>
          
          <div className="p-4 bg-slate-50 rounded-lg">
            <h3 className="font-medium text-slate-700">Version</h3>
            <p className="text-xl font-bold text-slate-900 mt-1">{mockDeploymentData.version}</p>
          </div>
          
          <div className="p-4 bg-slate-50 rounded-lg">
            <h3 className="font-medium text-slate-700">Status</h3>
            <p className={`mt-1 font-semibold ${
              mockDeploymentData.status === "ready" || mockDeploymentData.status === "active"
                ? "text-emerald-600"
                : mockDeploymentData.status === "error"
                ? "text-red-600"
                : "text-orange-600"
            }`}>
              {mockDeploymentData.status.toUpperCase()}
            </p>
          </div>
        </div>

        <div className="mt-4 flex items-center gap-2 text-sm text-slate-500">
          <Clock className="w-4 h-4" />
          Last deployed: {new Date(mockDeploymentData.lastDeployed!).toLocaleString("id-ID")}
        </div>
      </section>

      <section className="bg-white rounded-lg shadow-sm border border-slate-200 p-6">
        <h2 className="text-lg font-semibold mb-4">Installation Steps</h2>
        
        <ol className="space-y-3">
          {mockDeploymentData.installationSteps.map((step, index) => (
            <li 
              key={index}
              className={`flex items-start gap-3 p-3 rounded-lg transition-all ${
                stepIndex !== null && index <= stepIndex
                  ? "bg-emerald-50 border border-emerald-200"
                  : "bg-slate-50 hover:bg-slate-100"
              }`}
            >
              <span className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center text-sm font-semibold ${
                stepIndex !== null && index <= stepIndex
                  ? "bg-emerald-500 text-white"
                  : "bg-slate-200 text-slate-600"
              }`}>
                {index + 1}
              </span>
              <span className="flex-1 text-sm text-slate-700 pt-1">{step}</span>
              <button
                onClick={() => handleMarkComplete(index)}
                className="flex-shrink-0 p-2 hover:bg-white rounded-full transition-colors"
                title="Mark as complete"
              >
                <CheckCircle className={`w-5 h-5 ${
                  stepIndex !== null && index <= stepIndex
                    ? "text-emerald-600"
                    : "text-slate-300 hover:text-slate-500"
                }`} />
              </button>
            </li>
          ))}
        </ol>
      </section>

      <section className="bg-white rounded-lg shadow-sm border border-slate-200 p-6">
        <h2 className="text-lg font-semibold mb-4">Download EA File</h2>
        
        <div className="flex items-center justify-between p-4 bg-slate-50 rounded-lg border border-slate-200">
          <div className="flex items-center gap-3">
            <Download className="w-8 h-8 text-blue-600" />
            <div>
              <h3 className="font-medium text-slate-900">{mockDeploymentData.eaName}.mq4</h3>
              <p className="text-sm text-slate-500">Size: 45 KB • MD5: a1b2c3d4e5f6...</p>
            </div>
          </div>
          <a
            href={mockDeploymentData.downloadUrl}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors"
          >
            Download Now
          </a>
        </div>
      </section>

      <section className="bg-white rounded-lg shadow-sm border border-slate-200 p-6">
        <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <AlertCircle className="w-5 h-5 text-orange-600" />
          Common Issues & Troubleshooting
        </h2>
        
        <div className="space-y-4">
          <div className="p-3 bg-orange-50 rounded-lg border border-orange-200">
            <h4 className="font-medium text-orange-900">Connection Failed</h4>
            <p className="text-sm text-orange-800 mt-1">
              Ensure MT5 is running and MCP server is active on port 22346. Check Windows Firewall settings.
            </p>
          </div>
          
          <div className="p-3 bg-orange-50 rounded-lg border border-orange-200">
            <h4 className="font-medium text-orange-900">AutoTrading Disabled</h4>
            <p className="text-sm text-orange-800 mt-1">
              Click the "AutoTrading" button in MT5 toolbar (should show green). Enable it if disabled.
            </p>
          </div>
          
          <div className="p-3 bg-orange-50 rounded-lg border border-orange-200">
            <h4 className="font-medium text-orange-900">EA Not Showing in Navigator</h4>
            <p className="text-sm text-orange-800 mt-1">
              Restart MT5 terminal after copying .mq4 file. Right-click Expert Advisors and select Refresh.
            </p>
          </div>
        </div>
      </section>
    </div>
  );
}
