import React from 'react';
import { Handle, Position, NodeProps } from '@xyflow/react';
import { XCircle, CheckCircle2 } from 'lucide-react';

export interface BpmnEndNodeData {
  label: string;
  type: 'reject' | 'success';
  isActive?: boolean;
}

export const BpmnEndNode: React.FC<NodeProps> = ({ data, selected }) => {
  const nodeData = data as unknown as BpmnEndNodeData;
  const isReject = nodeData.type === 'reject';
  const isActive = nodeData.isActive;

  return (
    <div className="relative flex flex-col items-center justify-center">
      <Handle
        type="target"
        position={Position.Left}
        id="left"
        className="!w-2 !h-2 !bg-slate-300 !border !border-white !rounded-full transition-colors"
      />
      <Handle
        type="target"
        position={Position.Top}
        id="top"
        className="!w-2 !h-2 !bg-slate-300 !border !border-white !rounded-full transition-colors"
      />

      {/* PC-2026 Capsule on Active Terminal Node */}
      {isActive && (
        <div className="absolute -top-7 whitespace-nowrap z-20 animate-fade-in">
          <span
            className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded-full border shadow-xs flex items-center gap-1 ${
              isReject
                ? 'bg-rose-600 text-white border-rose-700 shadow-rose-200'
                : 'bg-emerald-600 text-white border-emerald-700 shadow-emerald-200'
            }`}
          >
            <span className="w-1.5 h-1.5 rounded-full bg-white animate-ping" />
            <span>PC-2026</span>
          </span>
        </div>
      )}

      <div
        className={`w-10 h-10 rounded-full bg-white border-2 flex items-center justify-center transition-all duration-200 cursor-pointer shadow-xs ${
          isReject
            ? isActive
              ? 'border-rose-500 ring-4 ring-rose-400/25 bg-rose-50/50'
              : 'border-rose-300 text-rose-500 hover:border-rose-400'
            : isActive
            ? 'border-emerald-500 ring-4 ring-emerald-400/25 bg-emerald-50/50'
            : 'border-emerald-300 text-emerald-500 hover:border-emerald-400'
        }`}
      >
        {isReject ? (
          <XCircle className="w-5 h-5 text-rose-500" />
        ) : (
          <CheckCircle2 className="w-5 h-5 text-emerald-500" />
        )}
      </div>

      <div className="absolute top-11 whitespace-nowrap text-center">
        <span
          className={`text-[10px] font-semibold px-2 py-0.5 rounded-md border shadow-2xs ${
            isReject
              ? 'bg-rose-50 text-rose-700 border-rose-200'
              : 'bg-emerald-50 text-emerald-700 border-emerald-200'
          }`}
        >
          {nodeData.label}
        </span>
      </div>
    </div>
  );
};
