import React from 'react';
import { ShieldCheck, HelpCircle, Settings, CheckCircle2 } from 'lucide-react';
import { TabType } from '../types';

interface HeaderProps {
  currentTab: TabType;
  onSelectTab: (tab: TabType) => void;
  flaggedCount: number;
}

export const Header: React.FC<HeaderProps> = ({ currentTab, onSelectTab, flaggedCount }) => {
  const steps = [
    { id: 'upload' as TabType, num: 1, label: 'Upload & Setup', shortLabel: 'Upload' },
    { id: 'pipeline' as TabType, num: 2, label: 'Pipeline Inspection', shortLabel: 'Processing' },
    { id: 'audit' as TabType, num: 3, label: 'Audit & Verification', shortLabel: 'Audit', badge: flaggedCount > 0 ? flaggedCount : undefined },
  ];

  return (
    <header className="sticky top-0 z-40 bg-[#fafaf9]/90 backdrop-blur-md border-b border-[#e7e5e4] px-4 sm:px-8 py-3.5">
      <div className="max-w-7xl mx-auto flex items-center justify-between">
        {/* Brand */}
        <div className="flex items-center gap-3">
          <button 
            onClick={() => onSelectTab('upload')}
            className="flex items-center gap-2.5 group text-left cursor-pointer focus:outline-none"
            title="ScanX Home"
          >
            <div className="w-8 h-8 rounded-lg bg-[#316342] flex items-center justify-center text-white shadow-sm transition-transform duration-200 group-hover:scale-105">
              <ShieldCheck className="w-5 h-5 stroke-[2.2]" />
            </div>
            <div className="flex flex-col">
              <span className="font-semibold text-lg tracking-tight text-[#292524] leading-tight flex items-center gap-1.5">
                ScanX
              </span>
            </div>
          </button>
        </div>

        {/* Center Step Navigation */}
        <nav className="hidden md:flex items-center gap-1 sm:gap-2">
          {steps.map((step) => {
            const isActive = currentTab === step.id;
            return (
              <button
                key={step.id}
                id={`nav-step-${step.id}`}
                onClick={() => onSelectTab(step.id)}
                className={`relative px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200 flex items-center gap-2.5 cursor-pointer ${
                  isActive
                    ? 'text-[#166534] bg-[#e8f5e9]/70 font-semibold'
                    : 'text-[#57534e] hover:text-[#292524] hover:bg-[#f5f5f4]'
                }`}
              >
                <span
                  className={`w-5 h-5 rounded-full text-xs flex items-center justify-center transition-colors ${
                    isActive
                      ? 'bg-[#316342] text-white font-bold'
                      : 'bg-[#e7e5e4] text-[#57534e]'
                  }`}
                >
                  {step.num}
                </span>
                <span>{step.label}</span>
                {step.badge !== undefined && (
                  <span className="ml-1 px-1.5 py-0.5 text-[11px] font-semibold bg-amber-100 text-amber-800 rounded-full border border-amber-300">
                    {step.badge}
                  </span>
                )}
                {isActive && (
                  <div className="absolute bottom-0 left-3 right-3 h-[2px] bg-[#316342] rounded-full" />
                )}
              </button>
            );
          })}
        </nav>

        {/* Mobile Step Select */}
        <div className="flex md:hidden items-center gap-1 text-sm bg-white px-2 py-1 rounded-lg border border-[#e7e5e4]">
          {steps.map((s) => (
            <button
              key={s.id}
              onClick={() => onSelectTab(s.id)}
              className={`px-2.5 py-1 rounded text-xs font-medium transition-colors ${
                currentTab === s.id
                  ? 'bg-[#316342] text-white'
                  : 'text-[#57534e] hover:text-[#292524]'
              }`}
            >
              {s.shortLabel}
            </button>
          ))}
        </div>

        {/* Right User & System Controls */}
        <div className="flex items-center gap-3">
          <div className="hidden lg:flex items-center gap-1.5 px-2.5 py-1 bg-white rounded-full border border-[#e7e5e4] text-xs text-[#57534e]">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
            <span className="font-medium text-[#292524]">Engine Cluster</span>
            <span className="text-[#a8a29e]">• Online</span>
          </div>

          <button
            onClick={() => onSelectTab('pipeline')}
            title="Scan engine documentation"
            className="p-2 text-[#57534e] hover:text-[#292524] hover:bg-[#f5f5f4] rounded-lg transition-colors"
          >
            <HelpCircle className="w-4 h-4" />
          </button>

          <button
            onClick={() => onSelectTab('upload')}
            title="Pipeline settings"
            className="p-2 text-[#57534e] hover:text-[#292524] hover:bg-[#f5f5f4] rounded-lg transition-colors"
          >
            <Settings className="w-4 h-4" />
          </button>

          {/* User profile button */}
          <div className="flex items-center gap-2 pl-2 border-l border-[#e7e5e4]">
            <div 
              className="w-8 h-8 rounded-full bg-[#f0e6e0] border border-[#d6d3d1] flex items-center justify-center text-xs font-semibold text-[#342f2b] shadow-xs cursor-pointer hover:ring-2 hover:ring-[#4a7c59]/40 transition-all"
              title="Alex Drake (Compliance Officer)"
            >
              AD
            </div>
          </div>
        </div>
      </div>
    </header>
  );
};
