import React, { useEffect, useRef, useState } from 'react';
import mermaid from 'mermaid';

mermaid.initialize({
  startOnLoad: false,
  theme: 'dark',
  securityLevel: 'loose',
});

const Mermaid = ({ chart }) => {
  const containerRef = useRef(null);
  const [svgStr, setSvgStr] = useState('');

  useEffect(() => {
    if (chart && chart.trim()) {
      const id = `mermaid-${Math.random().toString(36).substring(2, 9)}`;
      mermaid.render(id, chart)
        .then((result) => {
          setSvgStr(result.svg);
        })
        .catch((error) => {
          console.error('Mermaid render error:', error);
          // Fallback if there's a syntax error in the generated mermaid code
          setSvgStr(`<div style="color: #ef4444; padding: 10px; border: 1px solid #ef4444; border-radius: 8px;">Error rendering diagram: ${error.message}</div>`);
        });
    }
  }, [chart]);

  if (!chart || !chart.trim()) return null;

  return (
    <div 
      ref={containerRef}
      className="mermaid-container"
      style={{
        width: '100%',
        overflowX: 'auto',
        backgroundColor: '#0a0a0a',
        padding: '20px',
        borderRadius: '12px',
        border: '1px solid #333',
        marginTop: '10px',
        marginBottom: '10px',
        display: 'flex',
        justifyContent: 'center'
      }}
      dangerouslySetInnerHTML={{ __html: svgStr }}
    />
  );
};

export default Mermaid;
