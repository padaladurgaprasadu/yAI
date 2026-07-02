import React, { useState, useEffect } from 'react';
import { Excalidraw } from '@excalidraw/excalidraw';

export default function Whiteboard() {
  const [excalidrawAPI, setExcalidrawAPI] = useState(null);

  // Excalidraw component needs a defined height to render properly
  return (
    <div style={{ height: 'calc(100vh - 65px)', width: '100%', position: 'relative' }}>
      <Excalidraw 
        excalidrawAPI={(api) => setExcalidrawAPI(api)}
        theme="dark"
        UIOptions={{
          canvasActions: {
            loadScene: true,
            export: { saveFileToDisk: true },
            saveAsImage: true
          }
        }}
      />
    </div>
  );
}
