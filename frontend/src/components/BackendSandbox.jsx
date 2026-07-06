import React, { useState, useEffect, useRef } from 'react';

export const BackendSandbox = ({ activeTab, previewUrl, projectId }) => {
  const [logs, setLogs] = useState([]);
  const logsEndRef = useRef(null);

  useEffect(() => {
    if (!projectId) return;
    
    // Auto-detect the backend URL instead of hardcoding localhost
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.hostname === 'localhost' ? 'localhost:10000' : window.location.host;
    const wsUrl = `${protocol}//${host}/api/ws/sandbox/${projectId}`;
    
    const ws = new WebSocket(wsUrl);
    
    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        if (msg.type === 'log') {
          setLogs(prev => [...prev, msg.data]);
        } else if (msg.type === 'error') {
          setLogs(prev => [...prev, `[AiON Error] ${msg.message}\n`]);
        }
      } catch (e) {
        setLogs(prev => [...prev, event.data + '\n']);
      }
    };
    
    ws.onerror = () => {
       setLogs(prev => [...prev, '[AiON Sandbox] Failed to connect to log stream.\n']);
    };
    
    return () => ws.close();
  }, [projectId]);

  useEffect(() => {
    if (logsEndRef.current) {
      logsEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [logs]);

  return (
    <div style={{ width: '100%', height: '100%', display: 'flex', flexDirection: 'column' }}>
      
      {/* PREVIEW TAB */}
      <div style={{ display: activeTab === 'preview' ? 'block' : 'none', height: '100%', width: '100%' }}>
        {previewUrl ? (
          <iframe 
            src={previewUrl} 
            style={{ width: '100%', height: 'calc(100dvh - 120px)', border: 'none', backgroundColor: '#fff' }}
            title="Backend Preview"
            sandbox="allow-forms allow-modals allow-popups allow-presentation allow-same-origin allow-scripts"
          />
        ) : (
          <div style={{ padding: '20px', color: '#10b981', fontFamily: 'monospace', display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%' }}>
            [AiON DevOps] Booting up native backend Sandbox...
          </div>
        )}
      </div>

      {/* TERMINAL TAB */}
      <div style={{ display: activeTab === 'terminal' ? 'flex' : 'none', flexDirection: 'column', height: '100%', width: '100%' }}>
         <div style={{ padding: '12px 20px', borderBottom: '1px solid #222', color: '#888', fontSize: '0.85rem', display: 'flex', justifyContent: 'space-between', backgroundColor: '#000' }}>
             <span>AiON Native Execution Logs (Host Process)</span>
             <span style={{ color: '#10b981' }}>● Live</span>
         </div>
         <div style={{ flex: 1, overflow: 'auto', backgroundColor: '#000', padding: '10px', color: '#a6accd', fontFamily: 'monospace', fontSize: '13px', whiteSpace: 'pre-wrap' }}>
           {logs.map((log, i) => <span key={i}>{log}</span>)}
           <div ref={logsEndRef} />
         </div>
      </div>
      
    </div>
  );
};
