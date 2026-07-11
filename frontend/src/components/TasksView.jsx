import React from 'react';

const TasksView = ({ timeline }) => {
  return (
    <div style={{ padding: '24px', height: '100%', overflowY: 'auto', backgroundColor: 'var(--app-bg)' }}>
      <h2 style={{ display: 'flex', alignItems: 'center', gap: '10px', color: 'var(--text-primary)', marginTop: 0 }}>
        <span style={{ fontSize: '1.5rem' }}>📝</span> Planner Objectives
      </h2>
      <p style={{ color: 'var(--text-secondary)' }}>
        Current execution modules mapped by the yAI Planner and their real-time completion status.
      </p>
      
      <div style={{ marginTop: '30px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
        {timeline && timeline.length > 0 ? (
          timeline.map((item, idx) => (
            <div key={idx} className="dashboard-glass-card" style={{ 
              padding: '16px 20px', 
              display: 'flex', 
              justifyContent: 'space-between',
              alignItems: 'center',
              borderLeft: item.status === 'done' ? '4px solid #10b981' : (item.status === 'active' ? '4px solid #3b82f6' : '4px solid #475569')
            }}>
              <div>
                <h4 style={{ margin: '0 0 6px 0', color: 'var(--text-primary)' }}>{item.title}</h4>
                <p style={{ margin: 0, fontSize: '0.85rem', color: 'var(--modal-text-color)' }}>{item.reason}</p>
              </div>
              <div style={{ 
                padding: '4px 12px', 
                borderRadius: '12px', 
                fontSize: '0.75rem', 
                fontWeight: 'bold',
                backgroundColor: item.status === 'done' ? 'rgba(16, 185, 129, 0.1)' : (item.status === 'active' ? 'rgba(59, 130, 246, 0.1)' : 'rgba(71, 85, 105, 0.1)'),
                color: item.status === 'done' ? '#10b981' : (item.status === 'active' ? '#3b82f6' : '#94a3b8')
              }}>
                {item.status.toUpperCase()}
              </div>
            </div>
          ))
        ) : (
          <div style={{ padding: '40px', textAlign: 'center', color: 'var(--modal-text-color)' }}>
            No active planning modules. Start a project to see tasks here.
          </div>
        )}
      </div>
    </div>
  );
};

export default TasksView;
