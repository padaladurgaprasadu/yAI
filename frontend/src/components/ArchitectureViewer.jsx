import React, { useCallback, useMemo, useEffect, useState } from 'react';
import ReactFlow, { Background, Controls, MiniMap, useNodesState, useEdgesState, MarkerType } from 'reactflow';
import dagre from 'dagre';
import 'reactflow/dist/style.css';
import { Database, Server, Globe, ExternalLink, Mail, Zap, User, Code, Box, Maximize, Minimize } from 'lucide-react';

// Dagre Layout Engine
const dagreGraph = new dagre.graphlib.Graph();
dagreGraph.setDefaultEdgeLabel(() => ({}));

const nodeWidth = 220;
const nodeHeight = 80;

const getLayoutedElements = (nodes, edges, direction = 'LR') => {
  const isHorizontal = direction === 'LR';
  dagreGraph.setGraph({ rankdir: direction, nodesep: 60, ranksep: 120 });

  nodes.forEach((node) => {
    dagreGraph.setNode(node.id, { width: nodeWidth, height: nodeHeight });
  });

  edges.forEach((edge) => {
    dagreGraph.setEdge(edge.source, edge.target);
  });

  dagre.layout(dagreGraph);

  nodes.forEach((node) => {
    const nodeWithPosition = dagreGraph.node(node.id);
    node.targetPosition = isHorizontal ? 'left' : 'top';
    node.sourcePosition = isHorizontal ? 'right' : 'bottom';
    
    // Adjust position to be centered
    node.position = {
      x: nodeWithPosition.x - nodeWidth / 2,
      y: nodeWithPosition.y - nodeHeight / 2,
    };

    return node;
  });

  return { nodes, edges };
};

// Custom Node Styling based on Type
const getIconForType = (type) => {
  switch (type) {
    case 'database': return <Database size={20} />;
    case 'microservice': return <Box size={20} />;
    case 'gateway': return <Globe size={20} />;
    case 'external': return <ExternalLink size={20} />;
    case 'queue': return <Mail size={20} />;
    case 'ai': return <Zap size={20} />;
    case 'user': return <User size={20} />;
    default: return <Server size={20} />;
  }
};

const getColorForType = (type) => {
  switch (type) {
    case 'database': return { bg: '#991b1b', border: '#ef4444' };
    case 'microservice': return { bg: '#065f46', border: '#10b981' };
    case 'gateway': return { bg: '#4c1d95', border: '#8b5cf6' };
    case 'external': return { bg: '#1e3a8a', border: '#3b82f6' };
    case 'queue': return { bg: '#92400e', border: '#f59e0b' };
    case 'ai': return { bg: '#be185d', border: '#ec4899' };
    default: return { bg: '#1f2937', border: '#374151' };
  }
};

const CustomNode = ({ data }) => {
  const colors = getColorForType(data.type);
  return (
    <div style={{
      padding: '12px',
      borderRadius: '8px',
      background: colors.bg,
      border: `2px solid ${colors.border}`,
      color: '#fff',
      display: 'flex',
      alignItems: 'center',
      gap: '12px',
      width: '200px',
      boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.5), 0 2px 4px -1px rgba(0, 0, 0, 0.3)'
    }}>
      <div style={{ padding: '6px', background: 'rgba(0,0,0,0.3)', borderRadius: '6px', display: 'flex' }}>
        {getIconForType(data.type)}
      </div>
      <div>
        <div style={{ fontWeight: 'bold', fontSize: '14px', lineHeight: '1.2' }}>{data.label}</div>
        <div style={{ fontSize: '10px', opacity: 0.8, textTransform: 'uppercase', marginTop: '2px', letterSpacing: '0.5px' }}>
          {data.type}
        </div>
      </div>
    </div>
  );
};

const nodeTypes = {
  custom: CustomNode,
};

export default function ArchitectureViewer({ architectureJson }) {
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [isFullscreen, setIsFullscreen] = useState(false);

  useEffect(() => {
    try {
      const data = typeof architectureJson === 'string' ? JSON.parse(architectureJson) : architectureJson;
      
      const rfNodes = data.nodes.map(n => ({
        id: n.id,
        type: 'custom',
        data: { label: n.label, type: n.type, zone: n.zone },
        position: { x: 0, y: 0 }
      }));

      const rfEdges = data.edges.map((e, idx) => {
        let color = '#a1a1aa';
        let animated = false;
        if (e.type === 'sync') color = '#3b82f6';
        if (e.type === 'async') { color = '#10b981'; animated = true; }
        if (e.type === 'data') color = '#f59e0b';
        
        return {
          id: `e-${idx}`,
          source: e.source,
          target: e.target,
          label: e.label,
          animated,
          style: { stroke: color, strokeWidth: 2 },
          labelStyle: { fill: '#fff', fontWeight: 700 },
          labelBgStyle: { fill: '#18181b' },
          markerEnd: {
            type: MarkerType.ArrowClosed,
            color,
          },
        };
      });

      const { nodes: layoutedNodes, edges: layoutedEdges } = getLayoutedElements(rfNodes, rfEdges);
      
      setNodes(layoutedNodes);
      setEdges(layoutedEdges);
    } catch (err) {
      console.error("Failed to parse architecture JSON", err);
    }
  }, [architectureJson]);

  return (
    <div style={{ 
      ...(isFullscreen ? {
        position: 'fixed',
        top: 0,
        left: 0,
        width: '100vw',
        height: '100vh',
        zIndex: 99999,
        background: '#0a0a0a',
        padding: '20px'
      } : {
        width: '100%', 
        height: '500px', 
        minWidth: '300px',
        background: '#0a0a0a', 
        borderRadius: '12px', 
        border: '1px solid #27272a', 
        overflow: 'hidden', 
        marginTop: '16px', 
        marginBottom: '16px',
        position: 'relative'
      })
    }}>
      <button 
        onClick={() => setIsFullscreen(!isFullscreen)}
        style={{
          position: 'absolute',
          top: '16px',
          right: '16px',
          zIndex: 10,
          background: 'rgba(24, 24, 27, 0.8)',
          border: '1px solid #3f3f46',
          color: 'white',
          padding: '8px 12px',
          borderRadius: '8px',
          cursor: 'pointer',
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          backdropFilter: 'blur(4px)',
          boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)'
        }}
      >
        {isFullscreen ? <Minimize size={16} /> : <Maximize size={16} />}
        {isFullscreen ? 'Exit Fullscreen' : 'Expand to Fullscreen'}
      </button>

      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        nodeTypes={nodeTypes}
        fitView
        attributionPosition="bottom-right"
      >
        <Background color="#27272a" gap={16} />
        <Controls style={{ background: '#18181b', color: '#fff', fill: '#fff' }} />
      </ReactFlow>
    </div>
  );
}
