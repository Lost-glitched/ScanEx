import React, { useEffect, useMemo, useState } from 'react';
import { AlertTriangle, ArrowRight, Brain, CheckCircle, Eye, FileText, KeyRound, ScanLine, ShieldCheck, X } from 'lucide-react';
import { scanAdversarial, scanBaseline, ScanClientError } from '../api/scanClient';
import type { FileScanResult, StagedFile } from '../types';

interface ScreenPipelineProps {
  files: StagedFile[];
  results: FileScanResult[];
  onResults: (results: FileScanResult[]) => void;
  onFileStatus: (id: string, status: StagedFile['status'], error?: string) => void;
  onProceedToAudit: () => void;
  onCancelScan: () => void;
}

function isImage(file: StagedFile): boolean { return file.category === 'image'; }

export const ScreenPipeline: React.FC<ScreenPipelineProps> = ({ files, results, onResults, onFileStatus, onProceedToAudit, onCancelScan }) => {
  const [started, setStarted] = useState(false);

  useEffect(() => {
    if (started || files.length === 0) return;
    setStarted(true);
    let cancelled = false;
    const scanFiles = async () => {
      const completed: FileScanResult[] = [];
      for (const stagedFile of files) {
        if (cancelled) return;
        onFileStatus(stagedFile.id, 'scanning');
        try {
          const baseline = await scanBaseline(stagedFile.file);
          const adversarial = isImage(stagedFile) ? await scanAdversarial(stagedFile.file) : null;
          const error = baseline.error || adversarial?.error || null;
          const result = { stagedFile: { ...stagedFile, status: error ? 'error' : 'complete', error: error || undefined }, baseline, adversarial, error } satisfies FileScanResult;
          completed.push(result);
          onResults([...completed]);
          onFileStatus(stagedFile.id, error ? 'error' : 'complete', error || undefined);
        } catch (error) {
          const message = error instanceof ScanClientError ? error.message : 'The scan failed unexpectedly.';
          const result = { stagedFile: { ...stagedFile, status: 'error', error: message }, baseline: null, adversarial: null, error: message } satisfies FileScanResult;
          completed.push(result);
          onResults([...completed]);
          onFileStatus(stagedFile.id, 'error', message);
        }
      }
    };
    void scanFiles();
    return () => { cancelled = true; };
  }, [files, onFileStatus, onResults, started]);

  const completedCount = results.length;
  const progress = files.length === 0 ? 0 : Math.round((completedCount / files.length) * 100);
  const activeFile = files.find((file) => file.status === 'scanning') || files[completedCount] || files[files.length - 1];
  const canProceed = completedCount === files.length && files.length > 0;
  const findingsCount = results.reduce((sum, item) => sum + (item.baseline?.pii_findings.length || 0) + (item.baseline?.financial_findings.length || 0) + (item.baseline?.redaction_failures.length || 0) + (item.adversarial?.vlm_analysis?.observations.length || 0) + (item.adversarial?.geolocation ? 1 : 0), 0);

  const engines = useMemo(() => [
    { name: 'Baseline metadata', icon: <ScanLine className="w-5 h-5 text-[#57534e]" />, count: results.filter((item) => item.baseline && (item.baseline.metadata.hidden_content.length > 0 || item.baseline.metadata.gps)).length, label: 'files with metadata signals' },
    { name: 'PII findings', icon: <Brain className="w-5 h-5 text-[#316342]" />, count: results.reduce((sum, item) => sum + (item.baseline?.pii_findings.length || 0), 0), label: 'matches returned' },
    { name: 'Financial findings', icon: <KeyRound className="w-5 h-5 text-[#b45309]" />, count: results.reduce((sum, item) => sum + (item.baseline?.financial_findings.length || 0), 0), label: 'masked matches returned' },
    { name: 'High priority', icon: <AlertTriangle className="w-5 h-5 text-[#991b1b]" />, count: results.reduce((sum, item) => sum + (item.baseline?.pii_findings.filter((f) => f.priority === 'high').length || 0) + (item.baseline?.financial_findings.filter((f) => f.priority === 'high').length || 0), 0), label: 'high-priority findings' },
    { name: 'Redaction failures', icon: <ShieldCheck className="w-5 h-5 text-[#166534]" />, count: results.reduce((sum, item) => sum + (item.baseline?.redaction_failures.length || 0), 0), label: 'PDF failures returned' },
    { name: 'Adversarial observations', icon: <Eye className="w-5 h-5 text-[#316342]" />, count: results.reduce((sum, item) => sum + (item.adversarial?.vlm_analysis?.observations.length || 0) + (item.adversarial?.geolocation ? 1 : 0), 0), label: 'identity/location clues returned' },
  ], [results]);

  const logs = results.flatMap((item) => {
    const lines: string[] = [];
    if (item.baseline) lines.push(`${item.stagedFile.name}: baseline response received`);
    if (item.baseline?.metadata.hidden_content.length) lines.push(`${item.stagedFile.name}: ${item.baseline.metadata.hidden_content.length} metadata signals returned`);
    if (item.baseline?.pii_findings.length) lines.push(`${item.stagedFile.name}: ${item.baseline.pii_findings.length} PII findings returned`);
    if (item.baseline?.financial_findings.length) lines.push(`${item.stagedFile.name}: ${item.baseline.financial_findings.length} masked financial findings returned`);
    if (item.baseline?.redaction_failures.length) lines.push(`${item.stagedFile.name}: ${item.baseline.redaction_failures.length} redaction failures returned`);
    if (item.adversarial) lines.push(`${item.stagedFile.name}: adversarial response received (${item.adversarial.vlm_analysis?.model_used || 'no VLM model result'})`);
    if (item.adversarial?.vlm_analysis?.observations.length) lines.push(`${item.stagedFile.name}: ${item.adversarial.vlm_analysis.observations.length} adversarial observations returned (${item.adversarial.vlm_analysis.identity_risk_level} identity risk)`);
    if (item.adversarial?.geolocation) lines.push(`${item.stagedFile.name}: geolocation inferred at ${item.adversarial.geolocation.lat.toFixed(4)}, ${item.adversarial.geolocation.lon.toFixed(4)}`);
    if (item.adversarial?.error) lines.push(`${item.stagedFile.name}: adversarial error: ${item.adversarial.error}`);
    if (item.error) lines.push(`${item.stagedFile.name}: ${item.error}`);
    return lines;
  });

  return (
    <div className="max-w-6xl mx-auto space-y-8 animate-in fade-in duration-300">
      <div className="bg-white border border-[#e7e5e4] rounded-2xl p-6 sm:p-8 shadow-xs">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-center">
          <div className="lg:col-span-3 flex items-center justify-center lg:justify-start"><div className="relative w-28 h-28 flex items-center justify-center"><svg className="w-full h-full -rotate-90" viewBox="0 0 100 100"><circle cx="50" cy="50" r="42" stroke="#e7e5e4" strokeWidth="8" fill="transparent" /><circle cx="50" cy="50" r="42" stroke="#316342" strokeWidth="8" fill="transparent" strokeDasharray={2 * Math.PI * 42} strokeDashoffset={2 * Math.PI * 42 - (progress / 100) * 2 * Math.PI * 42} strokeLinecap="round" /></svg><div className="absolute inset-0 flex flex-col items-center justify-center"><span className="text-xl font-bold text-[#1f1b17]">{progress}%</span><span className="text-[10px] font-semibold text-[#717971] uppercase">Scanned</span></div></div></div>
          <div className="lg:col-span-6 space-y-3 text-center lg:text-left"><div className="flex items-center justify-center lg:justify-start gap-1.5 text-xs text-[#717971] font-medium"><FileText className="w-3.5 h-3.5" /><span>{completedCount} of {files.length} files completed</span></div><h2 className="text-lg sm:text-xl font-semibold text-[#1f1b17] font-mono tracking-tight">{activeFile?.name || 'Waiting for files'}</h2><p className="text-xs sm:text-sm text-[#717971] leading-relaxed">Baseline findings are returned by ScanEx. Image files also receive the independent adversarial pass.</p><div className="w-full bg-[#f0eee9] h-2 rounded-full overflow-hidden"><div className="bg-[#316342] h-full rounded-full transition-all duration-500" style={{ width: `${progress}%` }} /></div></div>
          <div className="lg:col-span-3 flex lg:flex-col justify-around items-center lg:items-end gap-4 border-t lg:border-t-0 lg:border-l border-[#f0eee9] pt-4 lg:pt-0 lg:pl-6"><div className="text-left lg:text-right"><p className="text-[11px] font-semibold text-[#a8a29e] uppercase">Findings returned</p><p className="text-2xl font-bold text-[#1f1b17]">{findingsCount}</p></div><div className="text-left lg:text-right"><p className="text-[11px] font-semibold text-[#a8a29e] uppercase">Status</p><p className="text-sm font-semibold text-[#316342]">{canProceed ? 'Complete' : 'Scanning'}</p></div></div>
        </div>
      </div>

      <div className="space-y-3"><h3 className="text-xs font-semibold text-[#717971] uppercase tracking-wider px-1">Scan data returned</h3><div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-6 gap-4">{engines.map((engine) => <div key={engine.name} className="bg-white border border-[#e7e5e4] rounded-2xl p-5 shadow-xs space-y-4"><div className="flex items-center justify-between"><div className="w-8 h-8 rounded-lg bg-[#fafaf9] border border-[#e7e5e4] flex items-center justify-center">{engine.icon}</div><span className="text-xs font-medium text-[#166534]">{completedCount ? 'Returned' : 'Waiting'}</span></div><div><h4 className="text-sm font-semibold text-[#1f1b17]">{engine.name}</h4><p className="text-xs text-[#717971] leading-relaxed">{engine.count} {engine.label}</p></div></div>)}</div></div>

      <div className="bg-white border border-[#e7e5e4] rounded-2xl p-5 sm:p-6 shadow-xs space-y-4"><div className="flex items-center justify-between pb-3 border-b border-[#f0eee9]"><div className="flex items-center gap-2"><span className="w-2 h-2 rounded-full bg-emerald-500" /><span className="text-xs font-bold tracking-wider text-[#1f1b17] uppercase">Activity from responses</span></div><span className="text-xs text-[#717971]">{logs.length} lines</span></div><div className="space-y-3 font-mono text-xs">{logs.length ? logs.map((log, index) => <div key={`${log}-${index}`} className="flex items-start gap-3 text-[#292524]"><span className="w-1.5 h-1.5 rounded-full mt-1.5 shrink-0 bg-slate-400" /><span className="break-words leading-relaxed">{log}</span></div>) : <p className="text-[#717971]">Waiting for the first backend response.</p>}</div></div>

      {results.some((item) => item.error) && <div role="alert" className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800 flex items-start gap-2"><AlertTriangle className="w-4 h-4 mt-0.5 shrink-0" /><span>{results.filter((item) => item.error).map((item) => `${item.stagedFile.name}: ${item.error}`).join(' ')}</span></div>}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-4 pt-2"><button onClick={onCancelScan} className="w-full sm:w-auto px-4 py-2 text-xs font-medium text-[#717971] hover:text-[#991b1b] bg-white border border-[#e7e5e4] rounded-xl flex items-center justify-center gap-2 cursor-pointer"><X className="w-3.5 h-3.5" />Cancel Scan</button><button id="proceed-audit-btn" disabled={!canProceed} onClick={onProceedToAudit} className={`w-full sm:w-auto px-6 py-2.5 text-sm font-semibold rounded-xl text-white flex items-center justify-center gap-2 shadow-xs ${canProceed ? 'bg-[#316342] hover:bg-[#3f6b4d] cursor-pointer' : 'bg-[#a8a29e] cursor-not-allowed'}`}><span>Proceed to Audit &amp; Verification</span><ArrowRight className="w-4 h-4" /></button></div>
    </div>
  );
};
