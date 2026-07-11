import React, { useState, useEffect } from 'react';

const MemoryView = ({ API_URL }) => {
  const [memoryData, setMemoryData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchMemory = async () => {
      try {
        const res = await fetch(`${API_URL}/api/memory`);
        const data = await res.json();
        setMemoryData(data);
      } catch (err) {
        console.error("Failed to fetch memory data:", err);
      } finally {
        setLoading(false);
      }
    };
    fetchMemory();
  }, [API_URL]);

  return (
    <div style={{ padding: '24px', height: '100%', overflowY: 'auto', backgroundColor: 'var(--app-bg)' }}>
      <h2 style={{ display: 'flex', alignItems: 'center', gap: '10px', color: 'var(--text-primary)', marginTop: 0 }}>
        <span style={{ fontSize: '1.5rem' }}>🧠</span> yAI Learning Memory
      </h2>
      <p style={{ color: 'var(--text-secondary)' }}>
        yAI continuously learns from architectural decisions and preferred design systems across projects.
      </p>
      
      {loading ? (
        <div style={{ color: 'var(--text-secondary)', marginTop: '20px' }}>Loading memory banks...</div>
      ) : memoryData ? (
        <div style={{ marginTop: '30px', display: 'flex', flexDirection: 'column', gap: '20px' }}>
          
          <div className="dashboard-glass-card" style={{ padding: '20px' }}>
            <h4 style={{ margin: '0 0 15px 0', color: 'var(--accent)', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span>📐</span> Learned Patterns & Templates
            </h4>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: '12px' }}>
              {memoryData.patterns_learned.map((pattern, idx) => (
                <div key={idx} style={{ background: 'rgba(255,255,255,0.05)', padding: '12px', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.1)' }}>
                  <div style={{ fontWeight: '500', color: 'var(--text-primary)', marginBottom: '4px' }}>{pattern.pattern}</div>
                  <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Used {pattern.count} times ({(pattern.success_rate * 100).toFixed(0)}% success)</div>
                </div>
              ))}
            </div>
          </div>
          
          <div className="dashboard-glass-card" style={{ padding: '20px' }}>
            <h4 style={{ margin: '0 0 15px 0', color: 'var(--accent)', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span>🤔</span> Recent Decisions
            </h4>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              {memoryData.recent_decisions.map((decision, idx) => (
                <div key={idx} style={{ background: 'rgba(0,0,0,0.2)', padding: '16px', borderRadius: '8px', borderLeft: '3px solid var(--accent)' }}>
                  <span style={{ display: 'inline-block', padding: '2px 8px', background: 'var(--accent)', color: '#000', fontSize: '0.75rem', fontWeight: 'bold', borderRadius: '4px', marginBottom: '8px' }}>
                    {decision.agent} Agent
                  </span>
                  <div style={{ fontSize: '0.9rem', color: 'var(--modal-text-color)', lineHeight: '1.5' }}>
                    {decision.rationale}
                  </div>
                </div>
              ))}
            </div>
          </div>
          
        </div>
      ) : (
        <div style={{ color: 'var(--text-secondary)' }}>Failed to load memory data.</div>
      )}
    </div>
  );
};

export default MemoryView;
