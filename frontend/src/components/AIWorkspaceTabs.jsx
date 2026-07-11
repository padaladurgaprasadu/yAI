import React from 'react';
import ArtifactViewer from './ArtifactViewer';
import ArchitectureViewer from './ArchitectureViewer';
import BackendSandbox from './BackendSandbox';
import ExecutionManager from './ExecutionManager';
import PlatformDashboards from './PlatformDashboards';
import MemoryView from './MemoryView';
import TasksView from './TasksView';
import DeploymentView from './DeploymentView';

const AIWorkspaceTabs = ({
  activeTab, 
  setActiveTab,
  codeFiles,
  blueprintJson,
  executionLogs,
  previewUrl,
  previewError,
  isBackend,
  projectId,
  isPreviewRunning,
  previewPort,
  API_URL,
  timeline
}) => {
  
  const tabs = [
    { id: 'files', label: '📂 Files', hidden: !codeFiles },
    { id: 'architecture', label: '📐 Architecture', hidden: !blueprintJson },
    { id: 'preview', label: '👁️ Preview', hidden: !codeFiles },
    { id: 'logs', label: '📋 Logs', hidden: false },
    { id: 'tasks', label: '📝 Tasks', hidden: false },
    { id: 'memory', label: '🧠 Memory', hidden: false },
    { id: 'deployment', label: '🚀 Deploy', hidden: false },
    { id: 'dashboards', label: '📊 Dashboards', hidden: false }
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', width: '100%', backgroundColor: 'var(--app-bg)' }}>
      {/* Workspace Tab Bar */}
      <div style={{ 
        display: 'flex', 
        gap: '8px', 
        padding: '12px 16px 0 16px', 
        borderBottom: '1px solid var(--border-color)',
        backgroundColor: 'var(--sidebar-bg)',
        overflowX: 'auto',
        scrollbarWidth: 'none'
      }}>
        {tabs.filter(t => !t.hidden).map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            style={{
              padding: '10px 16px',
              backgroundColor: activeTab === tab.id ? 'var(--app-bg)' : 'transparent',
              color: activeTab === tab.id ? 'var(--text-primary)' : 'var(--text-secondary)',
              border: '1px solid',
              borderColor: activeTab === tab.id ? 'var(--border-color)' : 'transparent',
              borderBottom: activeTab === tab.id ? '1px solid var(--app-bg)' : '1px solid transparent',
              borderTopLeftRadius: '8px',
              borderTopRightRadius: '8px',
              cursor: 'pointer',
              fontWeight: activeTab === tab.id ? '600' : '400',
              marginBottom: '-1px',
              whiteSpace: 'nowrap',
              transition: 'all 0.2s'
            }}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Workspace Content Area */}
      <div style={{ flex: 1, overflow: 'hidden', position: 'relative' }}>
        {activeTab === 'files' && (
          <ArtifactViewer files={codeFiles} />
        )}
        
        {activeTab === 'architecture' && (
          <ArchitectureViewer blueprint={blueprintJson} />
        )}
        
        {activeTab === 'preview' && (
          <BackendSandbox 
            previewUrl={previewUrl} 
            previewError={previewError}
            isBackend={isBackend}
            projectId={projectId}
            isPreviewRunning={isPreviewRunning}
            previewPort={previewPort}
            API_URL={API_URL}
          />
        )}
        
        {activeTab === 'logs' && (
          <ExecutionManager 
            executionLogs={executionLogs}
          />
        )}
        
        {activeTab === 'dashboards' && (
          <PlatformDashboards API_URL={API_URL} />
        )}
        
        {activeTab === 'memory' && (
          <MemoryView />
        )}
        
        {activeTab === 'tasks' && (
          <TasksView timeline={timeline} />
        )}
        
        {activeTab === 'deployment' && (
          <DeploymentView />
        )}
      </div>
    </div>
  );
};

export default AIWorkspaceTabs;
