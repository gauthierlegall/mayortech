import React from 'react';
import { Handle, Position, NodeProps } from '@xyflow/react';
import { GitFork, Plus } from 'lucide-react';

export interface BpmnGatewayNodeData {
  label: string;
  isActive?: boolean;
  gatewayType?: 'exclusive' | 'parallel';
}

export const BpmnGatewayNode: React.FC<NodeProps> = ({ data, selected }) => {
  const nodeData = data as unknown as BpmnGatewayNodeData;
  const isActive = nodeData.isActive;
  const isParallel = nodeData.gatewayType === 'parallel';

  return (
    <div className="relative flex flex-col items-center justify-center">
      {/* Target Handles */}
      <Handle
        type="target"
        position={Position.Left}
        id="left"
        className="!w-2 !h-2 !bg-slate-300 hover:!bg-amber-500 !border !border-white !rounded-full -ml-1 transition-colors"
      />
      <Handle
        type="target"
        position={Position.Top}
        id="top-target"
        className="!w-2 !h-2 !bg-slate-300 hover:!bg-amber-500 !border !border-white !rounded-full -mt-1 transition-colors"
      />
      <Handle
        type="target"
        position={Position.Bottom}
        id="bottom-target"
        className="!w-2 !h-2 !bg-slate-300 hover:!bg-amber-500 !border !border-white !rounded-full -mb-1 transition-colors"
      />

      {/* 44x44px Diamond */}
      <div
        className={`w-[44px] h-[44px] bg-white border-2 rounded-lg rotate-45 flex items-center justify-center transition-all duration-200 cursor-pointer shadow-xs ${
          isParallel
            ? isActive
              ? 'border-emerald-600 ring-4 ring-emerald-400/25 shadow-md scale-105'
              : selected
              ? 'border-emerald-500 shadow-md'
              : 'border-emerald-500 hover:border-emerald-600 hover:scale-105'
            : isActive
            ? 'border-amber-500 ring-4 ring-amber-400/25 shadow-md scale-105'
            : selected
            ? 'border-amber-500 shadow-md'
            : 'border-amber-400 hover:border-amber-500 hover:scale-105'
        }`}
      >
        {isParallel ? (
          <Plus className="-rotate-45 w-5 h-5 text-emerald-600 stroke-[3]" />
        ) : (
          <GitFork className="-rotate-45 w-5 h-5 text-amber-600" />
        )}
      </div>

      {/* Source Handles */}
      <Handle
        type="source"
        position={Position.Right}
        id="right"
        className={`!w-2 !h-2 !bg-slate-300 !border !border-white !rounded-full -mr-1 transition-colors ${
          isParallel ? 'hover:!bg-emerald-500' : 'hover:!bg-emerald-500'
        }`}
      />
      <Handle
        type="source"
        position={Position.Bottom}
        id="bottom"
        className="!w-2 !h-2 !bg-slate-300 hover:!bg-rose-500 !border !border-white !rounded-full -mb-1 transition-colors"
      />
      <Handle
        type="source"
        position={Position.Top}
        id="top"
        className="!w-2 !h-2 !bg-slate-300 hover:!bg-amber-500 !border !border-white !rounded-full -mt-1 transition-colors"
      />

      {/* Label Underneath */}
      <div className="absolute top-12 whitespace-nowrap text-center">
        <span
          className={`text-[11px] font-semibold px-2 py-0.5 rounded-md shadow-2xs border ${
            isParallel
              ? 'bg-emerald-50/90 text-emerald-800 border-emerald-200'
              : 'bg-white/95 text-slate-700 border-slate-200'
          }`}
        >
          {nodeData.label}
        </span>
      </div>
    </div>
  );
};
