import React, { useState, useRef } from 'react';
import { RefreshCw, ExternalLink, Monitor, Smartphone, Tablet, ChevronLeft, ChevronRight, Lock } from 'lucide-react';

export const AdvancedBrowserPreview = ({ url }) => {
  const [iframeKey, setIframeKey] = useState(0);
  const [deviceView, setDeviceView] = useState('desktop'); // 'desktop', 'tablet', 'mobile'
  
  const handleRefresh = () => {
    setIframeKey(prev => prev + 1);
  };

  const handleOpenExternal = () => {
    window.open(url, '_blank');
  };

  // Dimensions for different views
  const viewStyles = {
    desktop: { width: '100%', height: '100%', borderRadius: '0 0 8px 8px' },
    tablet: { width: '768px', height: '1024px', margin: '20px auto', borderRadius: '12px', boxShadow: '0 10px 40px rgba(0,0,0,0.5)', border: '12px solid #222' },
    mobile: { width: '375px', height: '812px', margin: '20px auto', borderRadius: '30px', boxShadow: '0 10px 40px rgba(0,0,0,0.5)', border: '14px solid #222' }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', width: '100%', height: '100%', backgroundColor: '#0d0d0d' }}>
      
      {/* Browser Chrome Header */}
      <div style={{ 
        display: 'flex', 
        alignItems: 'center', 
        justifyContent: 'space-between', 
        padding: '8px 16px', 
        backgroundColor: '#1a1a1a', 
        borderBottom: '1px solid #333',
        borderTopLeftRadius: '8px',
        borderTopRightRadius: '8px'
      }}>
        
        {/* Left: Window Controls & Nav */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          <div style={{ display: 'flex', gap: '8px' }}>
            <div style={{ width: '12px', height: '12px', borderRadius: '50%', backgroundColor: '#ef4444' }} />
            <div style={{ width: '12px', height: '12px', borderRadius: '50%', backgroundColor: '#f59e0b' }} />
            <div style={{ width: '12px', height: '12px', borderRadius: '50%', backgroundColor: '#10b981' }} />
          </div>
          <div style={{ display: 'flex', gap: '8px', color: '#666' }}>
            <ChevronLeft size={18} style={{ cursor: 'not-allowed' }} />
            <ChevronRight size={18} style={{ cursor: 'not-allowed' }} />
            <RefreshCw 
              size={16} 
              style={{ cursor: 'pointer', color: '#a6accd', marginLeft: '4px' }} 
              onClick={handleRefresh}
              title="Reload Preview"
            />
          </div>
        </div>

        {/* Center: URL Bar */}
        <div style={{ 
          display: 'flex', 
          alignItems: 'center', 
          gap: '8px', 
          backgroundColor: '#0a0a0a', 
          padding: '6px 16px', 
          borderRadius: '6px', 
          width: '50%', 
          maxWidth: '600px',
          border: '1px solid #333',
          color: '#a6accd',
          fontSize: '0.85rem'
        }}>
          <Lock size={12} color="#10b981" />
          <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', userSelect: 'all' }}>
            {url}
          </span>
        </div>

        {/* Right: Device Toggles & External */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div style={{ display: 'flex', backgroundColor: '#222', borderRadius: '6px', padding: '2px' }}>
            <button 
              onClick={() => setDeviceView('desktop')}
              style={{ padding: '6px', borderRadius: '4px', background: deviceView === 'desktop' ? '#3b82f6' : 'transparent', border: 'none', color: deviceView === 'desktop' ? '#fff' : '#666', cursor: 'pointer' }}
              title="Desktop View"
            ><Monitor size={16} /></button>
            <button 
              onClick={() => setDeviceView('tablet')}
              style={{ padding: '6px', borderRadius: '4px', background: deviceView === 'tablet' ? '#3b82f6' : 'transparent', border: 'none', color: deviceView === 'tablet' ? '#fff' : '#666', cursor: 'pointer' }}
              title="Tablet View"
            ><Tablet size={16} /></button>
            <button 
              onClick={() => setDeviceView('mobile')}
              style={{ padding: '6px', borderRadius: '4px', background: deviceView === 'mobile' ? '#3b82f6' : 'transparent', border: 'none', color: deviceView === 'mobile' ? '#fff' : '#666', cursor: 'pointer' }}
              title="Mobile View"
            ><Smartphone size={16} /></button>
          </div>
          
          <button 
            onClick={handleOpenExternal}
            style={{ display: 'flex', alignItems: 'center', gap: '6px', padding: '6px 12px', borderRadius: '6px', background: '#222', border: '1px solid #333', color: '#a6accd', cursor: 'pointer', fontSize: '0.8rem' }}
          >
            <ExternalLink size={14} /> Open
          </button>
        </div>

      </div>

      {/* Main Preview Area */}
      <div style={{ flex: 1, overflow: 'auto', backgroundColor: '#0d0d0d', display: 'flex', justifyContent: 'center' }}>
        <div style={{ transition: 'all 0.3s ease', ...viewStyles[deviceView], overflow: 'hidden' }}>
          <iframe
            key={iframeKey}
            src={url}
            style={{ width: '100%', height: '100%', border: 'none', backgroundColor: '#fff' }}
            title="Advanced Preview"
            sandbox="allow-forms allow-modals allow-popups allow-presentation allow-same-origin allow-scripts"
          />
        </div>
      </div>
      
    </div>
  );
};
