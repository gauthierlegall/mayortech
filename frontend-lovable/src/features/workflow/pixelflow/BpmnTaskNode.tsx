import React from 'react';
import { Handle, Position, NodeProps } from '@xyflow/react';
import { 
  Building2, 
  FileCheck, 
  HardHat, 
  Landmark, 
  Stamp, 
  ShieldCheck,
  AlertTriangle,
  Clock,
  CheckCircle2,
  ShieldAlert,
  AlertCircle
} from 'lucide-react';

export interface BpmnTaskNodeData {
  title: string;
  actor: string;
  sla: string;
  iconName: 'Building2' | 'FileCheck' | 'HardHat' | 'Landmark' | 'Stamp' | 'ShieldCheck' | 'ShieldAlert';
  iconColor: string;
  bgColor: string;
  isActive?: boolean;
  isCompleted?: boolean;
  isOverdue?: boolean;
  overdueLabel?: string;
  customBadgeText?: string;
  customBadgeColor?: 'amber' | 'emerald' | 'rose' | 'blue';
  subBadge?: string;
  tokenColor?: 'blue' | 'rose' | 'amber';
  status?: 'pending' | 'active' | 'completed' | 'warning' | 'rejected';
  stepNumber: number;
}

const ICON_MAP = {
  Building2,
  FileCheck,
  HardHat,
  Landmark,
  Stamp,
  ShieldCheck,
  ShieldAlert,
};

