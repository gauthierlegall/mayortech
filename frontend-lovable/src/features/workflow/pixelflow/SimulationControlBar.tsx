import React, { useState } from 'react';
import { Play, Pause, RotateCcw, FastForward, CheckCircle2, AlertTriangle, XCircle, Clock, ShieldAlert } from 'lucide-react';

export type SimulationScenario = 'nominal' | 'missing_docs' | 'rejection' | 'sla_timeout';

interface SimulationControlBarProps {
  isPlaying: boolean;
  onTogglePlay: () => void;
  onReset: () => void;
  onStep: () => void;
  speed: number;
  onSpeedChange: (speed: number) => void;
  currentScenario: SimulationScenario;
  onScenarioChange: (scenario: SimulationScenario) => void;
  activeStepName: string;
}

export function SimulationControlBar({
  isPlaying,
  onTogglePlay,
  onReset,
  onStep,
  speed,
  onSpeedChange,
  currentScenario,
  onScenarioChange,
  activeStepName,
}: SimulationControlBarProps) {
  const scenarios: { id: SimulationScenario; label: string; icon: React.ReactNode; color: string }[] = [
    {
      id: 'nominal',
      label: 'Voie Royale (Nominal)',
      icon: <CheckCircle2 size={14} className="text-emerald-400" />,
      color: 'border-emerald-500/40 hover:bg-emerald-950/30 text-emerald-300',
    },
    {
      id: 'missing_docs',
      label: 'Pièces Manquantes',
      icon: <AlertTriangle size={14} className="text-amber-400" />,
      color: 'border-amber-500/40 hover:bg-amber-950/30 text-amber-300',
    },
    {
      id: 'rejection',
      label: 'Rejet PLU / Non-conforme',
      icon: <XCircle size={14} className="text-rose-400" />,
      color: 'border-rose-500/40 hover:bg-rose-950/30 text-rose-300',
    },
    {
      id: 'sla_timeout',
      label: 'Escalade SLA DGS',
      icon: <ShieldAlert size={14} className="text-cyan-400" />,
      color: 'border-cyan-500/40 hover:bg-cyan-950/30 text-cyan-300',
    },
  ];

  return (
    <div className="bg-slate-950/90 border border-slate-800 rounded-xl p-3 shadow-2xl backdrop-blur-md flex flex-wrap items-center justify-between gap-4 font-mono text-xs">
      {/* Transport Controls */}
      <div className="flex items-center gap-2">
        <button
          onClick={onTogglePlay}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg font-semibold transition active:scale-95 shadow-md ${
            isPlaying
              ? 'bg-amber-500 hover:bg-amber-400 text-slate-950'
              : 'bg-emerald-500 hover:bg-emerald-400 text-slate-950'
          }`}
          title={isPlaying ? 'Pause' : 'Play'}
        >
          {isPlaying ? <Pause size={15} /> : <Play size={15} />}
          <span>{isPlaying ? 'PAUSE' : 'LANCER'}</span>
        </button>

        <button
          onClick={onStep}
          disabled={isPlaying}
          className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg border border-slate-700 bg-slate-900 text-slate-300 hover:bg-slate-800 disabled:opacity-40 disabled:cursor-not-allowed transition"
          title="Avancer d'un pas"
        >
          <FastForward size={14} />
          <span>PAS À PAS</span>
        </button>

        <button
          onClick={onReset}
          className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg border border-slate-700 bg-slate-900 text-slate-300 hover:bg-slate-800 transition"
          title="Réinitialiser la simulation"
        >
          <RotateCcw size={14} />
          <span>RESET</span>
        </button>

        {/* Speed Toggles */}
        <div className="flex items-center ml-2 bg-slate-900 border border-slate-800 rounded-lg p-0.5">
          {[0.5, 1, 2, 4].map((s) => (
            <button
              key={s}
              onClick={() => onSpeedChange(s)}
              className={`px-2 py-0.5 rounded text-[11px] font-bold transition ${
                speed === s
                  ? 'bg-cyan-500 text-slate-950 shadow-sm'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              {s}x
            </button>
          ))}
        </div>
      </div>

      {/* Scenario Selector Chips */}
      <div className="flex items-center gap-1.5 overflow-x-auto py-1">
        <span className="text-slate-500 text-[10px] uppercase font-bold tracking-wider mr-1">
          Scénario :
        </span>
        {scenarios.map((sc) => {
          const isSelected = currentScenario === sc.id;
          return (
            <button
              key={sc.id}
              onClick={() => onScenarioChange(sc.id)}
              className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg border transition text-[11px] ${
                isSelected
                  ? `bg-slate-900 shadow-sm font-bold ring-1 ring-offset-1 ring-offset-slate-950 ${sc.color}`
                  : 'border-slate-800 bg-slate-950/60 text-slate-400 hover:text-slate-200 hover:border-slate-700'
              }`}
            >
              {sc.icon}
              <span>{sc.label}</span>
            </button>
          );
        })}
      </div>

      {/* Telemetry pill & Retro FPS */}
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-1.5 px-2 py-1 bg-slate-900 border border-emerald-500/30 rounded-lg text-emerald-400 text-[11px]">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
          <span className="font-bold">60 FPS</span>
        </div>
        <div className="flex items-center gap-2 bg-slate-900/80 border border-slate-800 px-3 py-1 rounded-lg text-slate-300 text-[11px]">
          <span className="inline-block w-2 h-2 rounded-full bg-cyan-400 animate-pulse" />
          <span className="text-slate-500">Nœud Actuel :</span>
          <span className="text-cyan-300 font-semibold truncate max-w-[200px]">{activeStepName}</span>
        </div>
      </div>
    </div>
  );
}
