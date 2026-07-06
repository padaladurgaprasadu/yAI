import React, { useEffect, useState } from 'react';
import {
  SandpackProvider,
  SandpackLayout,
  SandpackPreview,
  useSandpack,
  SandpackConsole
} from "@codesandbox/sandpack-react";

const ExecutionLifecycle = ({ activeTab }) => {
  const { sandpack } = useSandpack();
  const [restarting, setRestarting] = useState(false);
  const [retryCount, setRetryCount] = useState(0);

  useEffect(() => {
    if (!sandpack || !sandpack.error) return;
    
    const errorMsg = typeof sandpack.error === 'string' ? sandpack.error : (sandpack.error.message || '');
    
    // Detect infrastructure-level WebContainer crashes
    if (
      errorMsg.includes('Failed to get shell by ID') || 
      errorMsg.includes('status code 1') ||
      errorMsg.includes('timeout') ||
      errorMsg.includes('Server has crashed')
    ) {
      if (retryCount < 3) {
        console.warn(`[AiON DevOps] Intercepted infrastructure crash (${errorMsg}), attempting auto-recovery... Attempt ${retryCount + 1}/3`);
        setRestarting(true);
        setRetryCount(prev => prev + 1);
        
        setTimeout(() => {
          sandpack.resetAllFiles();
          setRestarting(false);
        }, 2000);
      } else {
        console.error("[AiON DevOps] Max auto-recovery attempts reached. The preview environment remains unstable.");
      }
    }
  }, [sandpack.error]);

  return (
    <>
      <div style={{ display: activeTab === 'preview' ? 'block' : 'none', height: '100%', width: '100%' }}>
        {restarting ? (
          <div style={{ padding: '20px', color: '#10b981', fontFamily: 'monospace', display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%' }}>
            [AiON DevOps] Recovering execution environment... Rebooting container...
          </div>
        ) : (
          <SandpackPreview 
            style={{ height: 'calc(100dvh - 120px)' }} 
            showNavigator={true} 
            showRefreshButton={true}
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

export const ExecutionManager = ({ files, dynamicDependencies, activeTab }) => {
  return (
    <div style={{ width: '100%', height: '100%', backgroundColor: '#151515', position: 'relative' }}>
      <SandpackProvider
        template="vite-react"
        theme="dark"
        files={files}
        customSetup={{ dependencies: dynamicDependencies }}
        options={{
            recompileMode: "delayed",
            recompileDelay: 500
        }}
      >
        <SandpackLayout style={{ height: '100%', border: 'none', background: 'transparent', display: 'flex', flexDirection: 'column' }}>
          <ExecutionLifecycle activeTab={activeTab} />
        </SandpackLayout>
      </SandpackProvider>
    </div>
  );
};
