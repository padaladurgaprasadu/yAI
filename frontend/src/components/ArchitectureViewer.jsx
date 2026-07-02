import React, { useCallback, useMemo, useEffect, useState, useRef } from 'react';
import ReactFlow, { Background, Controls, MiniMap, useNodesState, useEdgesState, MarkerType, Handle, Position } from 'reactflow';
import dagre from 'dagre';
import 'reactflow/dist/style.css';
import { Database, Server, Globe, ExternalLink, Mail, Zap, User, Code, Box, Maximize, Minimize, Info, Shield, Activity, X, DownloadCloud, PanelRightClose, PanelRightOpen } from 'lucide-react';

const getLayoutedElements = (nodes, edges, zones = [], direction = 'LR') => {
  const dagreGraph = new dagre.graphlib.Graph({ compound: true });
  dagreGraph.setGraph({ rankdir: direction, nodesep: 60, ranksep: 150, edgesep: 40, ranker: 'network-simplex' });
  dagreGraph.setDefaultEdgeLabel(() => ({}));

  const isHorizontal = direction === 'LR';

  zones.forEach(zone => {
    dagreGraph.setNode(zone.id, { label: zone.label });
  });

  nodes.forEach((node) => {
    dagreGraph.setNode(node.id, { width: 280, height: 180 });
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
        position: { x: zNode.x - zNode.width / 2 - 20, y: zNode.y - zNode.height / 2 - 40 },
        style: { width: zNode.width + 40, height: zNode.height + 60, zIndex: -1 },
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
      position: { x: n.x - 130, y: n.y - 80 }, 
      style: { zIndex: 10 }
    });
  });

  return { nodes: layoutedNodes, edges };
};

const getIconForType = (type) => {
  switch ((type || '').toLowerCase()) {
    case 'database': return <Database size={20} />;
    case 'microservice': return <Box size={20} />;
    case 'gateway': return <Globe size={20} />;
    case 'external': return <ExternalLink size={20} />;
    case 'queue': return <Mail size={20} />;
    case 'ai': return <Zap size={20} />;
    case 'user': return <User size={20} />;
    case 'cache': return <Database size={20} color="#f59e0b" />;
    case 'monitoring': return <Activity size={20} />;
    case 'security': return <Shield size={20} />;
    default: return <Server size={20} />;
  }
};

const getColorForType = (type) => {
  switch ((type || '').toLowerCase()) {
    case 'database': return { accent: '#f43f5e', glow: 'rgba(244, 63, 94, 0.4)' };
    case 'microservice': return { accent: '#10b981', glow: 'rgba(16, 185, 129, 0.4)' };
    case 'gateway': return { accent: '#8b5cf6', glow: 'rgba(139, 92, 246, 0.4)' };
    case 'external': return { accent: '#3b82f6', glow: 'rgba(59, 130, 246, 0.4)' };
    case 'queue': return { accent: '#f59e0b', glow: 'rgba(245, 158, 11, 0.4)' };
    case 'ai': return { accent: '#ec4899', glow: 'rgba(236, 72, 153, 0.4)' };
    case 'security': return { accent: '#14b8a6', glow: 'rgba(20, 184, 166, 0.4)' };
    case 'monitoring': return { accent: '#a855f7', glow: 'rgba(168, 85, 247, 0.4)' };
    default: return { accent: '#6b7280', glow: 'rgba(107, 114, 128, 0.4)' };
  }
};

