import React, { useRef, useState } from 'react';
import { ArrowRight, CloudUpload, FileImage, FileText, FileSpreadsheet, FileType, X } from 'lucide-react';
import type { FileCategory, StagedFile } from '../types';

interface ScreenUploadProps {
  files: StagedFile[];
  onAddFiles: (newFiles: StagedFile[]) => void;
  onRemoveFile: (fileId: string) => void;
  onClearAll: () => void;
  onStartInspection: () => void;
  error: string | null;
  onError: (message: string | null) => void;
}

const supportedExtensions = new Set(['jpg', 'jpeg', 'png', 'heic', 'docx', 'xlsx', 'pptx', 'pdf']);

function formatSize(bytes: number): string {
  if (bytes === 0) return '0 B';
  if (bytes >= 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  return `${Math.max(1, Math.round(bytes / 1024))} KB`;
}

function fileCategory(file: File): { category: FileCategory; type: string } {
  const extension = file.name.split('.').pop()?.toLowerCase() || '';
  if (file.type.startsWith('image/')) return { category: 'image', type: 'Image' };
  if (file.type === 'application/pdf') return { category: 'pdf', type: 'PDF document' };
  if (['jpg', 'jpeg', 'png', 'heic'].includes(extension)) return { category: 'image', type: 'Image' };
  if (extension === 'pdf') return { category: 'pdf', type: 'PDF document' };
  if (extension === 'xlsx') return { category: 'doc', type: 'Spreadsheet' };
  if (extension === 'pptx') return { category: 'doc', type: 'Presentation' };
  return { category: 'doc', type: 'Word document' };
}

export const ScreenUpload: React.FC<ScreenUploadProps> = ({ files, onAddFiles, onRemoveFile, onClearAll, onStartInspection, error, onError }) => {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [isDragging, setIsDragging] = useState(false);

  const processNativeFiles = (fileList: FileList) => {
    const supported = Array.from(fileList).filter((file) => supportedExtensions.has(file.name.split('.').pop()?.toLowerCase() || ''));
    const rejected = Array.from(fileList).filter((file) => !supported.includes(file));
    onError(rejected.length ? `Unsupported file type: ${rejected.map((file) => file.name).join(', ')}. Supported types are JPG, JPEG, PNG, HEIC, DOCX, XLSX, PPTX, and PDF.` : null);
    const newItems = supported.map((file, index) => {
      const details = fileCategory(file);
      return {
        id: `${file.name}-${file.lastModified}-${index}`,
        file,
        name: file.name,
        type: details.type,
        size: formatSize(file.size),
        status: 'ready' as const,
        category: details.category,
      };
    });
    onAddFiles(newItems);
  };

  const iconFor = (category: FileCategory) => {
    if (category === 'image') return <FileImage className="w-5 h-5 text-amber-700" />;
    if (category === 'pdf') return <FileText className="w-5 h-5 text-rose-700" />;
    return <FileSpreadsheet className="w-5 h-5 text-sky-700" />;
  };

  const totalBytes = files.reduce((sum, item) => sum + item.file.size, 0);

  return (
    <div className="max-w-4xl mx-auto space-y-8 animate-in fade-in duration-300">
      <div className="space-y-1">
        <h1 className="text-2xl sm:text-3xl font-semibold tracking-tight text-[#1f1b17]">Document Screening</h1>
        <p className="text-sm sm:text-base text-[#57534e]">Stage files for a real baseline forensic scan.</p>
      </div>

      <div
        onDragOver={(event) => { event.preventDefault(); setIsDragging(true); }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={(event) => { event.preventDefault(); setIsDragging(false); processNativeFiles(event.dataTransfer.files); }}
        className={`relative bg-white border-2 border-dashed rounded-2xl p-8 sm:p-12 text-center transition-all duration-200 ${isDragging ? 'border-[#316342] bg-[#e8f5e9]/40' : 'border-[#e7e5e4] hover:border-[#316342]/50'}`}
      >
        <input ref={fileInputRef} type="file" multiple className="hidden" onChange={(event) => event.target.files && processNativeFiles(event.target.files)} accept=".jpg,.jpeg,.png,.heic,.docx,.xlsx,.pptx,.pdf" />
        <div className="flex flex-col items-center justify-center space-y-4">
          <div className="w-14 h-14 rounded-2xl bg-[#e8f5e9] flex items-center justify-center text-[#316342]"><CloudUpload className="w-7 h-7" /></div>
          <div className="space-y-1">
            <p className="text-base font-medium text-[#1f1b17]">Drop files to scan for sensitive data</p>
            <p className="text-xs sm:text-sm text-[#717971]">JPG, PNG, HEIC, DOCX, XLSX, PPTX, and PDF up to 25 MB each.</p>
          </div>
          <button onClick={() => fileInputRef.current?.click()} className="px-5 py-2 text-sm font-medium text-[#292524] bg-white border border-[#e7e5e4] hover:bg-[#f5f5f4] rounded-lg transition-colors shadow-xs cursor-pointer">Select files</button>
        </div>
      </div>

      {error && <div role="alert" className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800">{error}</div>}

      <div className="bg-white border border-[#e7e5e4] rounded-2xl p-6 shadow-xs space-y-4">
        <div className="flex items-center justify-between pb-3 border-b border-[#f0eee9]">
          <div className="flex items-center gap-2.5"><h2 className="text-base font-semibold text-[#1f1b17]">Staged Files</h2><span className="px-2.5 py-0.5 text-xs rounded-full bg-[#f5f5f4] text-[#57534e] border border-[#e7e5e4]">{files.length}</span></div>
          {files.length > 0 && <button onClick={onClearAll} className="text-xs font-medium text-[#717971] hover:text-[#991b1b] cursor-pointer">Clear all</button>}
        </div>
        <div className="divide-y divide-[#f5f5f4]">
          {files.map((file) => (
            <div key={file.id} className="py-3.5 px-2 flex items-center justify-between gap-4 hover:bg-[#fafaf9] rounded-lg">
              <div className="flex items-center gap-3.5 min-w-0"><div className="w-9 h-9 rounded-lg bg-[#f5f5f4] flex items-center justify-center shrink-0 border border-[#e7e5e4]/80">{iconFor(file.category)}</div><div className="min-w-0"><p className="text-sm font-medium text-[#1f1b17] truncate font-mono">{file.name}</p><p className="text-xs text-[#717971]">{file.type}</p></div></div>
              <div className="flex items-center gap-4 shrink-0"><span className="text-xs font-medium text-[#717971]">{file.size}</span><span className="flex items-center gap-1.5 text-xs font-medium text-[#166534]"><span className="w-1.5 h-1.5 rounded-full bg-[#166534]" />{file.status === 'ready' ? 'Ready' : file.status}</span><button onClick={() => onRemoveFile(file.id)} title="Remove file" className="p-1 text-[#a8a29e] hover:text-[#ba1a1a] cursor-pointer"><X className="w-4 h-4" /></button></div>
            </div>
          ))}
          {files.length === 0 && <div className="py-12 text-center text-sm text-[#717971]"><FileType className="w-8 h-8 mx-auto mb-3 text-[#a8a29e]" /><p>No files staged. Select or drop files to begin.</p></div>}
        </div>
      </div>

      <div className="bg-white border border-[#e7e5e4] rounded-2xl p-4 sm:p-5 shadow-xs flex flex-col sm:flex-row items-center justify-between gap-4">
        <div className="flex items-center gap-3"><div className="w-2.5 h-2.5 rounded-full bg-[#166534]" /><div><p className="text-sm font-medium text-[#1f1b17]">{files.length} files staged ({formatSize(totalBytes)} total)</p><p className="text-xs text-[#717971]">Ready for baseline analysis</p></div></div>
        <button id="start-inspection-btn" disabled={files.length === 0} onClick={onStartInspection} className={`px-6 py-2.5 text-sm font-semibold rounded-xl text-white flex items-center gap-2 shadow-xs cursor-pointer ${files.length > 0 ? 'bg-[#316342] hover:bg-[#3f6b4d]' : 'bg-[#a8a29e] cursor-not-allowed'}`}><span>Start Pipeline Inspection</span><ArrowRight className="w-4 h-4" /></button>
      </div>
    </div>
  );
};
