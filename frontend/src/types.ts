export type TabType = 'upload' | 'pipeline' | 'audit';

export type FileCategory = 'image' | 'pdf' | 'doc';
export type FileStatus = 'ready' | 'scanning' | 'complete' | 'error';

export interface ScanMetadata {
  gps: { lat?: number; lon?: number } | null;
  device: string | null;
  timestamps: { created: string | null; modified: string | null };
  author: string | null;
  last_modified_by: string | null;
  hidden_content: Array<Record<string, string>>;
}

export interface Finding {
  entity_type: string;
  text: string;
  confidence: number;
}

export interface RedactionFailure {
  page: number;
  recovered_text: string;
}

export interface ScanResponse {
  filename: string;
  file_type: 'image' | 'docx' | 'xlsx' | 'pptx' | 'pdf';
  metadata: ScanMetadata;
  pii_findings: Finding[];
  financial_findings: Finding[];
  redaction_failures: RedactionFailure[];
  severity_flags: string[];
  error: string | null;
}

export interface VLMObservation {
  clue_type: string;
  description: string;
  possible_inference: string;
  confidence: number;
}

export interface VLMAnalysis {
  model_used: 'qwen2.5vl:7b' | 'moondream:1.8b';
  observations: VLMObservation[];
  identity_risk_level: 'low' | 'medium' | 'high';
}

export interface AdversarialResponse {
  filename: string;
  vlm_analysis: VLMAnalysis | null;
  geolocation: { lat: number; lon: number; confidence?: number } | null;
  severity_flags: string[];
  error: string | null;
}

export interface StagedFile {
  id: string;
  file: File;
  name: string;
  type: string;
  size: string;
  status: FileStatus;
  error?: string;
  category: FileCategory;
}

export interface FileScanResult {
  stagedFile: StagedFile;
  baseline: ScanResponse | null;
  adversarial: AdversarialResponse | null;
  error: string | null;
}
