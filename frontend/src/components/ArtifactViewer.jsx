import React, { useState, useEffect, useRef } from 'react';
import { Sandpack } from "@codesandbox/sandpack-react";
import ReactMarkdown from 'react-markdown';
import JSZip from 'jszip';
import { saveAs } from 'file-saver';
import remarkGfm from 'remark-gfm';
import remarkBreaks from 'remark-breaks';
import { motion } from 'framer-motion';
import { ExecutionManager } from './ExecutionManager';
import Editor from '@monaco-editor/react';

const ArtifactViewer = ({ codeFiles, setCodeFiles, projectId, isPreviewRunning, API_URL, executionLogs, isBackend, previewUrl, previewError }) => {
  const [activeTab, setActiveTab] = useState('preview');
  const [selectedFile, setSelectedFile] = useState(null);
  const [isFullScreen, setIsFullScreen] = useState(false);
  
  const saveTimeoutRef = useRef(null);
  const [saveStatus, setSaveStatus] = useState("idle"); // "idle", "saving", "saved", "error"
  const [rebuildStatus, setRebuildStatus] = useState("idle"); // "idle", "rebuilding", "success", "error"

  const getFileLanguage = (filename) => {
    if (!filename) return 'javascript';
    const ext = filename.split('.').pop().toLowerCase();
    switch (ext) {
      case 'js':
      case 'jsx':
        return 'javascript';
      case 'ts':
      case 'tsx':
        return 'typescript';
      case 'html':
        return 'html';
      case 'css':
        return 'css';
      case 'json':
        return 'json';
      case 'py':
        return 'python';
      case 'sh':
        return 'shell';
      case 'md':
        return 'markdown';
      default:
        return 'javascript';
    }
  };

  const saveFileToDisk = (path, content) => {
    setSaveStatus("saving");
    if (saveTimeoutRef.current) {
      clearTimeout(saveTimeoutRef.current);
    }
    
    saveTimeoutRef.current = setTimeout(async () => {
      try {
        const response = await fetch(`${API_URL}/api/write-file/${projectId}`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json"
          },
          body: JSON.stringify({ path, content })
        });
        
        if (response.ok) {
          setSaveStatus("saved");
          setTimeout(() => setSaveStatus("idle"), 2000);
        } else {
          setSaveStatus("error");
        }
      } catch (err) {
        console.error("Failed to save file to disk:", err);
        setSaveStatus("error");
      }
    }, 1000);
  };

  const handleEditorChange = (value) => {
    if (!selectedFile || !setCodeFiles) return;
    setCodeFiles(prev => ({
      ...prev,
      [selectedFile]: value
    }));
    saveFileToDisk(selectedFile, value);
  };

  const handleRebuildPreview = async () => {
    setRebuildStatus("rebuilding");
    try {
      const endpoint = isBackend ? "restart-sandbox" : "start-preview";
      const response = await fetch(`${API_URL}/api/${endpoint}/${projectId}`, {
        method: "POST"
      });
      if (response.ok) {
        setRebuildStatus("success");
        setTimeout(() => setRebuildStatus("idle"), 2000);
      } else {
        setRebuildStatus("error");
      }
    } catch (err) {
      console.error("Rebuild failed:", err);
      setRebuildStatus("error");
    }
  };

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
    <title>yAI Preview</title>
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

  function generateStub(importPath) {
    // Guess a reasonable name from the path, e.g. "../contexts/AuthContext" -> "Auth"
    const fileName = importPath.split('/').pop(); // "AuthContext"
    const baseName = fileName.replace(/Context$/, ''); // "Auth"

    // Heuristic: if it looks like a React Context (common Coder-agent pattern), stub a real one
    if (fileName.endsWith('Context')) {
      const isAuth = fileName === 'AuthContext';
      const defaultState = isAuth 
        ? `{ user: { id: 'demo-user', name: 'Demo User', email: 'demo@aion.dev' }, isAuthenticated: true }` 
        : `{}`;

      return `import React, { createContext, useContext, useState } from 'react';

const ${fileName} = createContext(null);

export const ${baseName}Provider = ({ children }) => {
  const [state, setState] = useState(${defaultState});
  return (
    <${fileName}.Provider value={{ ...state, setState }}>
      {children}
    </${fileName}.Provider>
  );
};

export const use${baseName} = () => useContext(${fileName});
export default ${fileName};
`;
    }

    // Generic fallback: a no-op component stub
    return `import React from 'react';
export default function ${baseName}() {
  return null;
}
export const ${baseName} = () => null;
`;
  }

  function autoStubMissingFiles(files, missingImports) {
    const stubbedFiles = { ...files };
    return { stubbedFiles: {} };
  }

  const missingImports = validateClosure(sandpackFiles);

  let finalFiles = sandpackFiles;
  let stubbedFiles = {};
  if (codeFiles) {
    const result = analyzeImports(codeFiles);
    stubbedFiles = result.stubbedFiles || {};
  }

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
              <div style={{ 
                padding: '8px 20px', 
                borderBottom: '1px solid #1a1a1a', 
                color: '#888', 
                fontSize: '0.85rem', 
                fontFamily: 'monospace',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                backgroundColor: '#111'
              }}>
                <span style={{ fontWeight: '500' }}>{selectedFile}</span>
                <div style={{ display: 'flex', alignItems: 'center', gap: '15px' }}>
                  {/* Status Indicator */}
                  <span style={{ 
                    fontSize: '0.75rem', 
                    color: saveStatus === 'saving' ? '#fbbf24' : saveStatus === 'saved' ? '#34d399' : saveStatus === 'error' ? '#f87171' : '#666' 
                  }}>
                    {saveStatus === 'saving' ? '● Saving to disk...' : saveStatus === 'saved' ? '✔ Saved' : saveStatus === 'error' ? '✖ Save failed' : ''}
                  </span>
                  
                  {/* Rebuild Trigger */}
                  <button
                    onClick={handleRebuildPreview}
                    disabled={rebuildStatus === 'rebuilding'}
                    style={{
                      padding: '4px 10px',
                      borderRadius: '4px',
                      border: '1px solid #333',
                      backgroundColor: rebuildStatus === 'rebuilding' ? '#222' : '#1e3a8a',
                      color: rebuildStatus === 'rebuilding' ? '#888' : '#60a5fa',
                      cursor: rebuildStatus === 'rebuilding' ? 'not-allowed' : 'pointer',
                      fontSize: '0.75rem',
                      fontWeight: '500',
                      transition: 'all 0.2s'
                    }}
                  >
                    {rebuildStatus === 'rebuilding' ? 'Rebuilding...' : isBackend ? '🔄 Restart Server' : '🚀 Rebuild Preview'}
                  </button>
                </div>
              </div>
              <div style={{ flex: 1, overflow: 'hidden' }}>
                {selectedFile && codeFiles ? (
                  <Editor
                    height="100%"
                    theme="vs-dark"
                    language={getFileLanguage(selectedFile)}
                    value={codeFiles[selectedFile] || ''}
                    onChange={handleEditorChange}
                    options={{
                      fontSize: 14,
                      minimap: { enabled: true },
                      automaticLayout: true,
                      tabSize: 2,
                      scrollBeyondLastLine: false,
                      lineNumbers: 'on',
                      wordWrap: 'on'
                    }}
                  />
                ) : (
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: '#666', fontSize: '0.9rem' }}>
                    Select a file from the explorer to view/edit code.
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* EXECUTION MANAGER (Preview + WebContainer Terminal) */}
        {(activeTab === 'preview' || activeTab === 'terminal') && (
            <div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
              {/* Backend now guarantees completeness; removed placeholder warning banner */}
              <div style={{ flex: 1 }}>
                <ExecutionManager 
                    files={finalFiles}
                    dynamicDependencies={dynamicDependencies}
                    activeTab={activeTab}
                    isBackend={isBackend}
                    previewUrl={previewUrl}
                    previewError={previewError}
                    projectId={projectId}
                    hasFrontendFiles={codeFiles && Object.keys(codeFiles).some(f => f.includes('client/') || f.includes('src/') || f.endsWith('.jsx') || f.endsWith('.html'))}
                />
              </div>
            </div>
        )}

      </div>
    </div>
  );
};

export default ArtifactViewer;
