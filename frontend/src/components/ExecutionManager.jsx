import React, { useEffect, useState, useCallback } from 'react';
import { BackendSandbox } from './BackendSandbox';
import {
  SandpackProvider,
  SandpackLayout,
  SandpackPreview,
  useSandpack,
  SandpackConsole
} from "@codesandbox/sandpack-react";

const ExecutionLifecycle = ({ activeTab, onCrash }) => {
  const { sandpack, listen } = useSandpack();
  const [restarting, setRestarting] = useState(false);
  const [retryCount, setRetryCount] = useState(0);

  const triggerRecovery = useCallback((reason) => {
    if (retryCount >= 3) {
      console.error(`[AiON DevOps] Max auto-recovery attempts reached. Failed to recover from: ${reason}`);
      return;
    }
    console.warn(`[AiON DevOps] Intercepted infrastructure crash (${reason}), attempting hard reboot... Attempt ${retryCount + 1}/3`);
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
    if (!sandpack || !sandpack.error) return;
    const errorMsg = typeof sandpack.error === 'string' ? sandpack.error : (sandpack.error.message || '');
    if (
      errorMsg.includes('Failed to get shell by ID') || 
      errorMsg.includes('status code 1') ||
      errorMsg.includes('timeout') ||
      errorMsg.includes('Server has crashed')
    ) {
      triggerRecovery(errorMsg);
    }
  }, [sandpack.error, triggerRecovery]);

  return (
    <>
      <div style={{ display: activeTab === 'preview' ? 'block' : 'none', height: '100%', width: '100%' }}>
        {restarting ? (
          <div style={{ padding: '20px', color: '#10b981', fontFamily: 'monospace', display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%' }}>
            [AiON DevOps] Hard Rebooting WebContainer...
          </div>
        ) : (
          <SandpackPreview 
            style={{ height: 'calc(100dvh - 120px)' }} 
            showNavigator={true} 
            showRefreshButton={true}
            showSandpackErrorOverlay={true}
          />
        )}
      </div>

      <div style={{ display: activeTab === 'terminal' ? 'flex' : 'none', flexDirection: 'column', height: '100%', width: '100%' }}>
         <div style={{ padding: '12px 20px', borderBottom: '1px solid #222', color: '#888', fontSize: '0.85rem', display: 'flex', justifyContent: 'space-between', backgroundColor: '#000' }}>
             <span>AiON Execution Logs (WebContainer)</span>
             <span style={{ color: restarting ? '#ef4444' : '#10b981' }}>{restarting ? '● Rebooting' : '● Live'}</span>
         </div>
         <div style={{ flex: 1, overflow: 'auto', backgroundColor: '#000', padding: '10px' }}>
           <SandpackConsole resetOnPreviewRestart={true} style={{ height: '100%', background: 'transparent' }} />
         </div>
      </div>
    </>
  );
};

export const ExecutionManager = ({ files, dynamicDependencies, activeTab, isBackend, previewUrl, previewError, projectId }) => {
  const [restartKey, setRestartKey] = useState(0);

  const handleCrash = () => {
     // A hard key update forces React to unmount the SandpackProvider entirely and remount a fresh iframe
     setRestartKey(prev => prev + 1);
  };

  if (isBackend) {
      return (
          <BackendSandbox 
              activeTab={activeTab} 
              previewUrl={previewUrl} 
              previewError={previewError}
              projectId={projectId} 
          />
      );
  }

  return (
    <div style={{ width: '100%', height: '100%', backgroundColor: '#151515', position: 'relative' }}>
      <SandpackProvider
        key={`sp-reboot-${restartKey}`}
        template="vite-react"
        theme="dark"
        files={files}
        customSetup={{ dependencies: dynamicDependencies }}
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
  );
};