const ZoneNode = ({ data }) => {
  return (
    <div style={{
      width: '100%',
      height: '100%',
      backgroundColor: 'rgba(255, 255, 255, 0.03)',
      border: '2px dashed rgba(255, 255, 255, 0.15)',
      borderRadius: '24px',
      position: 'relative',
    }}>
      <div style={{
        position: 'absolute',
        top: '-16px',
        left: '32px',
        background: '#18181b',
        padding: '6px 24px',
        borderRadius: '20px',
        border: '1px solid rgba(255, 255, 255, 0.1)',
        color: '#e4e4e7',
        fontSize: '14px',
        fontWeight: 700,
        textTransform: 'uppercase',
        letterSpacing: '2px',
        boxShadow: '0 4px 20px rgba(0,0,0,0.6)'
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
      width: '280px',
      background: 'rgba(15, 15, 20, 0.95)',
      borderRadius: '16px',
      border: `1px solid rgba(255, 255, 255, 0.05)`,
      borderTop: `4px solid ${style.accent}`,
      boxShadow: `0 8px 32px rgba(0, 0, 0, 0.5), 0 0 20px -5px ${style.glow}`,
      backdropFilter: 'blur(12px)',
      position: 'relative',
      overflow: 'hidden',
      transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
      cursor: 'pointer'
    }}
    onMouseEnter={(e) => { 
      e.currentTarget.style.transform = 'translateY(-6px) scale(1.02)'; 
      e.currentTarget.style.boxShadow = `0 16px 48px rgba(0, 0, 0, 0.6), 0 0 30px 2px ${style.glow}`; 
      e.currentTarget.style.border = `1px solid ${style.accent}55`;
      e.currentTarget.style.borderTop = `4px solid ${style.accent}`;
    }}
    onMouseLeave={(e) => { 
      e.currentTarget.style.transform = 'translateY(0) scale(1)'; 
      e.currentTarget.style.boxShadow = `0 8px 32px rgba(0, 0, 0, 0.5), 0 0 20px -5px ${style.glow}`; 
      e.currentTarget.style.border = `1px solid rgba(255, 255, 255, 0.05)`;
      e.currentTarget.style.borderTop = `4px solid ${style.accent}`;
    }}
    >
      <div style={{ position: 'absolute', top: 0, left: 0, right: 0, bottom: 0, backgroundImage: 'radial-gradient(rgba(255, 255, 255, 0.05) 1px, transparent 1px)', backgroundSize: '16px 16px', opacity: 0.5 }} />
      
      <Handle type="target" position={Position.Left} isConnectable={isConnectable} style={{ background: '#18181b', border: `2px solid ${style.accent}`, width: '14px', height: '14px', left: '-7px' }} />
      
      <div style={{ padding: '20px', position: 'relative', zIndex: 1 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '16px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', color: style.accent, fontSize: '12px', textTransform: 'uppercase', fontWeight: 800, letterSpacing: '1px' }}>
            <div style={{ padding: '6px', background: `linear-gradient(135deg, ${style.accent}33, ${style.accent}00)`, borderRadius: '8px', border: `1px solid ${style.accent}44` }}>
              {getIconForType(data.type)}
            </div>
            {data.type}
          </div>
          {data.status && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '10px', fontWeight: 700, background: data.status.toLowerCase() === 'healthy' ? 'rgba(16,185,129,0.1)' : 'rgba(245,158,11,0.1)', border: `1px solid ${data.status.toLowerCase() === 'healthy' ? '#10b981' : '#f59e0b'}`, padding: '4px 10px', borderRadius: '12px', color: data.status.toLowerCase() === 'healthy' ? '#10b981' : '#f59e0b', textTransform: 'uppercase' }}>
              <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: data.status.toLowerCase() === 'healthy' ? '#10b981' : '#f59e0b', boxShadow: `0 0 8px ${data.status.toLowerCase() === 'healthy' ? '#10b981' : '#f59e0b'}` }} />
              {data.status}
            </div>
          )}
        </div>
        
        <div style={{ color: '#ffffff', fontSize: '16px', fontWeight: 700, letterSpacing: '0.5px', lineHeight: 1.4, textShadow: '0 2px 8px rgba(0,0,0,0.8)', marginBottom: '12px' }}>
          {data.label}
        </div>

        {data.tech && (
          <div style={{ display: 'inline-block', fontSize: '11px', color: '#e4e4e7', background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.15)', padding: '6px 12px', borderRadius: '6px', letterSpacing: '0.5px', fontWeight: 600 }}>
            {data.tech}
          </div>
        )}
      </div>

      <Handle type="source" position={Position.Right} isConnectable={isConnectable} style={{ background: '#18181b', border: `2px solid ${style.accent}`, width: '14px', height: '14px', right: '-7px' }} />
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
  
  const [reviewData, setReviewData] = useState(null);
  const [selectedNodeData, setSelectedNodeData] = useState(null);
  const [activeView, setActiveView] = useState('standard'); // standard, event, data, security
  const [isUnlocked, setIsUnlocked] = useState(false);
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const rfInstanceRef = useRef(null);

  useEffect(() => {
    if (rfInstanceRef.current) {
      setTimeout(() => {
        rfInstanceRef.current.fitView({ padding: 0.2, duration: 800 });
      }, 100);
    }
  }, [isSidebarOpen, isFullscreen]);

  const handleExportTerraform = useCallback(() => {
    try {
      const data = typeof architectureJson === 'string' ? JSON.parse(architectureJson) : architectureJson;
      let tfContent = `# Auto-generated Terraform Scaffolding by AiON Architecture Studio\n\n`;
      data.nodes.forEach(node => {
        const resourceName = node.label.toLowerCase().replace(/[^a-z0-9]/g, '_');
        if (node.type === 'database') {
          tfContent += `resource "aws_db_instance" "${resourceName}" {\n  allocated_storage = 20\n  engine = "postgres"\n  instance_class = "db.t3.micro"\n}\n\n`;
        } else if (node.type === 'microservice' || node.type === 'gateway') {
          tfContent += `resource "aws_ecs_service" "${resourceName}" {\n  name = "${node.label}"\n  cluster = aws_ecs_cluster.main.id\n}\n\n`;
        } else {
          tfContent += `# Resource placeholder for ${node.label} (${node.type})\n\n`;
        }
      });
      const blob = new Blob([tfContent], { type: 'text/plain' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'infrastructure.tf';
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      console.error("Export failed", e);
    }
  }, [architectureJson]);

  useEffect(() => {
    try {
      const data = typeof architectureJson === 'string' ? JSON.parse(architectureJson) : architectureJson;
      setReviewData(data.review || null);
      
      const rfNodes = data.nodes.map(n => ({
        id: n.id,
        type: 'custom',
        data: { label: n.label, type: n.type, zone: n.zone, tech: n.tech, status: n.status, description: n.description },
        position: { x: 0, y: 0 }
      }));

      const rfEdges = data.edges.map((e, idx) => {
        let color = '#9ca3af'; // default gray
        let animated = false;
        let lineStyle = { stroke: color, strokeWidth: 2, opacity: 0.6 };
        
        // Smart Connection Engine
        if (e.type === 'sync' || e.type === 'rest' || e.type === 'grpc') {
            color = '#3b82f6'; // Blue
            animated = true;
            lineStyle = { stroke: color, strokeWidth: 3, opacity: 0.8, filter: `drop-shadow(0 0 6px ${color}88)` };
        } else if (e.type === 'async' || e.type === 'event') {
            color = '#10b981'; // Green
            animated = true;
            lineStyle = { stroke: color, strokeWidth: 3, opacity: 0.8, filter: `drop-shadow(0 0 6px ${color}88)`, strokeDasharray: '5,5' };
        } else if (e.type === 'data' || e.type === 'db') {
            color = '#f59e0b'; // Orange
            animated = true;
            lineStyle = { stroke: color, strokeWidth: 3, opacity: 0.8, filter: `drop-shadow(0 0 6px ${color}88)` };
        } else if (e.type === 'monitor' || e.type === 'observability') {
            color = '#a855f7'; // Purple
            animated = true;
            lineStyle = { stroke: color, strokeWidth: 2, opacity: 0.5, strokeDasharray: '3,3' };
        } else if (e.type === 'fail' || e.type === 'retry') {
            color = '#ef4444'; // Red
            animated = true;
            lineStyle = { stroke: color, strokeWidth: 3, opacity: 0.8, filter: `drop-shadow(0 0 8px ${color}88)` };
        }
        
        // View Filters (Dim non-relevant edges based on toggle)
        if (activeView === 'event' && e.type !== 'async' && e.type !== 'event') {
            lineStyle.opacity = 0.1;
        } else if (activeView === 'data' && e.type !== 'data' && e.type !== 'db') {
            lineStyle.opacity = 0.1;
        }

        return {
          id: `e-${idx}`,
          source: e.source,
          target: e.target,
          label: e.label,
          type: 'smoothstep',
          animated,
          style: lineStyle,
          labelStyle: { fill: '#ffffff', fontWeight: 700, fontSize: 13, letterSpacing: '0.5px' },
          labelBgStyle: { fill: '#18181b', stroke: color, strokeWidth: 1.5, rx: 8, ry: 8 },
          labelBgPadding: [10, 6],
          markerEnd: {
            type: MarkerType.ArrowClosed,
            color,
            width: 24,
            height: 24,
          },
        };
      });

      const { nodes: layoutedNodes, edges: layoutedEdges } = getLayoutedElements(rfNodes, rfEdges, data.zones || []);
      
      setNodes(layoutedNodes);
      setEdges(layoutedEdges);
    } catch (err) {
      console.error("Failed to parse architecture JSON", err);
    }
  }, [architectureJson, activeView]);

  return (
    <div style={{ 
      ...(isFullscreen ? {
        position: 'fixed',
        top: 0,
        left: 0,
        width: '100vw',
        height: '100vh',
        zIndex: 99999,
        background: '#09090b',
        padding: '0px',
        display: 'flex'
      } : {
        width: '100%', 
        height: '100%', 
        minHeight: '700px',
        background: '#09090b', 
        borderRadius: '16px', 
        border: '1px solid rgba(255,255,255,0.1)', 
        overflow: 'hidden', 
        marginTop: '16px', 
        marginBottom: '16px',
        position: 'relative',
        display: 'flex'
      })
    }}>
      {/* LEFT: Node Details Panel */}
      {selectedNodeData && (
        <div style={{
          width: '320px',
          background: 'rgba(24,24,27,0.95)',
          borderRight: '1px solid rgba(255,255,255,0.1)',
          padding: '24px',
          display: 'flex',
          flexDirection: 'column',
          gap: '20px',
          backdropFilter: 'blur(10px)',
          zIndex: 20
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <h3 style={{ margin: 0, color: 'white', fontSize: '18px', fontWeight: 'bold' }}>Component Details</h3>
            <button onClick={() => setSelectedNodeData(null)} style={{ background: 'transparent', border: 'none', color: '#a1a1aa', cursor: 'pointer' }}>
              <X size={20} />
            </button>
          </div>
          
          <div style={{ background: 'rgba(0,0,0,0.3)', padding: '16px', borderRadius: '12px', border: '1px solid rgba(255,255,255,0.05)' }}>
            <div style={{ color: '#a1a1aa', fontSize: '12px', textTransform: 'uppercase', marginBottom: '4px', fontWeight: 600 }}>Name</div>
            <div style={{ color: 'white', fontSize: '16px', fontWeight: 700 }}>{selectedNodeData.label}</div>
          </div>

          <div style={{ background: 'rgba(0,0,0,0.3)', padding: '16px', borderRadius: '12px', border: '1px solid rgba(255,255,255,0.05)' }}>
            <div style={{ color: '#a1a1aa', fontSize: '12px', textTransform: 'uppercase', marginBottom: '4px', fontWeight: 600 }}>Type & Tech</div>
            <div style={{ color: '#3b82f6', fontSize: '14px', fontWeight: 600 }}>{selectedNodeData.type}</div>
            <div style={{ color: 'white', fontSize: '14px', marginTop: '4px' }}>{selectedNodeData.tech}</div>
          </div>

          <div style={{ background: 'rgba(0,0,0,0.3)', padding: '16px', borderRadius: '12px', border: '1px solid rgba(255,255,255,0.05)', flexGrow: 1 }}>
            <div style={{ color: '#a1a1aa', fontSize: '12px', textTransform: 'uppercase', marginBottom: '8px', fontWeight: 600 }}>Description</div>
            <div style={{ color: '#e4e4e7', fontSize: '14px', lineHeight: 1.6 }}>{selectedNodeData.description || 'No description provided for this component.'}</div>
          </div>
        </div>
      )}

      {/* MIDDLE: React Flow Canvas */}
      <div style={{ flexGrow: 1, position: 'relative' }}>
        
        {/* Toolbar Overlay */}
        <div style={{ position: 'absolute', top: '24px', left: '24px', zIndex: 10, display: 'flex', gap: '8px', background: 'rgba(24,24,27,0.8)', padding: '8px', borderRadius: '12px', border: '1px solid rgba(255,255,255,0.1)', backdropFilter: 'blur(8px)' }}>
            <button onClick={() => setActiveView('standard')} style={{ padding: '6px 12px', borderRadius: '8px', background: activeView === 'standard' ? '#3b82f6' : 'transparent', color: 'white', border: 'none', cursor: 'pointer', fontWeight: 600, fontSize: '12px' }}>Standard View</button>
            <button onClick={() => setActiveView('event')} style={{ padding: '6px 12px', borderRadius: '8px', background: activeView === 'event' ? '#10b981' : 'transparent', color: 'white', border: 'none', cursor: 'pointer', fontWeight: 600, fontSize: '12px' }}>Event Flow</button>
            <button onClick={() => setActiveView('data')} style={{ padding: '6px 12px', borderRadius: '8px', background: activeView === 'data' ? '#f59e0b' : 'transparent', color: 'white', border: 'none', cursor: 'pointer', fontWeight: 600, fontSize: '12px' }}>Data View</button>
            <div style={{ width: '1px', background: 'rgba(255,255,255,0.1)', margin: '0 4px' }} />
            <button onClick={() => setIsUnlocked(!isUnlocked)} style={{ padding: '6px 12px', borderRadius: '8px', background: isUnlocked ? '#ec4899' : 'transparent', color: 'white', border: '1px solid rgba(255,255,255,0.2)', cursor: 'pointer', fontWeight: 600, fontSize: '12px' }}>{isUnlocked ? 'Lock Canvas' : 'Unlock Canvas'}</button>
            <button onClick={handleExportTerraform} style={{ padding: '6px 12px', borderRadius: '8px', background: '#10b981', color: 'white', border: 'none', cursor: 'pointer', fontWeight: 600, fontSize: '12px', display: 'flex', alignItems: 'center', gap: '6px' }}><DownloadCloud size={14} /> Export IaC</button>
        </div>

        <div style={{ position: 'absolute', top: '24px', right: '24px', zIndex: 10, display: 'flex', gap: '12px' }}>
          <button 
            onClick={() => setIsSidebarOpen(!isSidebarOpen)}
            style={{
              background: 'rgba(24, 24, 27, 0.8)',
              border: '1px solid rgba(255,255,255,0.1)',
              color: 'white',
              padding: '10px 16px',
              borderRadius: '12px',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              backdropFilter: 'blur(8px)',
              boxShadow: '0 8px 16px rgba(0, 0, 0, 0.4)',
              fontWeight: 600
            }}
          >
            {isSidebarOpen ? <PanelRightClose size={16} /> : <PanelRightOpen size={16} />}
            {isSidebarOpen ? 'Hide Review' : 'Show Review'}
          </button>
          
          <button 
            onClick={() => setIsFullscreen(!isFullscreen)}
            style={{
              background: 'rgba(24, 24, 27, 0.8)',
              border: '1px solid rgba(255,255,255,0.1)',
              color: 'white',
              padding: '10px 16px',
              borderRadius: '12px',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              backdropFilter: 'blur(8px)',
              boxShadow: '0 8px 16px rgba(0, 0, 0, 0.4)',
              fontWeight: 600
            }}
          >
            {isFullscreen ? <Minimize size={16} /> : <Maximize size={16} />}
            {isFullscreen ? 'Exit Fullscreen' : 'Expand View'}
          </button>
        </div>

        <ReactFlow
          key={isFullscreen ? 'fs' : 'normal'}
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onNodeClick={(e, node) => {
            if (node.type === 'custom') {
              setSelectedNodeData(node.data);
              if (onNodeSelect) onNodeSelect(node.data);
            }
          }}
          nodesDraggable={isUnlocked}
          nodesConnectable={isUnlocked}
          nodeTypes={nodeTypes}
          onInit={(instance) => { rfInstanceRef.current = instance; }}
          fitView
          fitViewOptions={{ padding: 0.2 }}
          attributionPosition="bottom-right"
        >
          <Background color="#52525b" gap={24} size={2} style={{ opacity: 0.2 }} />
          <Controls style={{ background: '#18181b', color: '#fff', fill: '#fff', border: '1px solid rgba(255,255,255,0.1)' }} />
        </ReactFlow>
      </div>

      {/* RIGHT: Architecture Validation Sidebar */}
      {reviewData && isSidebarOpen && (
        <div style={{
          width: '380px',
          background: 'rgba(15,15,20,0.98)',
          borderLeft: '1px solid rgba(255,255,255,0.1)',
          padding: '24px',
          display: 'flex',
          flexDirection: 'column',
          gap: '20px',
          overflowY: 'auto',
          zIndex: 20
        }}>
          <h2 style={{ margin: 0, color: 'white', fontSize: '20px', fontWeight: 800, display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Shield size={24} color="#10b981" /> Architecture Review
          </h2>
          
          <div style={{ background: 'linear-gradient(135deg, rgba(16,185,129,0.1), rgba(16,185,129,0))', border: '1px solid rgba(16,185,129,0.3)', padding: '20px', borderRadius: '16px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span style={{ color: '#e4e4e7', fontSize: '14px', fontWeight: 600 }}>Validation Score</span>
            <span style={{ color: '#10b981', fontSize: '32px', fontWeight: 900 }}>{reviewData.score || 95}/100</span>
          </div>

          {reviewData.scalability && (
            <div>
              <div style={{ color: '#a1a1aa', fontSize: '12px', textTransform: 'uppercase', marginBottom: '8px', fontWeight: 700 }}>Scalability</div>
              <div style={{ color: '#d4d4d8', fontSize: '14px', lineHeight: 1.5, background: 'rgba(255,255,255,0.02)', padding: '12px', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.05)' }}>{reviewData.scalability}</div>
            </div>
          )}

          {reviewData.security && (
            <div>
              <div style={{ color: '#a1a1aa', fontSize: '12px', textTransform: 'uppercase', marginBottom: '8px', fontWeight: 700 }}>Security Posture</div>
              <div style={{ color: '#d4d4d8', fontSize: '14px', lineHeight: 1.5, background: 'rgba(255,255,255,0.02)', padding: '12px', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.05)' }}>{reviewData.security}</div>
            </div>
          )}

          {reviewData.bottlenecks && reviewData.bottlenecks.length > 0 && (
            <div>
              <div style={{ color: '#ef4444', fontSize: '12px', textTransform: 'uppercase', marginBottom: '8px', fontWeight: 700 }}>Potential Bottlenecks</div>
              <ul style={{ margin: 0, paddingLeft: '20px', color: '#fca5a5', fontSize: '14px', lineHeight: 1.6 }}>
                {reviewData.bottlenecks.map((item, i) => <li key={i}>{item}</li>)}
              </ul>
            </div>
          )}

          {reviewData.recommendations && reviewData.recommendations.length > 0 && (
            <div>
              <div style={{ color: '#3b82f6', fontSize: '12px', textTransform: 'uppercase', marginBottom: '8px', fontWeight: 700 }}>Recommendations</div>
              <ul style={{ margin: 0, paddingLeft: '20px', color: '#93c5fd', fontSize: '14px', lineHeight: 1.6 }}>
                {reviewData.recommendations.map((item, i) => <li key={i}>{item}</li>)}
              </ul>
            </div>
          )}
          
          {reviewData.tradeoffs && reviewData.tradeoffs.length > 0 && (
            <div>
              <div style={{ color: '#f59e0b', fontSize: '12px', textTransform: 'uppercase', marginBottom: '8px', fontWeight: 700 }}>Architectural Tradeoffs</div>
              <ul style={{ margin: 0, paddingLeft: '20px', color: '#fcd34d', fontSize: '14px', lineHeight: 1.6 }}>
                {reviewData.tradeoffs.map((item, i) => <li key={i}>{item}</li>)}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
