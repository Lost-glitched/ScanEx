import React, { useState } from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { createRoot } from 'react-dom/client';
import { act } from 'react';
import { ScreenPipeline } from '../ScreenPipeline';
import type { FileScanResult, StagedFile, ScanResponse, AdversarialResponse } from '../../types';
import * as scanClient from '../../api/scanClient';

vi.mock('../../api/scanClient');

(globalThis as any).IS_REACT_ACT_ENVIRONMENT = true;

describe('ScreenPipeline multi-file scanning regression', () => {
  const mockBaselineResponse: ScanResponse = {
    filename: 'test.pdf',
    file_type: 'pdf',
    metadata: { gps: null, device: null, timestamps: { created: null, modified: null }, author: null, last_modified_by: null, hidden_content: [] },
    pii_findings: [],
    financial_findings: [],
    redaction_failures: [],
    severity_flags: [],
    overall_priority: 'low',
    error: null,
  };

  const mockAdversarialResponse: AdversarialResponse = {
    filename: 'photo.jpg',
    vlm_analysis: null,
    geolocation: null,
    severity_flags: [],
    error: null,
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('scans every staged file to completion, not stopping after the first', async () => {
    vi.mocked(scanClient.scanBaseline).mockImplementation(async (file: File) => {
      await new Promise((resolve) => setTimeout(resolve, 10));
      return { ...mockBaselineResponse, filename: file.name };
    });

    vi.mocked(scanClient.scanAdversarial).mockImplementation(async (file: File) => {
      await new Promise((resolve) => setTimeout(resolve, 10));
      return { ...mockAdversarialResponse, filename: file.name };
    });

    const stagedFiles: StagedFile[] = [
      { id: 'file-1', name: 'resume.pdf', type: 'application/pdf', size: '1 KB', category: 'pdf', file: new File(['dummy1'], 'resume.pdf', { type: 'application/pdf' }), status: 'ready' },
      { id: 'file-2', name: 'id_card.png', type: 'image/png', size: '2 KB', category: 'image', file: new File(['dummy2'], 'id_card.png', { type: 'image/png' }), status: 'ready' },
      { id: 'file-3', name: 'statement.docx', type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', size: '4 KB', category: 'doc', file: new File(['dummy3'], 'statement.docx', { type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' }), status: 'ready' },
    ];

    const fileStatusCalls: { id: string; status: StagedFile['status'] }[] = [];
    const resultsUpdates: FileScanResult[][] = [];

    function TestHarness() {
      const [files, setFiles] = useState<StagedFile[]>(stagedFiles);
      const [results, setResults] = useState<FileScanResult[]>([]);

      const handleFileStatus = (id: string, status: StagedFile['status'], error?: string) => {
        fileStatusCalls.push({ id, status });
        setFiles((previous) => previous.map((file) => file.id === id ? { ...file, status, error } : file));
      };

      const handleResults = (newResults: FileScanResult[]) => {
        resultsUpdates.push(newResults);
        setResults(newResults);
      };

      return (
        <ScreenPipeline
          files={files}
          results={results}
          onResults={handleResults}
          onFileStatus={handleFileStatus}
          onProceedToAudit={() => {}}
          onCancelScan={() => {}}
        />
      );
    }

    const container = document.createElement('div');
    document.body.appendChild(container);
    const root = createRoot(container);

    await act(async () => {
      root.render(
        <React.StrictMode>
          <TestHarness />
        </React.StrictMode>
      );
    });

    const startTime = Date.now();
    while (Date.now() - startTime < 3000) {
      await act(async () => {
        await new Promise((resolve) => setTimeout(resolve, 50));
      });
      const latestResults = resultsUpdates[resultsUpdates.length - 1] || [];
      if (latestResults.length === stagedFiles.length) {
        break;
      }
    }

    const finalResults = resultsUpdates[resultsUpdates.length - 1] || [];

    // Assert that scanBaseline was called for all 3 files
    expect(scanClient.scanBaseline).toHaveBeenCalledTimes(3);

    // Assert that scanAdversarial was called for the image file
    expect(scanClient.scanAdversarial).toHaveBeenCalledTimes(1);

    // Assert that onFileStatus marked all files complete
    expect(fileStatusCalls.filter((c) => c.status === 'complete')).toHaveLength(3);

    // Assert that results contains all 3 files
    expect(finalResults).toHaveLength(3);
    expect(finalResults.map((r) => r.stagedFile.id)).toEqual(['file-1', 'file-2', 'file-3']);

    await act(async () => {
      root.unmount();
    });
    container.remove();
  });

  it('cancels the scan when unmounted mid-scan and does not process remaining files', async () => {
    vi.mocked(scanClient.scanBaseline).mockImplementation(async (file: File) => {
      await new Promise((resolve) => setTimeout(resolve, 50));
      return { ...mockBaselineResponse, filename: file.name };
    });

    const stagedFiles: StagedFile[] = [
      { id: 'cancel-1', name: 'f1.pdf', type: 'application/pdf', size: '1 KB', category: 'pdf', file: new File(['dummy1'], 'f1.pdf', { type: 'application/pdf' }), status: 'ready' },
      { id: 'cancel-2', name: 'f2.pdf', type: 'application/pdf', size: '2 KB', category: 'pdf', file: new File(['dummy2'], 'f2.pdf', { type: 'application/pdf' }), status: 'ready' },
    ];

    const container = document.createElement('div');
    document.body.appendChild(container);
    const root = createRoot(container);

    await act(async () => {
      root.render(
        <ScreenPipeline
          files={stagedFiles}
          results={[]}
          onResults={() => {}}
          onFileStatus={() => {}}
          onProceedToAudit={() => {}}
          onCancelScan={() => {}}
        />
      );
    });

    // Unmount while file 1 is being processed
    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 10));
      root.unmount();
    });

    // Wait past what file 2 would have taken
    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 100));
    });

    // Only file 1 was called; file 2 was never dispatched due to cancellation
    expect(scanClient.scanBaseline).toHaveBeenCalledTimes(1);
    container.remove();
  });
});
