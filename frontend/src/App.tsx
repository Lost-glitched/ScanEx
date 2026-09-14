import React, { useCallback, useState } from 'react';
import { Header } from './components/Header';
import { ScreenUpload } from './components/ScreenUpload';
import { ScreenPipeline } from './components/ScreenPipeline';
import { ScreenAudit } from './components/ScreenAudit';
import { AuditReportModal } from './components/AuditReportModal';
import type { FileScanResult, StagedFile, TabType } from './types';

export default function App() {
  const [currentTab, setCurrentTab] = useState<TabType>('upload');
  const [stagedFiles, setStagedFiles] = useState<StagedFile[]>([]);
  const [results, setResults] = useState<FileScanResult[]>([]);
  const [resolvedIds, setResolvedIds] = useState<Set<string>>(new Set());
  const [showReportModal, setShowReportModal] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);

  const handleAddFiles = useCallback((newFiles: StagedFile[]) => {
    setUploadError(null);
    setStagedFiles((previous) => [...previous, ...newFiles]);
  }, []);
  const handleRemoveFile = useCallback((id: string) => setStagedFiles((previous) => previous.filter((file) => file.id !== id)), []);
  const handleClearFiles = useCallback(() => { setStagedFiles([]); setResults([]); setResolvedIds(new Set()); }, []);
  const handleFileStatus = useCallback((id: string, status: StagedFile['status'], error?: string) => setStagedFiles((previous) => previous.map((file) => file.id === id ? { ...file, status, error } : file)), []);
  const handleStartInspection = useCallback(() => { setResults([]); setResolvedIds(new Set()); setCurrentTab('pipeline'); }, []);
  const handleToggleResolve = useCallback((id: string) => setResolvedIds((previous) => { const next = new Set(previous); if (next.has(id)) next.delete(id); else next.add(id); return next; }), []);
  const findingCount = results.reduce((sum, result) => sum + (result.baseline?.pii_findings.length || 0) + (result.baseline?.financial_findings.length || 0) + (result.baseline?.redaction_failures.length || 0), 0);

  return <div className="min-h-screen bg-[#fff8f5] text-[#1f1b17] flex flex-col selection:bg-[#316342]/20 selection:text-[#166534]"><Header currentTab={currentTab} onSelectTab={setCurrentTab} flaggedCount={findingCount} /><main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-8 py-8 md:py-10">{currentTab === 'upload' && <ScreenUpload files={stagedFiles} onAddFiles={handleAddFiles} onRemoveFile={handleRemoveFile} onClearAll={handleClearFiles} onStartInspection={handleStartInspection} error={uploadError} onError={setUploadError} />}{currentTab === 'pipeline' && <ScreenPipeline files={stagedFiles} results={results} onResults={setResults} onFileStatus={handleFileStatus} onProceedToAudit={() => setCurrentTab('audit')} onCancelScan={() => setCurrentTab('upload')} />}{currentTab === 'audit' && <ScreenAudit results={results} resolvedIds={resolvedIds} onToggleResolve={handleToggleResolve} onExportReport={() => setShowReportModal(true)} onCommitPipeline={() => undefined} onResetAll={() => setResolvedIds(new Set())} />}</main><footer className="border-t border-[#e7e5e4] bg-[#fafaf9] py-4 px-4 sm:px-8 text-center text-xs text-[#717971]"><div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-2"><span className="font-semibold text-[#1f1b17]">ScanX Zero-Retention Guard</span><span>Connected to ScanEx baseline and adversarial endpoints</span></div></footer><AuditReportModal isOpen={showReportModal} onClose={() => setShowReportModal(false)} results={results} /></div>;
}
