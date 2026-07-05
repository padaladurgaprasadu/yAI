import React, { useState, useEffect } from 'react';
import { Sandpack } from "@codesandbox/sandpack-react";

const ArtifactViewer = ({ codeFiles, projectId, isPreviewRunning, API_URL, executionLogs }) => {
  const [activeTab, setActiveTab] = useState('preview');
  const [selectedFile, setSelectedFile] = useState(null);

  // Set the initial selected file
  useEffect(() => {
    if (codeFiles && Object.keys(codeFiles).length > 0 && !selectedFile) {
      setSelectedFile(Object.keys(codeFiles)[0]);
    }
  }, [codeFiles, selectedFile]);

  // Format files for Sandpack
  const sandpackFiles = {};
  let hasIndexCss = false;
  let dynamicDependencies = {
    "lucide-react": "^0.263.1",
    "react-router-dom": "^6.22.3" // Fallback defaults
  };
  
  if (codeFiles) {
    // Attempt to extract dynamic dependencies from package.json
    const pkgFiles = Object.keys(codeFiles).filter(f => f.endsWith('package.json'));
    if (pkgFiles.length > 0) {
      try {
        const pkgData = JSON.parse(codeFiles[pkgFiles[0]]);
        if (pkgData.dependencies) {
          dynamicDependencies = { ...dynamicDependencies, ...pkgData.dependencies };
          
          // CRITICAL FIX: Sandpack crashes if we override its internal React bindings
          delete dynamicDependencies['react'];
          delete dynamicDependencies['react-dom'];
          delete dynamicDependencies['react-scripts'];
        }
      } catch (e) {
        console.warn("Failed to parse package.json for dynamic dependencies");
      }
    }

    Object.entries(codeFiles).forEach(([filePath, content]) => {
       if (filePath.startsWith('client/src/')) {
          // Map Vite src folder to Sandpack root
          let sandpackPath = filePath.replace('client/src/', '/');
          
          // Overwrite Sandpack's default App.js to avoid "Hello world" conflicts
          if (sandpackPath === '/App.jsx' || sandpackPath === '/App.js') {
             sandpackPath = '/App.js';
          }
          
          sandpackFiles[sandpackPath] = content;
          if (sandpackPath === '/index.css') hasIndexCss = true;
       } else if (filePath.startsWith('client/')) {
          // Map other files (if any) to root
          const sandpackPath = filePath.replace('client/', '/');
          sandpackFiles[sandpackPath] = content;
       }
       
       // AUTO-DETECT DEPENDENCIES FOR SANDPACK
       if (filePath.endsWith('.js') || filePath.endsWith('.jsx')) {
          const importRegex = /import\s+.*?\s+from\s+['"]([^'"]+)['"]/g;
          const requireRegex = /require\(['"]([^'"]+)['"]\)/g;
          
          const extractPackages = (regex) => {
              let match;
              while ((match = regex.exec(content)) !== null) {
                  let pkgName = match[1];
                  // Ignore relative/absolute imports
                  if (!pkgName.startsWith('.') && !pkgName.startsWith('/')) {
                      // Extract base package (handle scoped packages like @mui/material)
                      if (pkgName.startsWith('@')) {
                          const parts = pkgName.split('/');
                          if (parts.length >= 2) pkgName = `${parts[0]}/${parts[1]}`;
                      } else {
                          pkgName = pkgName.split('/')[0];
                      }
                      
                      // Ignore Sandpack builtins
                      if (pkgName !== 'react' && pkgName !== 'react-dom' && pkgName !== 'react-scripts') {
                          if (!dynamicDependencies[pkgName]) {
                              dynamicDependencies[pkgName] = "latest";
                          }
                      }
                  }
              }
          };
          
          extractPackages(importRegex);
          extractPackages(requireRegex);
       }
    });
  }
  
  // Override Sandpack's default entry point to link to the AI generated App.jsx
  sandpackFiles["/index.js"] = `
import React, { StrictMode } from "react";
import { createRoot } from "react-dom/client";
${hasIndexCss ? 'import "./index.css";' : ''}
import App from "./App";

const root = createRoot(document.getElementById("root"));
root.render(
  <StrictMode>
    <App />
  </StrictMode>
);
`;

  // Inject Tailwind CSS via CDN for instant styling support
  sandpackFiles["/public/index.html"] = `
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>AiON App</title>
    <script src="https://cdn.tailwindcss.com"></script>
  </head>
  <body>
    <noscript>You need to enable JavaScript to run this app.</noscript>
    <div id="root"></div>
  </body>
</html>
  `;

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
          <div style={{ width: '100%', height: '100%', backgroundColor: '#151515', position: 'relative' }}>
            <Sandpack 
              template="react" 
              theme="dark"
              files={sandpackFiles}
              options={{
                showNavigator: true,
                showTabs: false,
                editorHeight: 'calc(100dvh - 120px)',
                editorWidthPercentage: 0,
                autoHiddenFiles: true
              }}
              customSetup={{
                dependencies: dynamicDependencies
              }}
            />
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
