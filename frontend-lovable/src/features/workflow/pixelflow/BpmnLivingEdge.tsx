import React from 'react';
import {
  BaseEdge,
  EdgeLabelRenderer,
  EdgeProps,
  getSmoothStepPath,
  getBezierPath,
} from '@xyflow/react';

export interface BpmnLivingEdgeData {
  label?: string;
  isActive?: boolean;
  isCompleted?: boolean;
  color?: 'emerald' | 'amber' | 'rose' | 'blue';
  curveType?: 'smoothstep' | 'bezier';
  corridorX?: number;
  corridorY?: number;
  customLabelPos?: { x: number; y: number };
}

const COLOR_MAP = {
  emerald: {
    stroke: '#10b981',
    bg: 'bg-emerald-50',
    text: 'text-emerald-700',
    border: 'border-emerald-200',
  },
  amber: {
    stroke: '#f59e0b',
    bg: 'bg-amber-50',
    text: 'text-amber-700',
    border: 'border-amber-200',
  },
  rose: {
    stroke: '#f43f5e',
    bg: 'bg-rose-50',
    text: 'text-rose-700',
    border: 'border-rose-200',
  },
  blue: {
    stroke: '#3b82f6',
    bg: 'bg-blue-50',
    text: 'text-blue-700',
    border: 'border-blue-200',
  },
};

export const BpmnLivingEdge: React.FC<EdgeProps> = ({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  style = {},
  markerEnd,
  data,
}) => {
  const edgeData = (data || {}) as BpmnLivingEdgeData;
  const isActive = edgeData.isActive;
  const isCompleted = edgeData.isCompleted;
  const colorKey = edgeData.color || 'blue';
  const colorMeta = COLOR_MAP[colorKey] || COLOR_MAP.blue;
  const curveType = edgeData.curveType || 'smoothstep';

  let edgePath = '';
  let labelX = (sourceX + targetX) / 2;
  let labelY = (sourceY + targetY) / 2;

  if (edgeData.corridorX && edgeData.corridorY) {
    const cX = edgeData.corridorX;
    const cY = edgeData.corridorY;
    const r = 14;
    const signY1 = cY > sourceY ? 1 : -1;
    const signX1 = cX > sourceX ? 1 : -1;
    const signY2 = targetY > cY ? 1 : -1;
    const signX2 = targetX > cX ? 1 : -1;

    edgePath = `M ${sourceX} ${sourceY} L ${sourceX} ${cY - signY1 * r} Q ${sourceX} ${cY} ${sourceX + signX1 * r} ${cY} L ${cX - signX1 * r} ${cY} Q ${cX} ${cY} ${cX} ${cY + signY2 * r} L ${cX} ${targetY - signY2 * r} Q ${cX} ${targetY} ${cX + signX2 * r} ${targetY} L ${targetX} ${targetY}`;
    labelX = cX;
    labelY = (cY + targetY) / 2;
  } else if (edgeData.corridorX) {
    const cX = edgeData.corridorX;
    const r = 14;
    const signX1 = cX > sourceX ? 1 : -1;
    const signY = targetY > sourceY ? 1 : -1;
    const signX2 = targetX > cX ? 1 : -1;

    edgePath = `M ${sourceX} ${sourceY} L ${cX - signX1 * r} ${sourceY} Q ${cX} ${sourceY} ${cX} ${sourceY + signY * r} L ${cX} ${targetY - signY * r} Q ${cX} ${targetY} ${cX + signX2 * r} ${targetY} L ${targetX} ${targetY}`;
    labelX = cX;
    labelY = (sourceY + targetY) / 2;
  } else if (curveType === 'bezier') {
    const [path, lx, ly] = getBezierPath({
      sourceX,
      sourceY,
      sourcePosition,
      targetX,
      targetY,
      targetPosition,
    });
    edgePath = path;
    labelX = lx;
    labelY = ly;
  } else {
    const [path, lx, ly] = getSmoothStepPath({
      sourceX,
      sourceY,
      sourcePosition,
      targetX,
      targetY,
      targetPosition,
      borderRadius: 16,
    });
    edgePath = path;
    labelX = lx;
    labelY = ly;
  }

  if (edgeData.customLabelPos) {
    labelX = edgeData.customLabelPos.x;
    labelY = edgeData.customLabelPos.y;
  }

  const strokeColor = isActive ? colorMeta.stroke : isCompleted ? '#10b981' : '#CBD5E1';
  const strokeWidth = isActive ? 2.5 : isCompleted ? 2 : 1.75;

  return (
    <>
      {/* Background/Base Edge */}
      <BaseEdge
        id={id}
        path={edgePath}
        markerEnd={markerEnd}
        style={{
          ...style,
          stroke: strokeColor,
          strokeWidth,
          strokeDasharray: isActive ? '6 4' : undefined,
          animation: isActive ? 'flowDash 1.2s linear infinite' : undefined,
          transition: 'stroke 0.3s ease, stroke-width 0.3s ease',
        }}
      />

      {/* Travelling Light Bead along the SVG path */}
      {isActive && (
        <circle r="4" fill="#ffffff" stroke={colorMeta.stroke} strokeWidth="2.5">
          <animateMotion
            dur="1.4s"
            repeatCount="indefinite"
            path={edgePath}
            rotate="auto"
          />
        </circle>
      )}

      {/* Pastille on Edge via EdgeLabelRenderer */}
      {edgeData.label && (
        <EdgeLabelRenderer>
          <div
            style={{
              position: 'absolute',
              transform: `translate(-50%, -50%) translate(${labelX}px,${labelY}px)`,
              pointerEvents: 'all',
            }}
            className="nodrag nopan"
          >
            <span
              className={`px-2.5 py-0.5 rounded-full text-[10px] font-semibold border shadow-2xs transition-colors duration-200 whitespace-nowrap ${
                isActive
                  ? `${colorMeta.bg} ${colorMeta.text} ${colorMeta.border} ring-2 ring-white shadow-xs`
                  : isCompleted
                  ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                  : 'bg-white text-slate-600 border-slate-200 hover:text-slate-800'
              }`}
            >
              {edgeData.label}
            </span>
          </div>
        </EdgeLabelRenderer>
      )}
    </>
  );
};
