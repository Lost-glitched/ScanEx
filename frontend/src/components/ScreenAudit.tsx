import React, { useMemo, useState } from 'react';
import { AlertTriangle, ArrowRight, Download, FileCheck2, FileImage, FileText, Lock, RotateCcw, ShieldCheck, Unlock } from 'lucide-react';
import type { FileScanResult, Finding, Priority } from '../types';

interface ScreenAuditProps {
  results: FileScanResult[];
  resolvedIds: Set<string>;
  onToggleResolve: (id: string) => void;
  onExportReport: () => void;
  onCommitPipeline: () => void;
  onResetAll: () => void;
}

interface AuditFinding { id: string; fileName: string; kind: string; detail: string; confidence?: number; source: string; priority: Priority; }

const PRIORITY_ORDER: Record<Priority, number> = { high: 0, medium: 1, low: 2 };

const PRIORITY_BADGE: Record<Priority, string> = {
  high: 'bg-[#fef2f2] text-[#991b1b] border-[#fecaca]',
  medium: 'bg-[#fefce8] text-[#854d0e] border-[#fef08a]',
  low: 'bg-[#f5f5f4] text-[#57534e] border-[#e7e5e4]',
};

function buildFindings(results: FileScanResult[]): AuditFinding[] {
  const all = results.flatMap((result) => {
    const baseline = result.baseline;
    const adversarial = result.adversarial;
    if (!baseline && !adversarial) return result.error ? [{ id: `${result.stagedFile.id}-error`, fileName: result.stagedFile.name, kind: 'Scan error', detail: result.error, source: 'ScanEx response', priority: 'low' as Priority }] : [];
    const findings: AuditFinding[] = [];
    const addFinding = (finding: Finding, kind: string) => findings.push({ id: `${result.stagedFile.id}-${findings.length}`, fileName: result.stagedFile.name, kind, detail: finding.text, confidence: finding.confidence, source: finding.entity_type, priority: finding.priority });
    if (baseline) {
      baseline.pii_findings.forEach((finding) => addFinding(finding, 'PII finding'));
      baseline.financial_findings.forEach((finding) => addFinding(finding, 'Financial finding'));
      baseline.redaction_failures.forEach((failure, index) => findings.push({ id: `${result.stagedFile.id}-redaction-${index}`, fileName: result.stagedFile.name, kind: 'Redaction failure', detail: `Page ${failure.page}: ${failure.recovered_text}`, source: 'PDF redaction check', priority: 'high' }));
      baseline.severity_flags.forEach((flag, index) => findings.push({ id: `${result.stagedFile.id}-severity-${index}`, fileName: result.stagedFile.name, kind: 'Severity flag', detail: flag, source: 'ScanEx response', priority: 'medium' }));
    }
    adversarial?.vlm_analysis?.observations.forEach((observation) => findings.push({ id: `${result.stagedFile.id}-${findings.length}`, fileName: result.stagedFile.name, kind: `Adversarial clue (${observation.clue_type})`, detail: `${observation.description} Possible inference: ${observation.possible_inference}`, confidence: observation.confidence, source: `${adversarial.vlm_analysis?.model_used} · ${adversarial.vlm_analysis.identity_risk_level} identity risk`, priority: 'medium' }));
    if (adversarial?.geolocation) findings.push({ id: `${result.stagedFile.id}-${findings.length}`, fileName: result.stagedFile.name, kind: 'Geolocation inferred', detail: `${adversarial.geolocation.lat.toFixed(4)}, ${adversarial.geolocation.lon.toFixed(4)}`, confidence: adversarial.geolocation.confidence, source: 'GeoCLIP', priority: 'medium' });
    adversarial?.severity_flags.forEach((flag) => findings.push({ id: `${result.stagedFile.id}-${findings.length}`, fileName: result.stagedFile.name, kind: 'Adversarial severity flag', detail: flag, source: 'Adversarial response', priority: 'medium' }));
    if (adversarial?.error) findings.push({ id: `${result.stagedFile.id}-${findings.length}`, fileName: result.stagedFile.name, kind: 'Adversarial scan error', detail: adversarial.error, source: 'Adversarial response', priority: 'low' });
    return findings;
  });
  return all.sort((a, b) => PRIORITY_ORDER[a.priority] - PRIORITY_ORDER[b.priority]);
}

