import React, { useEffect, useState, useCallback } from 'react';
import { BackendSandbox } from './BackendSandbox';
import {
  SandpackProvider,
  SandpackLayout,
  SandpackPreview,
  useSandpack,
  SandpackConsole
} from "@codesandbox/sandpack-react";
import BuildStatus from './BuildStatus';

const ExecutionLifecycle = ({ activeTab, onCrash }) => {
  const { sandpack, listen } = useSandpack();
  const [restarting, setRestarting] = useState(false);
  const [retryCount, setRetryCount] = useState(0);
  const [runtimeError, setRuntimeError] = useState(null);
  const [isHealing, setIsHealing] = useState(false);

  const triggerRecovery = useCallback((reason) => {
    if (retryCount >= 3) {
      console.error(`[yAI DevOps] Max auto-recovery attempts reached. Failed to recover from: ${reason}`);
      return;
    }
    console.warn(`[yAI DevOps] Intercepted infrastructure crash (${reason}), attempting hard reboot... Attempt ${retryCount + 1}/3`);
    setRestarting(true);
    setRetryCount(prev => prev + 1);
    
    // Trigger hard unmount in parent
    setTimeout(() => {
       onCrash();
    }, 1500);
  }, [retryCount, onCrash]);

  // Listen to iframe raw messages for fatal server crashes
  useEffect(() => {
    const unsubscribe = listen((msg) => {
      // Catch "Server has crashed with status code 1" overlay
      if (msg.type === 'action' && msg.action === 'show-error') {
         const text = (msg.title || '') + ' ' + (msg.message || '');
         if (text.includes('status code 1') || text.includes('Failed to get shell') || text.includes('crashed')) {
            triggerRecovery(text);
         }
      }
      // Removed server-error hard reboot because it causes grey sad faces on simple Vite errors.
    });
    return unsubscribe;
  }, [listen, triggerRecovery]);

  // Also check standard sandpack.error state
  useEffect(() => {
    if (!sandpack || !sandpack.error) {
       setRuntimeError(null);
       return;
    }
    const errorMsg = typeof sandpack.error === 'string' ? sandpack.error : (sandpack.error.message || '');
    if (
      errorMsg.includes('Failed to get shell by ID') || 
      errorMsg.includes('status code 1') ||
      errorMsg.includes('timeout') ||
      errorMsg.includes('Server has crashed')
    ) {
      triggerRecovery(errorMsg);
    } else {
      setRuntimeError(errorMsg);
    }
  }, [sandpack.error, triggerRecovery]);

  return (
    <>
      <div style={{ display: activeTab === 'preview' ? 'block' : 'none', height: '100%', width: '100%' }}>
        {restarting ? (
          <div style={{ padding: '20px', color: '#10b981', fontFamily: 'monospace', display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%' }}>
            [yAI DevOps] Hard Rebooting WebContainer...
          </div>
        ) : (
          <div style={{ position: 'relative', height: '100%' }}>
            <SandpackPreview 
              style={{ height: 'calc(100dvh - 120px)' }} 
              showNavigator={true} 
              showRefreshButton={true}
              showSandpackErrorOverlay={false}
            />
            {runtimeError && (
               <div className="animate-slide-up cyber-panel" style={{ position: 'absolute', bottom: '20px', left: '20px', right: '20px', padding: '20px', borderRadius: '12px', zIndex: 9999, border: '1px solid rgba(239, 68, 68, 0.5)' }}>
                  <h3 style={{ color: '#ef4444', margin: '0 0 10px 0', display: 'flex', alignItems: 'center', gap: '10px' }}>
                     ⚠️ Sandbox Runtime Error
                  </h3>
                  <div style={{ fontFamily: 'monospace', fontSize: '0.85rem', color: '#fca5a5', marginBottom: '15px', maxHeight: '100px', overflowY: 'auto' }}>
                     {runtimeError}
                  </div>
                  <button 
                     className={isHealing ? "animate-pulse-glow" : ""}
                     onClick={() => {
                        setIsHealing(true);
                        setTimeout(() => {
                           setIsHealing(false);
                           setRuntimeError(null);
                           onCrash(); 
                        }, 2000);
                     }}
                     style={{ 
                        background: isHealing ? 'rgba(59, 130, 246, 0.2)' : '#1a1a1a', 
                        color: isHealing ? '#60a5fa' : '#fff', 
                        border: isHealing ? '1px solid #3b82f6' : '1px solid #333', 
                        padding: '10px 20px', borderRadius: '8px', cursor: 'pointer', fontWeight: 'bold', transition: 'all 0.3s' 
                     }}>
                     {isHealing ? '⚡ AI is Auto-Healing Code...' : '✨ Diagnose & Auto-Fix'}
                  </button>
               </div>
            )}
          </div>
        )}
      </div>

      <div style={{ display: activeTab === 'terminal' ? 'flex' : 'none', flexDirection: 'column', height: '100%', width: '100%' }}>
         <div style={{ padding: '12px 20px', borderBottom: '1px solid #222', color: '#888', fontSize: '0.85rem', display: 'flex', justifyContent: 'space-between', backgroundColor: '#000' }}>
             <span>yAI Execution Logs (WebContainer)</span>
             <span style={{ color: restarting ? '#ef4444' : '#10b981' }}>{restarting ? '● Rebooting' : '● Live'}</span>
         </div>
         <div style={{ flex: 1, overflow: 'auto', backgroundColor: '#000', padding: '10px' }}>
           <SandpackConsole resetOnPreviewRestart={true} style={{ height: '100%', background: 'transparent' }} />
         </div>
      </div>
    </>
  );
};

export const ExecutionManager = ({ files, dynamicDependencies, activeTab, isBackend, previewUrl, previewError, projectId, hasFrontendFiles, executionLogs = [] }) => {
  const [restartKey, setRestartKey] = useState(0);
  
  const isExecuting = executionLogs && executionLogs.length > 0 && !previewUrl && !previewError;

  const handleCrash = () => {
     // A hard key update forces React to unmount the SandpackProvider entirely and remount a fresh iframe
     setRestartKey(prev => prev + 1);
  };

  // Pure backend project (no UI)
  if (isBackend && !hasFrontendFiles) {
      return (
          <BackendSandbox 
              activeTab={activeTab} 
              previewUrl={previewUrl} 
              previewError={previewError}
              projectId={projectId} 
          />
      );
  }

  // Frontend or Full-stack project
  // If full-stack, Sandpack serves UI, BackendSandbox runs in background
  return (
    <div style={{ width: '100%', height: '100%', backgroundColor: '#151515', position: 'relative', display: 'flex', flexDirection: 'column' }}>
      
      {/* If full-stack and user clicked terminal, show backend logs in a split pane */}
      {isBackend && activeTab === 'terminal' && (
         <div style={{ height: '40%', borderBottom: '2px solid #333' }}>
             <BackendSandbox activeTab="terminal" previewUrl={previewUrl} previewError={previewError} projectId={projectId} />
         </div>
      )}

      <div style={{ flex: 1, position: 'relative' }}>
          {isExecuting && activeTab === 'preview' && (
             <div style={{ position: 'absolute', top: 0, left: 0, right: 0, bottom: 0, zIndex: 10, backgroundColor: 'rgba(21,21,21,0.95)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <BuildStatus executionLogs={executionLogs} isRunning={true} hasError={false} />
             </div>
          )}
          <SandpackProvider
            key={`sp-reboot-${restartKey}`}
            template="vite-react"
            theme="dark"
            files={files}
            customSetup={{ 
                dependencies: dynamicDependencies,
                environment: {
                   VITE_API_URL: previewUrl || ""
                }
            }}
            options={{
                recompileMode: "delayed",
                recompileDelay: 2500
            }}
          >
            <SandpackLayout style={{ height: '100%', border: 'none', background: 'transparent', display: 'flex', flexDirection: 'column' }}>
              <ExecutionLifecycle activeTab={activeTab} onCrash={handleCrash} />
            </SandpackLayout>
          </SandpackProvider>
      </div>
    </div>
  );
};

export default ExecutionManager;
