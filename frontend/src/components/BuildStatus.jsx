import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { CheckCircle, Loader, XCircle, Code, Server, Play, ShieldAlert } from 'lucide-react';

const steps = [
  { id: 'scaffold', label: 'Scaffolding Project', icon: <Code size={18} /> },
  { id: 'install', label: 'Installing Dependencies', icon: <Server size={18} /> },
  { id: 'start', label: 'Starting Server', icon: <Play size={18} /> },
  { id: 'verify', label: 'Verifying Preview', icon: <CheckCircle size={18} /> }
];

export const BuildStatus = ({ executionLogs = [], isRunning = false, hasError = false }) => {
  const [currentStep, setCurrentStep] = useState(0);

  useEffect(() => {
    if (!isRunning && !hasError) {
      if (executionLogs.length > 0) {
         setCurrentStep(4); // All done
      }
      return;
    }

    if (hasError) {
       // Keep current step but show error state
       return;
    }

    // Heuristics to determine the current step based on the live SSE telemetry logs
    const logsStr = executionLogs.join('\n').toLowerCase();
    
    if (logsStr.includes('verifying preview') || logsStr.includes('http://localhost:')) {
      setCurrentStep(3);
    } else if (logsStr.includes('running: npm run') || logsStr.includes('running: python') || logsStr.includes('starting server')) {
      setCurrentStep(2);
    } else if (logsStr.includes('npm install') || logsStr.includes('pip install') || logsStr.includes('installing')) {
      setCurrentStep(1);
    } else if (logsStr.length > 0) {
      setCurrentStep(0);
    }
  }, [executionLogs, isRunning, hasError]);

  if (!isRunning && currentStep === 4 && !hasError) {
     return null; // Don't show if successfully finished (ExecutionManager takes over)
  }

  return (
    <div style={{
      padding: '24px',
      backgroundColor: '#111',
      borderRadius: '12px',
      border: '1px solid #333',
      margin: '20px auto',
      maxWidth: '600px',
      color: '#fff',
      boxShadow: '0 10px 30px rgba(0,0,0,0.5)'
    }}>
      <h3 style={{ margin: '0 0 20px 0', fontSize: '1.2rem', display: 'flex', alignItems: 'center', gap: '10px' }}>
        <span style={{ color: '#60a5fa' }}>⚙️</span> Execution Engine
      </h3>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
        {steps.map((step, index) => {
          const isActive = index === currentStep && isRunning && !hasError;
          const isPast = index < currentStep || (index === currentStep && !isRunning && !hasError);
          const isError = index === currentStep && hasError;

          return (
            <div key={step.id} style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              <div style={{
                width: '32px',
                height: '32px',
                borderRadius: '50%',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                backgroundColor: isError ? 'rgba(239, 68, 68, 0.2)' : isPast ? 'rgba(16, 185, 129, 0.2)' : isActive ? 'rgba(59, 130, 246, 0.2)' : '#222',
                color: isError ? '#ef4444' : isPast ? '#10b981' : isActive ? '#60a5fa' : '#666',
                border: `1px solid ${isError ? '#ef4444' : isPast ? '#10b981' : isActive ? '#3b82f6' : '#333'}`
              }}>
                {isError ? <ShieldAlert size={16} /> : isPast ? <CheckCircle size={16} /> : isActive ? <Loader className="animate-spin" size={16} /> : step.icon}
              </div>
              <div style={{ flex: 1 }}>
                <div style={{ 
                  fontWeight: isActive || isError ? '600' : '400',
                  color: isError ? '#ef4444' : isActive ? '#fff' : isPast ? '#a6accd' : '#666',
                  fontSize: '0.95rem'
                }}>
                  {step.label}
                </div>
                {isActive && (
                  <motion.div 
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: 'auto' }}
                    style={{ fontSize: '0.8rem', color: '#888', marginTop: '4px' }}
                  >
                    Processing via AI Swarm...
                  </motion.div>
                )}
                {isError && (
                  <motion.div 
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: 'auto' }}
                    style={{ fontSize: '0.8rem', color: '#fca5a5', marginTop: '4px' }}
                  >
                    Auto-healing sequence initiated...
                  </motion.div>
                )}
              </div>
            </div>
          );
        })}
      </div>
      
      {/* Latest Log Preview */}
      {executionLogs.length > 0 && (
         <div style={{ 
            marginTop: '24px', 
            padding: '12px', 
            backgroundColor: '#0a0a0a', 
            borderRadius: '8px', 
            fontFamily: 'monospace', 
            fontSize: '0.75rem', 
            color: '#888',
            height: '60px',
            overflow: 'hidden',
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'flex-end'
         }}>
            {executionLogs.slice(-2).map((log, i) => (
               <div key={i} style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                  {log}
               </div>
            ))}
         </div>
      )}
    </div>
  );
};

export default BuildStatus;
