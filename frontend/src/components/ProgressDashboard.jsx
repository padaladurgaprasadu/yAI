import React, { useRef, useEffect } from 'react';

const ProgressDashboard = ({ activeAgent, timeline, liveUpdates, streamFileName, streamedCode }) => {
  const codeEndRef = useRef(null);

  useEffect(() => {
    if (codeEndRef.current) {
      codeEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [streamedCode]);

  const getAgentProgress = () => {
    switch(activeAgent) {
      case 'architect': return 25;
      case 'coder': return 65;
      case 'reviewer': return 90;
      case 'ready': return 100;
      default: return 0;
    }
  };

  const getAgentLabel = () => {
    switch(activeAgent) {
      case 'architect': return '🧠 Architect is designing the system...';
      case 'coder': return '⚡ Coder is writing the application...';
      case 'reviewer': return '🔎 Reviewer is analyzing the code...';
      case 'ready': return '✅ Preview Ready';
      default: return 'Initializing...';
    }
  };

  return (
    <div style={{ width: '100%', height: '100%', display: 'flex', flexDirection: 'column', gap: '20px' }}>
      
      {/* Top Level Progress */}
      <div className="cyber-panel" style={{ borderRadius: '12px', padding: '20px', flexShrink: 0 }}>
         <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '10px' }}>
            <h3 style={{ margin: 0, fontWeight: '600', color: 'var(--text-primary)', fontSize: '1.1rem' }}>
              {getAgentLabel()}
            </h3>
            <span style={{ color: 'var(--accent)', fontWeight: 'bold' }}>{getAgentProgress()}%</span>
         </div>
         <div style={{ width: '100%', height: '8px', backgroundColor: '#1a1a1a', borderRadius: '4px', overflow: 'hidden' }}>
            <div style={{ 
               width: `${getAgentProgress()}%`, 
               height: '100%', 
               backgroundColor: 'var(--accent)', 
               transition: 'width 0.5s ease-out',
               boxShadow: '0 0 10px var(--accent)'
            }} />
         </div>
         <div style={{ marginTop: '12px', fontSize: '0.85rem', color: '#888', display: 'flex', justifyContent: 'space-between' }}>
            <span style={{ color: activeAgent === 'architect' ? '#fff' : '#555' }}>1. Planning</span>
            <span style={{ color: activeAgent === 'coder' ? '#fff' : '#555' }}>2. Generating</span>
            <span style={{ color: activeAgent === 'reviewer' ? '#fff' : '#555' }}>3. Reviewing</span>
            <span style={{ color: activeAgent === 'ready' ? '#fff' : '#555' }}>4. Compiling</span>
         </div>
      </div>

      <div style={{ display: 'flex', gap: '20px', flex: 1, minHeight: 0 }}>
         {/* Engineering Reasoning Timeline */}
         <div className="cyber-panel" style={{ flex: 1, borderRadius: '12px', padding: '20px', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
            <h4 style={{ margin: '0 0 15px 0', color: '#aaa', fontSize: '0.9rem', textTransform: 'uppercase', letterSpacing: '1px' }}>Engineering Reasoning Timeline</h4>
            
            <div style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '15px', paddingRight: '10px' }}>
               {timeline.length === 0 && (
                  <div style={{ color: '#555', fontStyle: 'italic', fontSize: '0.9rem' }}>Awaiting initial system architecture...</div>
               )}
               {timeline.map((item, idx) => (
                  <div key={idx} style={{ display: 'flex', gap: '15px', animation: 'fadeIn 0.3s ease-out' }}>
                     <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                        <div className={item.status === 'active' ? 'animate-pulse-glow' : item.status === 'done' ? 'animate-pulse-glow-success' : ''} style={{ 
                           width: '30px', height: '30px', borderRadius: '50%', 
                           backgroundColor: item.status === 'done' ? 'rgba(16, 185, 129, 0.2)' : 'rgba(59, 130, 246, 0.2)',
                           border: item.status === 'done' ? '1px solid #10b981' : '1px solid #3b82f6',
                           display: 'flex', alignItems: 'center', justifyContent: 'center',
                           fontSize: '0.9rem',
                           transition: 'all 0.3s ease'
                        }}>
                           {item.status === 'done' ? '✅' : '⚙️'}
                        </div>
                        {idx < timeline.length - 1 && (
                           <div style={{ width: '2px', flex: 1, backgroundColor: '#333', margin: '4px 0' }} />
                        )}
                     </div>
                     <div style={{ flex: 1, paddingBottom: '15px' }}>
                        <div style={{ fontSize: '0.95rem', fontWeight: '500', color: '#e5e7eb', marginBottom: '4px' }}>{item.title}</div>
                        {item.reason && (
                           <div style={{ fontSize: '0.85rem', color: '#9ca3af', backgroundColor: 'rgba(255,255,255,0.03)', padding: '8px 12px', borderRadius: '6px', borderLeft: '2px solid #555' }}>
                              <span style={{ color: '#6b7280', marginRight: '6px' }}>Reason:</span>
                              {item.reason}
                           </div>
                        )}
                     </div>
                  </div>
               ))}
            </div>
         </div>
         
         {/* Live Code Stream Terminal */}
         <div className="cyber-panel" style={{ flex: 1, borderRadius: '12px', display: 'flex', flexDirection: 'column', overflow: 'hidden', border: '1px solid rgba(16, 185, 129, 0.3)', boxShadow: '0 0 20px rgba(16, 185, 129, 0.05)' }}>
            <div style={{ padding: '12px 20px', backgroundColor: 'rgba(16, 185, 129, 0.1)', borderBottom: '1px solid rgba(16, 185, 129, 0.2)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
               <h4 style={{ margin: 0, color: '#10b981', fontSize: '0.9rem', letterSpacing: '1px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <div className="animate-pulse-glow-success" style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: '#10b981' }} />
                  LIVE CODE STREAM
               </h4>
               <div style={{ fontSize: '0.8rem', color: '#6ee7b7', fontFamily: 'monospace' }}>{streamFileName || 'Awaiting file...'}</div>
            </div>
            <div style={{ flex: 1, overflowY: 'auto', padding: '20px', backgroundColor: '#050505', fontFamily: 'monospace', fontSize: '0.85rem', color: '#a6accd', whiteSpace: 'pre-wrap', lineHeight: '1.5' }}>
               {streamedCode ? streamedCode : <span style={{ color: '#444' }}>Waiting for AI Coder to connect to stream...</span>}
               <div ref={codeEndRef} />
            </div>
         </div>
      </div>
      
      {/* Live System Logs (Small) */}
      {liveUpdates.length > 0 && (
         <div className="animate-slide-up" style={{ backgroundColor: 'rgba(0,0,0,0.6)', padding: '12px 18px', borderRadius: '8px', border: '1px solid rgba(59,130,246,0.2)', fontSize: '0.85rem', color: '#888', fontFamily: 'monospace', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', backdropFilter: 'blur(8px)', boxShadow: '0 4px 12px rgba(0,0,0,0.5)', flexShrink: 0 }}>
            <span style={{ color: '#3b82f6', fontWeight: 'bold' }}>$</span> <span className="typing-cursor" style={{ color: '#ccc' }}>{liveUpdates[liveUpdates.length - 1]}</span>
         </div>
      )}
      
    </div>
  );
};

export default ProgressDashboard;
