import React, { useState, useEffect } from 'react';

const ArtifactViewer = ({ codeFiles, projectId, isPreviewRunning, API_URL, executionLogs }) => {
  const [activeTab, setActiveTab] = useState('preview');
  const [selectedFile, setSelectedFile] = useState(null);

  // Set the initial selected file
  useEffect(() => {
    if (codeFiles && Object.keys(codeFiles).length > 0 && !selectedFile) {
      setSelectedFile(Object.keys(codeFiles)[0]);
    }
  }, [codeFiles, selectedFile]);

  const previewUrl = `${API_URL}/live/${projectId}/index.html`;

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      height: '100%',
      backgroundColor: '#0a0a0a',
      borderRadius: '16px',
      border: '1px solid #2a2a2a',
      overflow: 'hidden',
      boxShadow: '0 20px 40px rgba(0,0,0,0.4)',
      animation: 'slideInRight 0.5s cubic-bezier(0.2, 0.8, 0.2, 1)'
    }}>
      {/* Sleek Tab Bar */}
      <div style={{
        display: 'flex',
        justifyContent: 'center',
        padding: '12px 20px',
        backgroundColor: '#111',
        borderBottom: '1px solid #2a2a2a',
        position: 'relative'
      }}>
        <div style={{
          display: 'flex',
          backgroundColor: '#1e1e1e',
          borderRadius: '8px',
          padding: '4px',
          gap: '4px'
        }}>
          <button
            onClick={() => setActiveTab('code')}
            style={{
              padding: '8px 24px',
              borderRadius: '6px',
              border: 'none',
              background: activeTab === 'code' ? '#2a2a2a' : 'transparent',
              color: activeTab === 'code' ? '#fff' : '#888',
              fontSize: '0.9rem',
              fontWeight: '500',
              cursor: 'pointer',
              transition: 'all 0.2s',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              boxShadow: activeTab === 'code' ? '0 2px 8px rgba(0,0,0,0.2)' : 'none'
            }}
          >
            <span style={{ color: '#4ade80' }}>⚛️</span> Code
          </button>
          <button
            onClick={() => setActiveTab('preview')}
            style={{
              padding: '8px 24px',
              borderRadius: '6px',
              border: 'none',
              background: activeTab === 'preview' ? '#2a2a2a' : 'transparent',
              color: activeTab === 'preview' ? '#fff' : '#888',
              fontSize: '0.9rem',
              fontWeight: '500',
              cursor: 'pointer',
              transition: 'all 0.2s',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              boxShadow: activeTab === 'preview' ? '0 2px 8px rgba(0,0,0,0.2)' : 'none'
            }}
          >
            <span style={{ color: '#60a5fa' }}>🌐</span> Preview
          </button>
          <button
            onClick={() => setActiveTab('terminal')}
            style={{
              padding: '8px 24px',
              borderRadius: '6px',
              border: 'none',
              background: activeTab === 'terminal' ? '#2a2a2a' : 'transparent',
              color: activeTab === 'terminal' ? '#fff' : '#888',
              fontSize: '0.9rem',
              fontWeight: '500',
              cursor: 'pointer',
              transition: 'all 0.2s',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              boxShadow: activeTab === 'terminal' ? '0 2px 8px rgba(0,0,0,0.2)' : 'none'
            }}
          >
            <span style={{ color: '#f59e0b' }}>🖥️</span> Terminal
          </button>
        </div>
        
        <div style={{ position: 'absolute', right: '20px', top: '16px' }}>
            <button 
                onClick={() => window.location.href = `${API_URL}/api/download?project_id=${projectId}`} 
                style={{ 
                    padding: '8px 16px', 
                    borderRadius: '8px', 
                    fontSize: '0.85rem', 
                    fontWeight: 'bold', 
                    border: 'none', 
                    cursor: 'pointer', 
                    background: 'linear-gradient(135deg, #3b82f6, #2563eb)', 
                    color: '#fff',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px',
                    transition: 'transform 0.2s, box-shadow 0.2s'
                }}
                onMouseEnter={(e) => e.currentTarget.style.boxShadow = '0 0 15px rgba(59, 130, 246, 0.4)'}
                onMouseLeave={(e) => e.currentTarget.style.boxShadow = 'none'}
            >
                ↓ Download
            </button>
        </div>
      </div>

      {/* Content Area */}
      <div style={{ flex: 1, overflow: 'hidden', position: 'relative' }}>
        
        {/* CODE TAB */}
        {activeTab === 'code' && (
          <div style={{ display: 'flex', height: '100%' }}>
            {/* File Explorer */}
            <div style={{ 
              width: '250px', 
              backgroundColor: '#111', 
              borderRight: '1px solid #2a2a2a',
              display: 'flex',
              flexDirection: 'column'
            }}>
              <div style={{ padding: '15px', fontSize: '0.8rem', fontWeight: 'bold', color: '#666', textTransform: 'uppercase', letterSpacing: '1px' }}>
                Files
              </div>
              <div style={{ flex: 1, overflowY: 'auto' }}>
                {codeFiles && Object.keys(codeFiles).map(path => (
                  <div 
                    key={path}
                    onClick={() => setSelectedFile(path)}
                    style={{
                      padding: '10px 15px',
                      fontSize: '0.85rem',
                      color: selectedFile === path ? '#fff' : '#aaa',
                      backgroundColor: selectedFile === path ? 'rgba(59, 130, 246, 0.1)' : 'transparent',
                      borderLeft: selectedFile === path ? '3px solid #3b82f6' : '3px solid transparent',
                      cursor: 'pointer',
                      fontFamily: 'monospace',
                      whiteSpace: 'nowrap',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis'
                    }}
                    title={path}
                  >
                    📄 {path.split('/').pop()}
                  </div>
                ))}
              </div>
            </div>
            
            {/* Code Editor View */}
            <div style={{ flex: 1, backgroundColor: '#0d0d0d', overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
              <div style={{ padding: '12px 20px', borderBottom: '1px solid #1a1a1a', color: '#888', fontSize: '0.85rem', fontFamily: 'monospace' }}>
                {selectedFile}
              </div>
              <div style={{ flex: 1, overflow: 'auto', padding: '20px' }}>
                <pre style={{ margin: 0, color: '#a6accd', fontFamily: 'monospace', fontSize: '0.9rem', lineHeight: '1.6' }}>
                  {codeFiles && selectedFile ? codeFiles[selectedFile] : ''}
                </pre>
              </div>
            </div>
          </div>
        )}

        {/* PREVIEW TAB */}
        {activeTab === 'preview' && (
          <div style={{ width: '100%', height: '100%', backgroundColor: '#fff', position: 'relative' }}>
            {isPreviewRunning ? (
              <iframe 
                src={previewUrl} 
                style={{ width: '100%', height: '100%', border: 'none', backgroundColor: '#fff' }}
                title="Live Preview"
              />
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%', color: '#666', backgroundColor: '#f9fafb' }}>
                <div style={{ width: '40px', height: '40px', border: '3px solid #e5e7eb', borderTopColor: '#3b82f6', borderRadius: '50%', animation: 'spin 1s linear infinite', marginBottom: '16px' }}></div>
                <p>Compiling Live Preview...</p>
              </div>
            )}
            
            {/* Floating Browser Bar Mockup */}
            <div style={{ 
              position: 'absolute', 
              top: '20px', 
              left: '50%', 
              transform: 'translateX(-50%)', 
              backgroundColor: 'rgba(255, 255, 255, 0.9)', 
              backdropFilter: 'blur(10px)',
              padding: '8px 16px', 
              borderRadius: '20px',
              border: '1px solid #e5e7eb',
              boxShadow: '0 4px 15px rgba(0,0,0,0.1)',
              display: 'flex',
              alignItems: 'center',
              gap: '12px',
              fontSize: '0.85rem',
              color: '#4b5563',
              zIndex: 10,
              pointerEvents: 'none'
            }}>
              <span style={{ color: '#10b981' }}>🔒</span>
              <span style={{ fontFamily: 'monospace' }}>{previewUrl.split('://')[1]?.split('/')[0] || 'localhost'}/live</span>
            </div>
          </div>
        )}

        {/* TERMINAL TAB */}
        {activeTab === 'terminal' && (
          <div style={{ flex: 1, backgroundColor: '#000', overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
            <div style={{ padding: '12px 20px', borderBottom: '1px solid #222', color: '#888', fontSize: '0.85rem', display: 'flex', justifyContent: 'space-between' }}>
               <span>Executor Agent Logs</span>
               <span style={{ color: '#10b981' }}>● Live</span>
            </div>
            <div style={{ flex: 1, overflow: 'auto', padding: '20px', display: 'flex', flexDirection: 'column-reverse' }}>
               <pre style={{ margin: 0, color: '#a6accd', fontFamily: 'monospace', fontSize: '0.9rem', lineHeight: '1.6', whiteSpace: 'pre-wrap' }}>
                 {/* Determine the props name based on what we passed in App.jsx */}
                 {/* App.jsx passes executionLogs={executionLogs} */}
                 {/* But we forgot to destructure it in ArtifactViewer parameters! Let's do that next */}
                 {executionLogs && executionLogs.length > 0 
                    ? executionLogs.join('\n') 
                    : "> Waiting for execution logs...\n"}
               </pre>
            </div>
          </div>
        )}

      </div>
    </div>
  );
};

export default ArtifactViewer;
