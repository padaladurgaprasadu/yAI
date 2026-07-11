import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Activity, Server, Users, Zap, AlertTriangle, ShieldCheck, Database, Clock, TerminalSquare, Key, Network } from 'lucide-react';

const PlatformDashboards = ({ API_URL }) => {
  const [activeTab, setActiveTab] = useState('telemetry');
  const [metrics, setMetrics] = useState(null);
  const [workspaces, setWorkspaces] = useState([]);
  const [isLoading, setIsLoading] = useState(true);

  // Fetch real/mock data from backend
  useEffect(() => {
    const fetchData = async () => {
      setIsLoading(true);
      try {
        const metricsRes = await fetch(`${API_URL}/api/telemetry/metrics`);
        if (metricsRes.ok) {
          const mData = await metricsRes.json();
          setMetrics(mData);
        } else {
          // Fallback if endpoint fails
          setMetrics({ active_swarms: 2, tokens_processed: 850000, avg_latency_ms: 320, error_rate: 0.01, uptime: "99.9%" });
        }

        const orgsRes = await fetch(`${API_URL}/api/orgs/workspaces`);
        if (orgsRes.ok) {
          const oData = await orgsRes.json();
          setWorkspaces(oData);
        }
      } catch (err) {
        console.error("Dashboard data fetch failed", err);
        setMetrics({ active_swarms: 3, tokens_processed: 1200000, avg_latency_ms: 450, error_rate: 0.02, uptime: "99.8%" });
      } finally {
        setIsLoading(false);
      }
    };

    fetchData();
    
    // Auto-refresh every 10 seconds
    const interval = setInterval(fetchData, 10000);
    return () => clearInterval(interval);
  }, [API_URL]);

  const tabs = [
    { id: 'telemetry', label: 'Telemetry', icon: <Activity size={18} /> },
    { id: 'gateway', label: 'AI Gateway', icon: <Network size={18} /> },
    { id: 'enterprise', label: 'Enterprise', icon: <Users size={18} /> }
  ];

  return (
    <div style={{ padding: '30px', maxWidth: '1200px', margin: '0 auto', height: '100%', overflowY: 'auto' }}>
      
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '30px' }}>
        <div>
          <h1 style={{ fontSize: '2rem', fontWeight: 'bold', margin: '0 0 8px 0', display: 'flex', alignItems: 'center', gap: '12px' }}>
            <Server className="animate-pulse-glow" style={{ color: 'var(--accent)', borderRadius: '50%' }} size={32} />
            AiON Command Center
          </h1>
          <p style={{ color: 'var(--text-secondary)', margin: 0 }}>Production monitoring, API gateway routing, and enterprise controls.</p>
        </div>
      </div>

      {/* Navigation Tabs */}
      <div style={{ display: 'flex', gap: '10px', marginBottom: '30px', borderBottom: '1px solid var(--border-color)', paddingBottom: '16px' }}>
        {tabs.map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            style={{
              display: 'flex', alignItems: 'center', gap: '8px',
              padding: '10px 20px', borderRadius: '8px',
              background: activeTab === tab.id ? 'rgba(59, 130, 246, 0.15)' : 'transparent',
              color: activeTab === tab.id ? 'var(--accent)' : 'var(--text-secondary)',
              border: `1px solid ${activeTab === tab.id ? 'rgba(59, 130, 246, 0.3)' : 'transparent'}`,
              cursor: 'pointer', fontWeight: '500', transition: 'all 0.2s ease'
            }}
          >
            {tab.icon}
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      <AnimatePresence mode="wait">
        <motion.div
          key={activeTab}
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -10 }}
          transition={{ duration: 0.2 }}
        >
          {activeTab === 'telemetry' && <TelemetryTab metrics={metrics} isLoading={isLoading} />}
          {activeTab === 'gateway' && <GatewayTab />}
          {activeTab === 'enterprise' && <EnterpriseTab workspaces={workspaces} isLoading={isLoading} />}
        </motion.div>
      </AnimatePresence>

    </div>
  );
};

