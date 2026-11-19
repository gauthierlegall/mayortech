import React from 'react';
import { Handle, Position, NodeProps } from '@xyflow/react';
import { 
  Cpu, 
  ExternalLink, 
  CheckCircle2, 
  Clock, 
  Send, 
  FileCheck2, 
  ShieldCheck,
  RefreshCw
} from 'lucide-react';

export interface ConnectorTaskNodeData {
  title: string;
  connectorName: string; // e.g. "i-Parapheur / Pastell" | "Grist" | "Matrix / Tchap" | "ProConnect"
  connectorType: 'parapheur' | 'grist' | 'matrix' | 'proconnect' | 'exchange';
  sla: string;
  externalStatus: 'ready' | 'transmitted' | 'signed_acknowledged' | 'syncing';
  statusLabel?: string;
  isActive?: boolean;
  isCompleted?: boolean;
  stepNumber: number;
}

export const ConnectorTaskNode: React.FC<NodeProps> = ({ id, data, selected }) => {
  const nodeData = data as unknown as ConnectorTaskNodeData;
  const isActive = nodeData.isActive;
  const isCompleted = nodeData.isCompleted;

  const handleClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    window.dispatchEvent(new CustomEvent('bpmn-node-selected', { detail: { id, isConnector: true } }));
  };

  const statusConfig = {
    ready: { label: 'Prêt pour télétransmission', color: 'text-slate-600 bg-slate-100 border-slate-200' },
    transmitted: { label: 'Transmis en Préfecture (@CTES)', color: 'text-indigo-700 bg-indigo-50 border-indigo-200' },
    signed_acknowledged: { label: 'Signé & Acquitté @CTES', color: 'text-emerald-700 bg-emerald-50 border-emerald-200' },
    syncing: { label: 'Synchronisation en cours', color: 'text-blue-700 bg-blue-50 border-blue-200' }
  }[nodeData.externalStatus || 'ready'];

  return (
    <div
      data-node-id={id}
      data-testid={`bpmn-connector-${id}`}
      onClick={handleClick}
      className={`w-[265px] bg-white rounded-xl border transition-all duration-200 px-3.5 py-3 relative cursor-pointer group shadow-xs ${
        isActive
          ? 'border-indigo-500 ring-2 ring-indigo-500/25 shadow-md bg-indigo-50/15'
          : isCompleted
          ? 'border-emerald-300 bg-emerald-50/10 hover:border-emerald-400'
          : selected
          ? 'border-indigo-400 shadow-md'
          : 'border-indigo-200/80 hover:border-indigo-300 hover:shadow-sm'
      }`}
    >
      {/* Handles: Left */}
      <Handle
        type="target"
        position={Position.Left}
        id="target-left"
        className="!w-2 !h-2 !bg-indigo-500 !border-2 !border-white !-left-1"
      />
      <Handle
        type="source"
        position={Position.Left}
        id="source-left"
        className="!w-2 !h-2 !bg-indigo-500 !border-2 !border-white !-left-1 !opacity-0"
      />

      {/* Handles: Right */}
      <Handle
        type="source"
        position={Position.Right}
        id="source-right"
        className="!w-2 !h-2 !bg-indigo-500 !border-2 !border-white !-right-1"
      />
      <Handle
        type="target"
        position={Position.Right}
        id="target-right"
        className="!w-2 !h-2 !bg-indigo-500 !border-2 !border-white !-right-1 !opacity-0"
      />

      {/* Top row: step number + connector badge */}
      <div className="flex items-center justify-between gap-1 mb-2">
        <div className="flex items-center gap-1.5">
          <span className="inline-flex items-center justify-center w-5 h-5 rounded-full bg-indigo-100 text-indigo-700 text-[10px] font-bold">
            {nodeData.stepNumber || 4}
          </span>
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-indigo-50 text-indigo-700 border border-indigo-200/60">
            <Cpu className="w-2.5 h-2.5" />
            Connecteur externe
          </span>
        </div>
        <span className="text-[10px] text-slate-600 font-medium flex items-center gap-1">
          <Clock className="w-2.5 h-2.5 text-slate-600" />
          {nodeData.sla || '12h'}
        </span>
      </div>

      {/* Title & Service */}
      <div className="mb-2">
        <h4 className="text-xs font-bold text-slate-900 leading-snug line-clamp-1 group-hover:text-indigo-600 transition-colors">
          {nodeData.title || 'Télétransmission @CTES & Signature'}
        </h4>
        <div className="flex items-center gap-1.5 text-[11px] text-slate-600 font-medium mt-0.5">
          <span className="w-1.5 h-1.5 rounded-full bg-indigo-500" />
          <span className="truncate">{nodeData.connectorName || 'i-Parapheur / Pastell'}</span>
          <ExternalLink className="w-2.5 h-2.5 text-slate-600 ml-auto flex-shrink-0" />
        </div>
      </div>

      {/* External status badge */}
      <div className="pt-2 border-t border-slate-100 flex items-center justify-between">
        <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-medium border ${statusConfig.color}`}>
          {isCompleted ? (
            <CheckCircle2 className="w-2.5 h-2.5 text-emerald-600" />
          ) : isActive ? (
            <RefreshCw className="w-2.5 h-2.5 text-indigo-600 animate-spin" />
          ) : (
            <Send className="w-2.5 h-2.5 text-slate-600" />
          )}
          <span className="truncate max-w-[190px]">{nodeData.statusLabel || statusConfig.label}</span>
        </span>
      </div>
    </div>
  );
};