export const BpmnTaskNode: React.FC<NodeProps> = ({ id, data, selected }) => {
  const nodeData = data as unknown as BpmnTaskNodeData;
  const IconComponent = ICON_MAP[nodeData.iconName] || Building2;
  const isActive = nodeData.isActive;
  const isCompleted = nodeData.isCompleted;
  const isOverdue = nodeData.isOverdue;
  const tokenBg = nodeData.tokenColor === 'rose' ? 'bg-rose-600' : nodeData.tokenColor === 'amber' ? 'bg-amber-600' : 'bg-blue-600';

  const handleClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    window.dispatchEvent(new CustomEvent('bpmn-node-selected', { detail: { id } }));
  };

  return (
    <div
      data-node-id={id}
      data-testid={`bpmn-task-${id}`}
      onClick={handleClick}
      className={`w-[280px] bg-white rounded-xl border transition-all duration-200 px-3.5 py-3 relative cursor-pointer group shadow-xs ${
        isOverdue
          ? 'border-rose-400 ring-2 ring-rose-400/25 bg-rose-50/15 shadow-md'
          : isActive
          ? 'border-blue-500 ring-2 ring-blue-500/25 shadow-md bg-blue-50/15'
          : isCompleted
          ? nodeData.customBadgeColor === 'amber'
            ? 'border-amber-300 bg-amber-50/10 hover:border-amber-400'
            : 'border-emerald-300 bg-emerald-50/10 hover:border-emerald-400'
          : selected
          ? 'border-blue-400 shadow-md'
          : 'border-slate-200 hover:border-slate-300 hover:shadow-sm'
      }`}
    >
      {/* Handles: Left (Target & Source) */}
      <Handle
        type="target"
        position={Position.Left}
        id="left"
        className="!w-2 !h-2 !bg-slate-300 hover:!bg-blue-500 !border !border-white !rounded-full transition-colors"
      />
      <Handle
        type="source"
        position={Position.Left}
        id="left"
        className="!w-2 !h-2 !bg-slate-300 hover:!bg-rose-500 !border !border-white !rounded-full transition-colors"
      />

      {/* Handles: Top (Target & Source) */}
      <Handle
        type="target"
        position={Position.Top}
        id="top"
        className="!w-2 !h-2 !bg-slate-300 hover:!bg-amber-500 !border !border-white !rounded-full transition-colors"
      />
      <Handle
        type="source"
        position={Position.Top}
        id="top"
        className="!w-2 !h-2 !bg-slate-300 hover:!bg-blue-500 !border !border-white !rounded-full transition-colors"
      />

      {/* Handles: Right (Source & Target) */}
      <Handle
        type="source"
        position={Position.Right}
        id="right"
        className="!w-2 !h-2 !bg-slate-300 hover:!bg-blue-500 !border !border-white !rounded-full transition-colors"
      />
      <Handle
        type="target"
        position={Position.Right}
        id="right"
        className="!w-2 !h-2 !bg-slate-300 hover:!bg-blue-500 !border !border-white !rounded-full transition-colors"
      />

      {/* Handles: Bottom (Source & Target) */}
      <Handle
        type="source"
        position={Position.Bottom}
        id="bottom"
        className="!w-2 !h-2 !bg-slate-300 hover:!bg-rose-500 !border !border-white !rounded-full transition-colors"
      />
      <Handle
        type="target"
        position={Position.Bottom}
        id="bottom"
        className="!w-2 !h-2 !bg-slate-300 hover:!bg-blue-500 !border !border-white !rounded-full transition-colors"
      />

      {/* Active Dossier Token Pill */}
      {isActive && (
        <div className={`absolute -top-2.5 right-3 ${tokenBg} text-white font-mono text-[10px] font-bold px-2 py-0.5 rounded-full shadow-sm flex items-center gap-1 z-10 animate-fade-in`}>
          <span className="w-1.5 h-1.5 rounded-full bg-white animate-ping" />
          <span>PC-2026</span>
        </div>
      )}

      {/* Line 1: Colored icon badge + Short title (2 lines clear without truncate) */}
      <div className="flex items-center gap-2.5">
        <div
          className="w-8 h-8 rounded-lg flex items-center justify-center shrink-0 border"
          style={{
            backgroundColor: nodeData.bgColor || '#eff6ff',
            borderColor: `${nodeData.iconColor}33`,
            color: nodeData.iconColor || '#2563eb',
          }}
        >
          <IconComponent className="w-4 h-4" />
        </div>
        <div className="min-w-0 flex-1 min-h-[38px] flex items-center">
          <h3 className="text-sm font-semibold text-slate-900 leading-snug line-clamp-2">
            {nodeData.title}
          </h3>
        </div>
      </div>

      {/* Line 2: Subtle Actor + 1 Single SLA Badge or Validated Check */}
      <div className="mt-2.5 pt-2 border-t border-slate-100 flex items-center justify-between gap-1.5 text-xs">
        <span className="text-slate-500 text-[10.5px] truncate flex-1 font-medium" title={nodeData.actor}>
          {nodeData.actor}
        </span>

        {nodeData.customBadgeText ? (
          <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded shrink-0 flex items-center gap-1 border ${
            nodeData.customBadgeColor === 'rose'
              ? 'bg-rose-50 text-rose-800 border-rose-300'
              : nodeData.customBadgeColor === 'amber'
              ? 'bg-amber-50 text-amber-800 border-amber-300'
              : 'bg-emerald-50 text-emerald-700 border-emerald-200'
          }`}>
            <AlertCircle className={`w-2.5 h-2.5 ${nodeData.customBadgeColor === 'rose' ? 'text-rose-600' : 'text-amber-600'}`} />
            <span>{nodeData.customBadgeText}</span>
          </span>
        ) : isOverdue ? (
          <span className="bg-rose-50 text-rose-700 border border-rose-300 text-[10px] font-mono px-1.5 py-0.5 rounded font-bold shrink-0 flex items-center gap-1 ">
            <AlertTriangle className="w-2.5 h-2.5 text-rose-600" />
            <span>{nodeData.overdueLabel || 'DÉPASSÉ'}</span>
          </span>
        ) : isCompleted ? (
          <span className="bg-emerald-50 text-emerald-700 border border-emerald-200 text-[10px] font-medium px-1.5 py-0.5 rounded shrink-0 flex items-center gap-1">
            <CheckCircle2 className="w-3 h-3 text-emerald-600" />
            <span>Validé</span>
          </span>
        ) : (
          <span className="bg-emerald-50 text-emerald-700 border border-emerald-200 text-[10px] font-mono px-1.5 py-0.5 rounded font-medium shrink-0 flex items-center gap-1">
            <Clock className="w-2.5 h-2.5 text-emerald-600" />
            <span>{nodeData.sla}</span>
          </span>
        )}
      </div>

      {/* Sub-badge indicator (e.g. Délai suspendu · 3 mois usager) */}
      {nodeData.subBadge && (
        <div className="mt-1 pt-1 border-t border-dashed border-amber-200/80 flex items-center justify-center">
          <span className="text-[9.5px] font-medium text-amber-700 bg-amber-50 px-2 py-0.5 rounded-full border border-amber-200/60 flex items-center gap-1">
            <Clock className="w-2.5 h-2.5 text-amber-600" />
            <span>{nodeData.subBadge}</span>
          </span>
        </div>
      )}
    </div>
  );
};