export const ScreenAudit: React.FC<ScreenAuditProps> = ({ results, resolvedIds, onToggleResolve, onExportReport, onCommitPipeline, onResetAll }) => {
  const [copiedLocation, setCopiedLocation] = useState(false);
  const [priorityFilter, setPriorityFilter] = useState<Priority | null>(null);
  const findings = useMemo(() => buildFindings(results), [results]);
  const filtered = priorityFilter ? findings.filter((f) => f.priority === priorityFilter) : findings;
  const pending = filtered.filter((finding) => !resolvedIds.has(finding.id));
  const allResolved = findings.length > 0 && findings.every((f) => resolvedIds.has(f.id));
  const flaggedFiles = new Set(pending.map((finding) => finding.fileName)).size;
  const cleanFiles = Math.max(0, results.length - flaggedFiles);
  const handleCopyLocation = () => { navigator.clipboard?.writeText?.(window.location.href); setCopiedLocation(true); window.setTimeout(() => setCopiedLocation(false), 1500); };

  const filterButtons: { label: string; value: Priority | null }[] = [{ label: 'All', value: null }, { label: 'High', value: 'high' }, { label: 'Medium', value: 'medium' }, { label: 'Low', value: 'low' }];

  return (
    <div className="max-w-6xl mx-auto space-y-8 animate-in fade-in duration-300">
      <div className="bg-[#fcf2eb] border border-[#f0e6e0] rounded-2xl p-4 sm:p-5 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 shadow-xs"><div className="flex items-start gap-3"><div className="w-8 h-8 rounded-full bg-white flex items-center justify-center text-[#854d0e] border border-[#e7e5e4]"><AlertTriangle className="w-4 h-4" /></div><p className="text-sm font-medium text-[#1f1b17]">{results.length ? `Inspection completed for ${results.length} file${results.length === 1 ? '' : 's'}.` : 'No scan results are available yet.'}</p></div><div className="flex items-center gap-3"><button onClick={handleCopyLocation} className="text-xs text-[#717971] hover:text-[#1f1b17] cursor-pointer">{copiedLocation ? 'Copied' : 'Copy session link'}</button><span className={`px-3 py-1 rounded-full text-xs font-semibold ${allResolved ? 'bg-[#e8f5e9] text-[#166534] border border-[#bbf7d0]' : 'bg-[#fef9c3] text-[#854d0e] border border-[#fef08a]'}`}>{allResolved ? 'Locally reviewed' : 'Review needed'}</span></div></div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 sm:gap-6"><div className="bg-white border border-[#e7e5e4] rounded-2xl p-6 shadow-xs"><div className="flex items-center justify-between text-xs font-semibold text-[#a8a29e] uppercase tracking-wider"><span>Checked files</span><FileCheck2 className="w-4 h-4" /></div><p className="my-4 text-3xl font-bold text-[#1f1b17] font-mono">{results.length}</p><div className="text-xs text-[#717971]">{cleanFiles} without pending findings · {flaggedFiles} flagged</div></div><div className="bg-white border border-[#e7e5e4] rounded-2xl p-6 shadow-xs"><div className="flex items-center justify-between text-xs font-semibold text-[#a8a29e] uppercase tracking-wider"><span>Findings</span><ShieldCheck className="w-4 h-4" /></div><p className="my-4 text-3xl font-bold text-[#b45309] font-mono">{findings.length}</p><div className="text-xs text-[#717971]">{pending.length} pending local review</div></div><div className={`border rounded-2xl p-6 shadow-xs ${allResolved ? 'bg-[#e8f5e9]/40 border-[#bbf7d0]' : 'bg-white border-[#e7e5e4]'}`}><div className="flex items-center justify-between text-xs font-semibold text-[#a8a29e] uppercase tracking-wider"><span>Backend actions</span>{allResolved ? <Unlock className="w-4 h-4 text-[#166534]" /> : <Lock className="w-4 h-4 text-[#991b1b]" />}</div><p className={`my-4 text-lg font-bold ${allResolved ? 'text-[#166534]' : 'text-[#991b1b]'}`}>Not available</p><div className="text-xs text-[#717971]">Resolve and commit endpoints are Phase 2.</div></div></div>

      <div className="space-y-4"><div className="flex items-center justify-between px-1"><div><h2 className="text-base sm:text-lg font-semibold text-[#1f1b17]">Findings from ScanEx</h2><p className="text-xs sm:text-sm text-[#717971]">Values and metadata below are taken directly from the scan responses.</p></div>{resolvedIds.size > 0 && <button onClick={onResetAll} className="text-xs text-[#717971] hover:text-[#292524] flex items-center gap-1 cursor-pointer"><RotateCcw className="w-3 h-3" />Reset local review</button>}</div><div className="flex items-center gap-2 px-1">{filterButtons.map((btn) => <button key={btn.label} onClick={() => setPriorityFilter(btn.value)} className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors cursor-pointer ${priorityFilter === btn.value ? 'bg-[#316342] text-white border-[#316342]' : 'bg-white text-[#57534e] border-[#e7e5e4] hover:border-[#316342]'}`}>{btn.label}</button>)}</div><div className="space-y-4">{filtered.map((finding) => { const resolved = resolvedIds.has(finding.id); return <div key={finding.id} className={`bg-white border rounded-2xl p-5 sm:p-6 shadow-xs ${resolved ? 'border-[#bbf7d0] bg-[#fafdfa]' : 'border-[#e7e5e4]'}`}><div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-[#f5f5f4]"><div className="flex items-start gap-3"><div className="w-8 h-8 rounded-lg bg-[#fafaf9] border border-[#e7e5e4] flex items-center justify-center">{finding.fileName.match(/\.(jpg|jpeg|png|heic)$/i) ? <FileImage className="w-4 h-4 text-amber-700" /> : <FileText className="w-4 h-4 text-rose-700" />}</div><div><div className="flex items-center gap-2 flex-wrap"><span className="text-sm font-semibold font-mono text-[#1f1b17]">{finding.fileName}</span><span className="px-2.5 py-0.5 rounded-full text-[11px] font-medium bg-[#fcf2eb] text-[#854d0e] border border-[#f0e6e0]">{finding.kind}</span><span className={`px-2.5 py-0.5 rounded-full text-[11px] font-medium border ${PRIORITY_BADGE[finding.priority]}`}>{finding.priority}</span></div><p className="text-xs text-[#717971] mt-0.5">{finding.source}{finding.confidence !== undefined ? ` · ${Math.round(finding.confidence * 100)}% confidence` : ''}</p></div></div><button onClick={() => onToggleResolve(finding.id)} className={`px-4 py-2 rounded-xl text-xs font-semibold cursor-pointer ${resolved ? 'bg-[#e8f5e9] text-[#166534] border border-[#bbf7d0]' : 'bg-white text-[#292524] border border-[#e7e5e4] hover:border-[#316342]'}`}>{resolved ? 'Reviewed locally' : 'Mark reviewed locally'}</button></div><div className="mt-4 bg-[#fafaf9] border border-[#e7e5e4] rounded-xl p-4 text-xs sm:text-sm text-[#57534e] leading-relaxed break-words">{finding.detail}</div></div>; })}{filtered.length === 0 && <div className="bg-white border border-[#e7e5e4] rounded-2xl p-10 text-center text-sm text-[#717971]">{priorityFilter ? `No ${priorityFilter}-priority findings.` : 'No findings were returned by the backend.'}</div>}</div></div>

      <div className="bg-white border border-[#e7e5e4] rounded-2xl p-4 sm:p-5 shadow-xs flex flex-col sm:flex-row items-center justify-between gap-4"><div><p className="text-xs font-semibold text-[#a8a29e] uppercase tracking-wider">Phase 1 actions</p><p className="text-sm font-medium text-[#1f1b17]">Export is generated locally from returned responses. Resolve and commit are not persisted.</p></div><div className="flex items-center gap-3 w-full sm:w-auto"><button onClick={onExportReport} className="flex-1 px-5 py-2.5 text-xs font-medium text-[#292524] bg-white border border-[#e7e5e4] rounded-xl flex items-center justify-center gap-2 cursor-pointer"><Download className="w-4 h-4" />Export response report</button><button disabled onClick={onCommitPipeline} className="flex-1 px-6 py-2.5 text-xs font-semibold rounded-xl text-white bg-[#a8a29e] cursor-not-allowed flex items-center justify-center gap-2"><span>Commit unavailable</span><ArrowRight className="w-4 h-4" /></button></div></div>
    </div>
  );
};
