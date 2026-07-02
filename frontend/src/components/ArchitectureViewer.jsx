import React, { useCallback, useMemo, useEffect, useState } from 'react';
import ReactFlow, { Background, Controls, MiniMap, useNodesState, useEdgesState, MarkerType, Handle, Position } from 'reactflow';
import dagre from 'dagre';
import 'reactflow/dist/style.css';
import { Database, Server, Globe, ExternalLink, Mail, Zap, User, Code, Box, Maximize, Minimize } from 'lucide-react';

const getLayoutedElements = (nodes, edges, zones = [], direction = 'LR') => {
  const dagreGraph = new dagre.graphlib.Graph({ compound: true });
  dagreGraph.setGraph({ rankdir: direction, nodesep: 80, ranksep: 250, edgesep: 100, ranker: 'network-simplex' });
  dagreGraph.setDefaultEdgeLabel(() => ({}));

  const isHorizontal = direction === 'LR';

  zones.forEach(zone => {
    dagreGraph.setNode(zone.id, { label: zone.label });
  });

  nodes.forEach((node) => {
    dagreGraph.setNode(node.id, { width: 280, height: 160 });
    if (node.data.zone && zones.find(z => z.id === node.data.zone)) {
      dagreGraph.setParent(node.id, node.data.zone);
    }
  });

  edges.forEach((edge) => {
    dagreGraph.setEdge(edge.source, edge.target);
  });

  dagre.layout(dagreGraph);

  const layoutedNodes = [];

  zones.forEach(zone => {
    const zNode = dagreGraph.node(zone.id);
    if (zNode && zNode.width) {
      layoutedNodes.push({
        id: zone.id,
        type: 'zone',
        data: { label: zone.label },
        position: { x: zNode.x - zNode.width / 2 - 40, y: zNode.y - zNode.height / 2 - 60 },
        style: { width: zNode.width + 80, height: zNode.height + 100, zIndex: -1 },
        draggable: false,
        selectable: false
      });
    }
  });

  nodes.forEach((node) => {
    const n = dagreGraph.node(node.id);
    layoutedNodes.push({
      ...node,
      targetPosition: isHorizontal ? 'left' : 'top',
      sourcePosition: isHorizontal ? 'right' : 'bottom',
      position: { x: n.x - 130, y: n.y - 70 }, // Centered for 260x140
      style: { zIndex: 10 }
    });
  });

  return { nodes: layoutedNodes, edges };
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
    case 'database': return { accent: '#f43f5e', glow: 'rgba(244, 63, 94, 0.5)' };
    case 'microservice': return { accent: '#10b981', glow: 'rgba(16, 185, 129, 0.5)' };
    case 'gateway': return { accent: '#8b5cf6', glow: 'rgba(139, 92, 246, 0.5)' };
    case 'external': return { accent: '#3b82f6', glow: 'rgba(59, 130, 246, 0.5)' };
    case 'queue': return { accent: '#f59e0b', glow: 'rgba(245, 158, 11, 0.5)' };
    case 'ai': return { accent: '#ec4899', glow: 'rgba(236, 72, 153, 0.5)' };
    default: return { accent: '#6b7280', glow: 'rgba(107, 114, 128, 0.5)' };
  }
};

const ZoneNode = ({ data }) => {
  return (
    <div style={{
      width: '100%',
      height: '100%',
      backgroundColor: 'rgba(255, 255, 255, 0.02)',
      border: '2px dashed rgba(255, 255, 255, 0.2)',
      borderRadius: '24px',
      position: 'relative',
    }}>
      <div style={{
        position: 'absolute',
        top: '-14px',
        left: '32px',
        background: '#18181b',
        padding: '4px 20px',
        borderRadius: '16px',
        border: '1px solid rgba(255, 255, 255, 0.2)',
        color: '#a1a1aa',
        fontSize: '13px',
        fontWeight: 700,
        textTransform: 'uppercase',
        letterSpacing: '1.5px',
        boxShadow: '0 4px 12px rgba(0,0,0,0.5)'
      }}>
        {data.label}
      </div>
    </div>
  );
};