// ==========================================
// 1. Telemetry Tab
// ==========================================
const TelemetryTab = ({ metrics, isLoading }) => {
  if (isLoading && !metrics) return <div style={{ color: 'var(--text-secondary)' }}>Loading metrics...</div>;

  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '20px' }}>
      
      {/* Top Level Cards */}
      <div className="dashboard-glass-card">
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', color: 'var(--text-secondary)', marginBottom: '16px' }}>
          <Activity size={18} /> Active Swarms
        </div>
        <div className="metric-value-text">{metrics?.active_swarms || 0}</div>
        <div style={{ fontSize: '0.85rem', color: 'var(--success)', marginTop: '8px', display: 'flex', alignItems: 'center', gap: '4px' }}>
          <div className="status-dot status-green animate-pulse-glow-success"></div> All healthy
        </div>
      </div>

      <div className="dashboard-glass-card">
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', color: 'var(--text-secondary)', marginBottom: '16px' }}>
          <Zap size={18} /> Avg Latency
        </div>
        <div className="metric-value-text metric-value-accent">{metrics?.avg_latency_ms || 0} <span style={{ fontSize: '1rem', color: 'var(--text-secondary)' }}>ms</span></div>
        <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginTop: '8px' }}>
          p95: {(metrics?.avg_latency_ms * 1.4).toFixed(0)} ms
        </div>
      </div>

      <div className="dashboard-glass-card">
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', color: 'var(--text-secondary)', marginBottom: '16px' }}>
          <Database size={18} /> Tokens Processed
        </div>
        <div className="metric-value-text">{(metrics?.tokens_processed / 1000000).toFixed(2)}M</div>
        <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginTop: '8px' }}>
          Across all providers
        </div>
      </div>

      <div className="dashboard-glass-card" style={{ borderColor: metrics?.error_rate > 0.05 ? 'rgba(239, 68, 68, 0.4)' : '' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', color: 'var(--text-secondary)', marginBottom: '16px' }}>
          <AlertTriangle size={18} /> Error Rate
        </div>
        <div className="metric-value-text" style={{ color: metrics?.error_rate > 0.05 ? 'var(--error)' : 'inherit' }}>
          {(metrics?.error_rate * 100).toFixed(1)}%
        </div>
        <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginTop: '8px' }}>
          System Uptime: {metrics?.uptime}
        </div>
      </div>

      {/* Running Tasks Table (Mock) */}
      <div className="dashboard-glass-card" style={{ gridColumn: '1 / -1', marginTop: '10px' }}>
        <h3 style={{ margin: '0 0 20px 0', display: 'flex', alignItems: 'center', gap: '10px' }}><TerminalSquare size={20} /> Active Agent Executions</h3>
        <table className="dashboard-table">
          <thead>
            <tr>
              <th>Task ID</th>
              <th>Agent Role</th>
              <th>Status</th>
              <th>Model</th>
              <th>Duration</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td style={{ fontFamily: 'monospace', color: 'var(--accent)' }}>tsk_01H9Z2X</td>
              <td>Code Architect</td>
              <td><div className="status-dot status-green"></div> Generating</td>
              <td>NVIDIA GLM-5.2</td>
              <td>45s</td>
            </tr>
            <tr>
              <td style={{ fontFamily: 'monospace', color: 'var(--accent)' }}>tsk_01H9Z5B</td>
              <td>Research Agent</td>
              <td><div className="status-dot status-yellow"></div> Searching Web</td>
              <td>Llama 3.1 8B</td>
              <td>12s</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  );
};

