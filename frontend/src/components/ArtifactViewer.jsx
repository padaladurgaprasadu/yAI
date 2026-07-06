import React, { useState, useEffect } from 'react';
import { Sandpack } from "@codesandbox/sandpack-react";
import ReactMarkdown from 'react-markdown';
import JSZip from 'jszip';
import { saveAs } from 'file-saver';
import remarkGfm from 'remark-gfm';
import remarkBreaks from 'remark-breaks';
import { motion } from 'framer-motion';
import { ExecutionManager } from './ExecutionManager';

const ArtifactViewer = ({ codeFiles, projectId, isPreviewRunning, API_URL, executionLogs, isBackend, previewUrl }) => {
  const [activeTab, setActiveTab] = useState('preview');
  const [selectedFile, setSelectedFile] = useState(null);
  const [isFullScreen, setIsFullScreen] = useState(false);

  const handleDownload = () => {
    const zip = new JSZip();
    
    // Add all codeFiles to the zip
    Object.entries(codeFiles || {}).forEach(([path, content]) => {
      // Remove leading slash if present
      const cleanPath = path.startsWith('/') ? path.substring(1) : path;
      zip.file(cleanPath, content);
    });
    
    zip.generateAsync({ type: 'blob' }).then(blob => {
      saveAs(blob, `aion_project_${projectId || 'download'}.zip`);
    });
  };

  // Set the initial selected file
  useEffect(() => {
    if (codeFiles && Object.keys(codeFiles).length > 0 && !selectedFile) {
      setSelectedFile(Object.keys(codeFiles)[0]);
    }
  }, [codeFiles, selectedFile]);

  const sandpackFiles = {
    "/index.html": `<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>AiON Preview</title>
    <script src="https://cdn.tailwindcss.com"></script>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.jsx"></script>
  </body>
</html>`,
    "/src/main.jsx": `import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.jsx'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)`,
    "/src/index.css": `@tailwind base;\n@tailwind components;\n@tailwind utilities;`,
    "/vite.config.js": `import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: { port: 3000 }
});`
  };
  
  let dynamicDependencies = {
    "lucide-react": "latest",
    "recharts": "latest",
    "react-router-dom": "latest",
    "framer-motion": "latest",
    "axios": "latest"
  };
  
  if (codeFiles) {
    const pkgFiles = Object.keys(codeFiles).filter(f => f.endsWith('package.json') && f.includes('client'));
    if (pkgFiles.length > 0) {
      try {
        const pkgData = JSON.parse(codeFiles[pkgFiles[0]]);
        if (pkgData.dependencies) {
          Object.keys(pkgData.dependencies).forEach(dep => {
              // Sandbox-safe filter: Remove @types, node internals, backend drivers, and common Python/ML hallucinations
              const blacklist = ['react', 'react-dom', 'pg', 'redis', 'kubernetes', 'docker', 'mongoose', 'express', 'apollo-server', 'apollo-server-express', 'server', 'client', 'ts-node', 'nodemon', 'tensorflow', 'opencv', 'pandas', 'numpy', 'pytorch', 'scikit-learn', 'flask', 'django', 'fastapi', 'keras', 'matplotlib', 'seaborn'];
              if (!dep.startsWith('@types/') && !blacklist.includes(dep) && !dep.startsWith('vite')) {
                  dynamicDependencies[dep] = pkgData.dependencies[dep];
              }
          });
        }
      } catch (e) {
        console.warn("Failed to parse package.json");
      }
    }
    const isMonorepo = Object.keys(codeFiles).some(path => path.includes('client/') || path.includes('server/'));

    Object.entries(codeFiles).forEach(([filePath, content]) => {
       let sandpackPath = filePath.startsWith('/') ? filePath : '/' + filePath;
       // If it's a fullstack project, isolate only the frontend for Sandpack preview
       if (isMonorepo) {
           if (sandpackPath.startsWith('/client/')) {
               sandpackPath = sandpackPath.replace('/client', '');
           } else if (sandpackPath.startsWith('/server/')) {
               return; // Skip backend files
           }
       }
       
       // NEVER inject the AI's package.json into Sandpack. 
       // This forces Sandpack to use its flawless default vite-react package.json.
       if (sandpackPath === '/package.json' || sandpackPath === '/client/package.json') {
           return;
       }
       
       // Ensure App is always .jsx for Vite compatibility
       if (sandpackPath === '/src/App.js') sandpackPath = '/src/App.jsx';
       
       let finalContent = content;
       
       sandpackFiles[sandpackPath] = finalContent;
       
       // AUTO-DETECT DEPENDENCIES FOR SANDPACK
       const isJsLike = /\.(js|jsx|ts|tsx)$/.test(filePath);
       if (isJsLike) {
          const importRegex = /import\s+[\s\S]*?\s+from\s+['"]([^'"]+)['"]/g;
          const bareImportRegex = /import\s+['"]([^'"]+)['"]/g;
          
          for (const regex of [importRegex, bareImportRegex]) {
            let match;
            while ((match = regex.exec(content)) !== null) {
                let pkgName = match[1];
                if (!pkgName.startsWith('.') && !pkgName.startsWith('/')) {
                    if (pkgName.startsWith('@')) {
                        const parts = pkgName.split('/');
                        if (parts.length >= 2) pkgName = `${parts[0]}/${parts[1]}`;
                    } else {
                        pkgName = pkgName.split('/')[0];
                    }
                    
                    // Ignore built-in React, @types, and common Node built-ins, and ML hallucinations
                    const blacklist = ['react', 'react-dom', 'pg', 'redis', 'kubernetes', 'docker', 'mongoose', 'express', 'apollo-server', 'apollo-server-express', 'server', 'client', 'ts-node', 'nodemon', 'tensorflow', 'opencv', 'pandas', 'numpy', 'pytorch', 'scikit-learn', 'flask', 'django', 'fastapi', 'keras', 'matplotlib', 'seaborn'];
                    const isBlacklisted = blacklist.includes(pkgName);
                    
                    if (
                        !isBlacklisted && 
                        !pkgName.startsWith('@types/') &&
                        !['fs', 'path', 'crypto', 'os', 'http', 'https', 'stream', 'events', 'util', 'url'].includes(pkgName)
                    ) {
                        if (!dynamicDependencies[pkgName]) {
                            dynamicDependencies[pkgName] = "latest";
                        }
                    }
                }
            }
          }
       }
    });
  }

  function validateClosure(files) {
    const missing = [];
    const filePaths = new Set(Object.keys(files));

    Object.entries(files).forEach(([path, content]) => {
      if (typeof content !== 'string') return;
      const importRegex = /from\s+['"](\.[^'"]+)['"]/g;
      let match;
      while ((match = importRegex.exec(content)) !== null) {
        const dir = path.substring(0, path.lastIndexOf('/')) || '';
        let resolved;
        try {
          resolved = new URL(match[1], `file:///${dir.replace(/^\//, '')}/`).pathname;
          // Ensure it starts with / for Sandpack paths
          if (!resolved.startsWith('/')) resolved = '/' + resolved;
        } catch {
          continue;
        }
        const candidates = [
          resolved, resolved + '.js', resolved + '.jsx',
          resolved + '.ts', resolved + '.tsx', resolved + '/index.js',
          resolved + '.css'
        ];
        if (!candidates.some(c => filePaths.has(c))) {
          missing.push({ file: path, import: match[1] });
        }
      }
    });

    return missing;
  }

  const missingImports = validateClosure(sandpackFiles);

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      ...(isFullScreen ? {
        position: 'fixed',
        top: 0,
        left: 0,
        width: '100vw',
        height: '100vh',
        zIndex: 9999,
        borderRadius: 0,
        animation: 'none'
      } : {
        height: '100%',
        borderRadius: '16px',
        animation: 'slideInRight 0.5s cubic-bezier(0.2, 0.8, 0.2, 1)'
      }),
      backgroundColor: '#0a0a0a',
      border: '1px solid #2a2a2a',
      overflow: 'hidden',
      boxShadow: '0 20px 40px rgba(0,0,0,0.4)'
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
        
        <div style={{ position: 'absolute', right: '20px', top: '16px', display: 'flex', gap: '10px' }}>
            <button 
                onClick={() => setIsFullScreen(!isFullScreen)}
                style={{ 
                    padding: '8px 16px', 
                    borderRadius: '8px', 
                    fontSize: '0.85rem', 
                    fontWeight: 'bold', 
                    border: '1px solid #444', 
                    cursor: 'pointer', 
                    background: '#222', 
                    color: '#fff',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px',
                    transition: 'all 0.2s'
                }}
                onMouseEnter={(e) => e.currentTarget.style.background = '#333'}
                onMouseLeave={(e) => e.currentTarget.style.background = '#222'}
            >
                {isFullScreen ? '↙ Exit Independent Mode' : '↗ Independent Preview'}
            </button>
            <button 
                onClick={handleDownload} 
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
                      padding: '8px 15px',
                      cursor: 'pointer',
                      fontSize: '0.80rem',
                      color: selectedFile === path ? '#fff' : '#aaa',
                      backgroundColor: selectedFile === path ? '#222' : 'transparent',
                      borderLeft: selectedFile === path ? '3px solid #3b82f6' : '3px solid transparent',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '8px',
                      wordBreak: 'break-all'
                    }}
                    title={path}
                  >
                    📄 {path}
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

        {/* EXECUTION MANAGER (Preview + WebContainer Terminal) */}
        {(activeTab === 'preview' || activeTab === 'terminal') && (
            missingImports.length > 0 ? (
              <div style={{ padding: 20, color: '#ef4444', fontFamily: 'monospace', height: '100%', backgroundColor: '#000', overflow: 'auto' }}>
                <strong style={{ fontSize: '1.1em', display: 'block', marginBottom: '10px' }}>[AiON] Generation incomplete — {missingImports.length} file(s) missing:</strong>
                <ul style={{ listStyleType: 'none', padding: 0 }}>
                  {missingImports.map((m, i) => (
                    <li key={i} style={{ marginBottom: '8px', padding: '10px', backgroundColor: '#1a0000', border: '1px solid #330000', borderRadius: '4px' }}>
                      <span style={{ color: '#aaa' }}>{m.file}</span> imports <strong style={{ color: '#ff6b6b' }}>"{m.import}"</strong> — file not found
                    </li>
                  ))}
                </ul>
              </div>
            ) : (
              <ExecutionManager 
                  files={sandpackFiles}
                  dynamicDependencies={dynamicDependencies}
                  activeTab={activeTab}
                  isBackend={isBackend}
                  previewUrl={previewUrl}
                  projectId={projectId}
              />
            )
        )}

      </div>
    </div>
  );
};

export default ArtifactViewer;