const CustomNode = ({ data, isConnectable }) => {
  const style = getColorForType(data.type);
  
  return (
    <div style={{
      width: '260px',
      background: 'rgba(15, 15, 20, 0.95)',
      borderRadius: '12px',
      border: `1px solid rgba(255, 255, 255, 0.1)`,
      borderTop: `4px solid ${style.accent}`,
      boxShadow: `0 8px 32px rgba(0, 0, 0, 0.6), 0 0 20px -5px ${style.glow}`,
      backdropFilter: 'blur(12px)',
      position: 'relative',
      overflow: 'hidden',
      transition: 'transform 0.2s, box-shadow 0.2s',
      cursor: 'pointer'
    }}
    onMouseEnter={(e) => { e.currentTarget.style.transform = 'translateY(-4px)'; e.currentTarget.style.boxShadow = `0 12px 40px rgba(0, 0, 0, 0.7), 0 0 25px -2px ${style.glow}`; }}
    onMouseLeave={(e) => { e.currentTarget.style.transform = 'translateY(0)'; e.currentTarget.style.boxShadow = `0 8px 32px rgba(0, 0, 0, 0.6), 0 0 20px -5px ${style.glow}`; }}
    >
      <div style={{ position: 'absolute', top: 0, left: 0, right: 0, bottom: 0, backgroundImage: 'radial-gradient(rgba(255, 255, 255, 0.1) 1px, transparent 1px)', backgroundSize: '12px 12px', opacity: 0.3 }} />
      
      <Handle type="target" position={Position.Left} isConnectable={isConnectable} style={{ background: '#18181b', border: `2px solid ${style.accent}`, width: '12px', height: '12px', left: '-6px' }} />
      
      <div style={{ padding: '16px 20px', position: 'relative', zIndex: 1 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '12px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: style.accent, fontSize: '11px', textTransform: 'uppercase', fontWeight: 700, letterSpacing: '1px' }}>
            <div style={{ padding: '4px', background: `linear-gradient(135deg, ${style.accent}33, ${style.accent}00)`, borderRadius: '6px', border: `1px solid ${style.accent}44` }}>
              {getIconForType(data.type)}
            </div>
            {data.type}
          </div>
          {data.status && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '9px', fontWeight: 600, background: data.status.toLowerCase() === 'healthy' ? 'rgba(16,185,129,0.1)' : 'rgba(245,158,11,0.1)', border: `1px solid ${data.status.toLowerCase() === 'healthy' ? '#10b981' : '#f59e0b'}`, padding: '3px 8px', borderRadius: '12px', color: data.status.toLowerCase() === 'healthy' ? '#10b981' : '#f59e0b', textTransform: 'uppercase' }}>
              <div style={{ width: '6px', height: '6px', borderRadius: '50%', background: data.status.toLowerCase() === 'healthy' ? '#10b981' : '#f59e0b', boxShadow: `0 0 6px ${data.status.toLowerCase() === 'healthy' ? '#10b981' : '#f59e0b'}` }} />
              {data.status}
            </div>
          )}
        </div>
        
        <div style={{ color: '#f4f4f5', fontSize: '15px', fontWeight: 600, letterSpacing: '0.3px', lineHeight: 1.3, textShadow: '0 2px 4px rgba(0,0,0,0.5)', marginBottom: '12px' }}>
          {data.label}
        </div>

        {data.tech && (
          <div style={{ display: 'inline-block', fontSize: '10px', color: '#d4d4d8', background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.1)', padding: '4px 8px', borderRadius: '4px', letterSpacing: '0.5px' }}>
            {data.tech}
          </div>
        )}
      </div>

      <Handle type="source" position={Position.Right} isConnectable={isConnectable} style={{ background: '#18181b', border: `2px solid ${style.accent}`, width: '12px', height: '12px', right: '-6px' }} />
    </div>
  );
};

const nodeTypes = {
  custom: CustomNode,
  zone: ZoneNode,
};

export default function ArchitectureViewer({ architectureJson, onNodeSelect }) {
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [isFullscreen, setIsFullscreen] = useState(false);

  useEffect(() => {
    try {
      const data = typeof architectureJson === 'string' ? JSON.parse(architectureJson) : architectureJson;
      
      const rfNodes = data.nodes.map(n => ({
        id: n.id,
        type: 'custom',
        data: { label: n.label, type: n.type, zone: n.zone, tech: n.tech, status: n.status, description: n.description },
        position: { x: 0, y: 0 }
      }));

      const rfEdges = data.edges.map((e, idx) => {
        let color = '#a1a1aa';
        let animated = true; // Make everything flow!
        if (e.type === 'sync') color = '#3b82f6';
        if (e.type === 'async') color = '#10b981';
        if (e.type === 'data') color = '#f59e0b';
        
        return {
          id: `e-${idx}`,
          source: e.source,
          target: e.target,
          label: e.label,
          type: 'smoothstep',
          animated,
          style: { stroke: color, strokeWidth: 3, opacity: 0.8, filter: `drop-shadow(0 0 8px ${color}88)` },
          labelStyle: { fill: '#ffffff', fontWeight: 600, fontSize: 12 },
          labelBgStyle: { fill: '#18181b', stroke: color, strokeWidth: 1, rx: 8, ry: 8 },
          labelBgPadding: [8, 4],
          markerEnd: {
            type: MarkerType.ArrowClosed,
            color,
            width: 20,
            height: 20,
          },
        };
      });

      const { nodes: layoutedNodes, edges: layoutedEdges } = getLayoutedElements(rfNodes, rfEdges, data.zones || []);
      
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
        background: 'radial-gradient(circle at 50% 50%, #1e1e24 0%, #050505 100%)',
        padding: '20px'
      } : {
        width: '100%', 
        height: '100%', 
        minHeight: '600px',
        background: 'radial-gradient(circle at 50% 50%, #1e1e24 0%, #050505 100%)', 
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
        onNodeClick={(e, node) => {
          if (node.type === 'custom' && onNodeSelect) {
            onNodeSelect(node.data);
          }
        }}
        nodeTypes={nodeTypes}
        fitView
        attributionPosition="bottom-right"
      >
        <Background color="#3f3f46" gap={20} size={1.5} style={{ opacity: 0.4 }} />
        <Controls style={{ background: '#18181b', color: '#fff', fill: '#fff' }} />
      </ReactFlow>
    </div>
  );
}