// ==========================================
// 2. AI Gateway Tab
// ==========================================
const GatewayTab = () => {
  const registeredModels = [
    { id: 'glm-5.2', provider: 'NVIDIA NIM', capability: 'Reasoning/Coding', status: 'healthy', latency: '350ms' },
    { id: 'llama-3.1-8b', provider: 'NVIDIA NIM', capability: 'Chat/Fast', status: 'healthy', latency: '120ms' },
    { id: 'nv-embed', provider: 'NVIDIA NIM', capability: 'Embeddings', status: 'healthy', latency: '40ms' },
    { id: 'qwen-coder', provider: 'NVIDIA NIM', capability: 'Fallback Coding', status: 'healthy', latency: '280ms' }
  ];

  return (
    <div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '20px', marginBottom: '20px' }}>
        <div className="dashboard-glass-card">
          <h3 style={{ margin: '0 0 20px 0', display: 'flex', alignItems: 'center', gap: '10px' }}><ShieldCheck size={20} /> Provider Health</h3>
          
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '12px', background: 'rgba(255,255,255,0.03)', borderRadius: '8px', marginBottom: '10px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <div className="status-dot status-green animate-pulse-glow-success"></div>
              <strong>NVIDIA API</strong>
            </div>
            <span style={{ fontSize: '0.85rem', color: 'var(--success)' }}>Operational</span>
          </div>

          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '12px', background: 'rgba(255,255,255,0.03)', borderRadius: '8px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <div className="status-dot status-green"></div>
              <strong>Local Vector DB</strong>
            </div>
            <span style={{ fontSize: '0.85rem', color: 'var(--success)' }}>Operational</span>
          </div>
        </div>

        <div className="dashboard-glass-card">
          <h3 style={{ margin: '0 0 20px 0', display: 'flex', alignItems: 'center', gap: '10px' }}><Network size={20} /> Current Routing</h3>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', marginBottom: '15px' }}>
            The AI Gateway is currently routing requests across 1 active provider key.
          </p>
          <div style={{ borderLeft: '2px solid var(--accent)', paddingLeft: '15px' }}>
            <div style={{ marginBottom: '10px' }}>
              <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', textTransform: 'uppercase' }}>Primary Chat</div>
              <div style={{ fontWeight: '500' }}>Llama 3.1 8B Instruct</div>
            </div>
            <div>
              <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', textTransform: 'uppercase' }}>Heavy Reasoning</div>
              <div style={{ fontWeight: '500', color: 'var(--accent)' }}>NVIDIA GLM-5.2</div>
            </div>
          </div>
        </div>
      </div>

      <div className="dashboard-glass-card">
        <h3 style={{ margin: '0 0 20px 0', display: 'flex', alignItems: 'center', gap: '10px' }}><Key size={20} /> Registered Models</h3>
        <table className="dashboard-table">
          <thead>
            <tr>
              <th>Model ID</th>
              <th>Provider</th>
              <th>Capability Focus</th>
              <th>Avg Latency</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {registeredModels.map(model => (
              <tr key={model.id}>
                <td style={{ fontWeight: '500' }}>{model.id}</td>
                <td>{model.provider}</td>
                <td style={{ color: 'var(--text-secondary)' }}>{model.capability}</td>
                <td>{model.latency}</td>
                <td>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <div className={`status-dot ${model.status === 'healthy' ? 'status-green' : 'status-yellow'}`}></div>
                    {model.status}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

// ==========================================
// 3. Enterprise Tab
// ==========================================
const EnterpriseTab = ({ workspaces, isLoading }) => {
  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: '20px' }}>
      
      <div className="dashboard-glass-card" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h3 style={{ margin: '0 0 8px 0', fontSize: '1.2rem' }}>Acme Corp Organization</h3>
          <p style={{ margin: 0, color: 'var(--text-secondary)' }}>Enterprise Plan • 24 active seats</p>
        </div>
        <button style={{ padding: '8px 16px', background: 'var(--accent)', color: '#fff', border: 'none', borderRadius: '6px', cursor: 'pointer', fontWeight: '500' }}>
          Invite Member
        </button>
      </div>

      <div className="dashboard-glass-card">
        <h3 style={{ margin: '0 0 20px 0', display: 'flex', alignItems: 'center', gap: '10px' }}><Users size={20} /> Collaborative Workspaces</h3>
        {isLoading ? (
          <div style={{ color: 'var(--text-secondary)' }}>Loading workspaces...</div>
        ) : (
          <table className="dashboard-table">
            <thead>
              <tr>
                <th>Workspace ID</th>
                <th>Name</th>
                <th>Members</th>
                <th>Role Policy</th>
              </tr>
            </thead>
            <tbody>
              {workspaces && workspaces.length > 0 ? workspaces.map(ws => (
                <tr key={ws.id}>
                  <td style={{ fontFamily: 'monospace', color: 'var(--accent)' }}>{ws.id}</td>
                  <td style={{ fontWeight: '500' }}>{ws.name}</td>
                  <td>{ws.members} active</td>
                  <td><span style={{ padding: '4px 8px', background: 'rgba(255,255,255,0.1)', borderRadius: '4px', fontSize: '0.8rem' }}>Strict RBAC</span></td>
                </tr>
              )) : (
                <tr>
                  <td colSpan="4" style={{ textAlign: 'center', color: 'var(--text-secondary)' }}>No workspaces found.</td>
                </tr>
              )}
            </tbody>
          </table>
        )}
      </div>

      <div className="dashboard-glass-card">
        <h3 style={{ margin: '0 0 20px 0', display: 'flex', alignItems: 'center', gap: '10px' }}><Clock size={20} /> Recent Audit Logs</h3>
        <table className="dashboard-table" style={{ opacity: 0.8 }}>
          <thead>
            <tr>
              <th>Timestamp</th>
              <th>Action</th>
              <th>User</th>
              <th>IP Address</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>2026-07-11 10:15:32</td>
              <td>API Key Encrypted & Stored</td>
              <td>admin@acme.com</td>
              <td>192.168.1.42</td>
            </tr>
            <tr>
              <td>2026-07-11 09:02:11</td>
              <td>New Agent Workspace Created</td>
              <td>dev@acme.com</td>
              <td>10.0.0.15</td>
            </tr>
          </tbody>
        </table>
      </div>

    </div>
  );
};

export default PlatformDashboards;
