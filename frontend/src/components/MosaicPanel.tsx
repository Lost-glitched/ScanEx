import React from 'react';
import { AlertTriangle, CheckCircle2, FileText, Globe, HelpCircle, Layers, Network, ShieldAlert } from 'lucide-react';
import type { Convergence, MosaicResult, Priority } from '../types';

interface MosaicPanelProps {
  result: MosaicResult;
  onClose?: () => void;
}

const PRIORITY_BADGE: Record<Priority, string> = {
  high: 'bg-[#fef2f2] text-[#991b1b] border-[#fecaca]',
  medium: 'bg-[#fefce8] text-[#854d0e] border-[#fef08a]',
  low: 'bg-[#f5f5f4] text-[#57534e] border-[#e7e5e4]',
};

export const MosaicPanel: React.FC<MosaicPanelProps> = ({ result, onClose }) => {
  const { convergences, possible_associations = [], mosaic_score, file_count } = result;

  const scoreLevel = mosaic_score >= 6 ? 'High Mosaic Exposure' : mosaic_score > 0 ? 'Moderate Mosaic Exposure' : 'Isolated Batch Exposure';
  const scoreBadgeColor = mosaic_score >= 6 ? 'text-[#991b1b] bg-[#fef2f2] border-[#fecaca]' : mosaic_score > 0 ? 'text-[#854d0e] bg-[#fefce8] border-[#fef08a]' : 'text-[#166534] bg-[#f0fdf4] border-[#bbf7d0]';

  return (
    <div className="bg-white border border-[#e7e5e4] rounded-2xl p-6 shadow-xs space-y-6 animate-in fade-in duration-300">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-[#f0eee9]">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-[#fafaf9] border border-[#e7e5e4] flex items-center justify-center text-[#316342]">
              <Network className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-base font-semibold text-[#1f1b17] flex items-center gap-2">
                Layer C — Mosaic Risk Analysis
                <span className="text-xs font-normal text-[#717971]">({file_count} files analyzed)</span>
              </h3>
              <p className="text-xs text-[#717971]">
                Correlating cross-file identifiers, shared organizations, and geographic co-location.
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <div className="text-right">
            <p className="text-[10px] font-bold uppercase tracking-wider text-[#a8a29e]">Mosaic Score</p>
            <div className="flex items-center gap-2">
              <span className="text-2xl font-bold font-mono text-[#1f1b17]">{mosaic_score.toFixed(1)}</span>
              <span className={`text-xs px-2.5 py-0.5 rounded-full font-medium border ${scoreBadgeColor}`}>
                {scoreLevel}
              </span>
            </div>
          </div>
          {onClose && (
            <button
              onClick={onClose}
              className="text-[#717971] hover:text-[#1f1b17] text-xs px-2.5 py-1.5 rounded-lg border border-[#e7e5e4] hover:bg-[#fafaf9] cursor-pointer"
            >
              Dismiss
            </button>
          )}
        </div>
      </div>

      {convergences.length === 0 ? (
        <div className="p-8 rounded-xl bg-[#fafaf9] border border-[#e7e5e4] text-center space-y-2">
          <CheckCircle2 className="w-8 h-8 text-[#166534] mx-auto" />
          <h4 className="text-sm font-semibold text-[#1f1b17]">No Cross-File Convergences Detected</h4>
          <p className="text-xs text-[#717971] max-w-md mx-auto">
            Entities, identities, and geographic coordinates across the {file_count} analyzed files remain completely isolated with no shared footprint.
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-[#717971] uppercase tracking-wider">
              Detected Convergences ({convergences.length})
            </span>
            <span className="text-xs text-[#717971]">
              Ranked by risk weight and cluster size
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {convergences.map((conv, idx) => (
              <div
                key={`${conv.entity_type}-${conv.representative_text}-${idx}`}
                className="p-4 rounded-xl border border-[#e7e5e4] bg-[#fafaf9] hover:bg-white transition-colors space-y-3 shadow-2xs"
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="flex items-center gap-2">
                    {conv.entity_type === 'LOCATION_PROXIMITY' ? (
                      <Globe className="w-4 h-4 text-[#0284c7] shrink-0" />
                    ) : (
                      <Layers className="w-4 h-4 text-[#316342] shrink-0" />
                    )}
                    <span className="text-xs font-mono font-bold text-[#1f1b17] truncate">
                      {conv.representative_text}
                    </span>
                  </div>
                  <div className="flex items-center gap-1.5 shrink-0">
                    <span className="text-[10px] font-mono uppercase px-1.5 py-0.5 rounded-md bg-[#f5f5f4] text-[#57534e] border border-[#e7e5e4]">
                      {conv.entity_type}
                    </span>
                    <span className={`text-[10px] uppercase font-bold px-2 py-0.5 rounded-md border ${PRIORITY_BADGE[conv.priority]}`}>
                      {conv.priority}
                    </span>
                  </div>
                </div>

                <p className="text-xs text-[#44403c] leading-relaxed">
                  {conv.explanation}
                </p>

                <div className="pt-2 border-t border-[#e7e5e4]/60 flex flex-wrap items-center gap-1.5">
                  <span className="text-[10px] font-semibold text-[#a8a29e] uppercase">Linked Files:</span>
                  {conv.source_files.map((file) => (
                    <span
                      key={file}
                      className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-white border border-[#e7e5e4] text-[11px] font-mono text-[#292524]"
                    >
                      <FileText className="w-3 h-3 text-[#717971]" />
                      {file}
                    </span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {possible_associations.length > 0 && (
        <div className="space-y-3 pt-2 border-t border-[#f0eee9]">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="text-xs font-semibold text-[#717971] uppercase tracking-wider">
                Possible Associations (unconfirmed)
              </span>
              <span className="px-2 py-0.5 rounded-full text-[10px] font-medium bg-[#f5f5f4] text-[#717971] border border-[#e7e5e4]">
                {possible_associations.length}
              </span>
            </div>
            <span className="text-xs text-[#a8a29e] flex items-center gap-1">
              <HelpCircle className="w-3.5 h-3.5" />
              Cross-type heuristic inference
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {possible_associations.map((assoc, idx) => (
              <div
                key={`${assoc.person_text}-${assoc.org_text}-${assoc.org_filename}-${idx}`}
                className="p-4 rounded-xl border border-dashed border-[#d6d3d1] bg-[#fafaf9]/70 hover:bg-[#fafaf9] transition-colors space-y-2.5"
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="flex items-center gap-1.5 flex-wrap">
                    <span className="text-xs font-mono font-bold text-[#1f1b17]">
                      {assoc.person_text}
                    </span>
                    <span className="text-xs text-[#a8a29e]">→</span>
                    <span className="text-xs font-mono font-semibold text-[#44403c]">
                      {assoc.org_text}
                    </span>
                  </div>
                  <span className="text-[10px] uppercase font-medium px-2 py-0.5 rounded-md bg-[#f5f5f4] text-[#78716c] border border-[#e7e5e4] shrink-0">
                    {assoc.confidence_label} confidence
                  </span>
                </div>

                <p className="text-xs text-[#57534e] leading-relaxed">
                  {assoc.explanation}
                </p>

                <div className="pt-2 border-t border-[#e7e5e4]/60 flex items-center gap-1.5 text-[11px] text-[#717971]">
                  <span className="text-[10px] font-semibold text-[#a8a29e] uppercase">Source File:</span>
                  <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-white border border-[#e7e5e4] font-mono text-[#292524]">
                    <FileText className="w-3 h-3 text-[#a8a29e]" />
                    {assoc.org_filename}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
