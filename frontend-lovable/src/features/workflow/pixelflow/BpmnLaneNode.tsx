import React from 'react';
import { NodeProps } from '@xyflow/react';

export interface BpmnLaneNodeData {
  title: string;
  dotColor: string;
  width: number;
  height: number;
}

export const BpmnLaneNode: React.FC<NodeProps> = ({ data }) => {
  const nodeData = data as unknown as BpmnLaneNodeData;

  return (
    <div
      style={{
        width: nodeData.width || 1540,
        height: nodeData.height || 195,
      }}
      className="bg-white/70 border border-slate-200/90 rounded-2xl p-4 flex flex-col justify-between pointer-events-none shadow-2xs select-none"
    >
      <div className="flex items-center gap-2">
        <span
          className="w-2.5 h-2.5 rounded-full shrink-0"
          style={{ backgroundColor: nodeData.dotColor || '#3b82f6' }}
        />
        <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500 font-sans">
          {nodeData.title}
        </span>
      </div>
    </div>
  );
};
