import React, { useEffect, useRef, useState } from 'react';

const PreviewViewer = ({ codeFiles }) => {
  const iframeRef = useRef(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!codeFiles || Object.keys(codeFiles).length === 0) return;

    // Find the main App component
    const appCode = codeFiles['client/src/App.jsx'] || codeFiles['src/App.jsx'] || codeFiles['App.jsx'] || '';
    
    if (!appCode) {
      setError("No App.jsx found to preview.");
      return;
    }

    setError(null);

    // Prepare the HTML document for the iframe
    const htmlContent = `
      <!DOCTYPE html>
      <html lang="en">
        <head>
          <meta charset="UTF-8" />
          <meta name="viewport" content="width=device-width, initial-scale=1.0" />
          <title>Live Preview</title>
          
          <!-- Tailwind CSS for styling -->
          <script src="https://cdn.tailwindcss.com"></script>
          
          <!-- React and ReactDOM -->
          <script crossorigin src="https://unpkg.com/react@18/umd/react.development.js"></script>
          <script crossorigin src="https://unpkg.com/react-dom@18/umd/react-dom.development.js"></script>
          
          <!-- Babel Standalone for in-browser JSX compilation -->
          <script src="https://unpkg.com/@babel/standalone/babel.min.js"></script>
          
          <!-- Lucide Icons (often used by AI generators) -->
          <script src="https://unpkg.com/lucide@latest"></script>

          <style>
            body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; margin: 0; padding: 0; }
          </style>
        </head>
        <body>
          <div id="root"></div>
          
          <script type="text/babel">
            try {
                // Mock dependencies that the AI might import
                window.lucide_react = {
                    Menu: () => <i data-lucide="menu"></i>,
                    Home: () => <i data-lucide="home"></i>,
                    Settings: () => <i data-lucide="settings"></i>,
                    User: () => <i data-lucide="user"></i>,
                    Search: () => <i data-lucide="search"></i>,
                    Bell: () => <i data-lucide="bell"></i>
                };
                
                const require = (moduleName) => {
                    if (moduleName === 'react') return React;
                    if (moduleName === 'lucide-react') return window.lucide_react;
                    return {};
                };
                window.require = require;
                window.exports = {};
                window.module = { exports: {} };

                // Strip out import statements so Babel doesn't crash
                let code = \`${appCode.replace(/\\/g, '\\\\').replace(/\`/g, '\\`').replace(/\$/g, '\\$')}\`;
                
                // Extremely naive import stripper
                code = code.replace(/^import\\s+.*?\\s+from\\s+['"].*?['"];?$/gm, '');
                
                // Compile and execute the React component
                const compiled = Babel.transform(code, { presets: ['react', 'env'] }).code;
                
                // Execute the compiled code in this context
                const execFunction = new Function('React', 'require', 'exports', 'module', compiled + '; return module.exports || App || window.App;');
                
                const AppComponent = execFunction(React, require, window.exports, window.module);
                
                // Check if it's a valid React component
                if (AppComponent) {
                    const root = ReactDOM.createRoot(document.getElementById('root'));
                    root.render(<AppComponent />);
                    setTimeout(() => { if (window.lucide) window.lucide.createIcons(); }, 100);
                } else {
                    throw new Error("Could not find a valid App component to render.");
                }
            } catch (err) {
                document.getElementById('root').innerHTML = \`
                    <div style="color: red; padding: 20px; font-family: monospace;">
                        <h3>Preview Error:</h3>
                        <pre>\${err.toString()}</pre>
                        <p>Note: Complex imports (like react-router-dom) are not supported in this lightweight preview.</p>
                    </div>
                \`;
            }
          </script>
        </body>
      </html>
    `;

    if (iframeRef.current) {
      const iframeDoc = iframeRef.current.contentDocument || iframeRef.current.contentWindow.document;
      iframeDoc.open();
      iframeDoc.write(htmlContent);
      iframeDoc.close();
    }
  }, [codeFiles]);

  return (
    <div style={{ width: '100%', height: '100%', display: 'flex', flexDirection: 'column', backgroundColor: '#fff', borderRadius: '12px', overflow: 'hidden' }}>
      {error ? (
        <div style={{ padding: '20px', color: 'red', backgroundColor: '#fee2e2', height: '100%' }}>
          {error}
        </div>
      ) : (
        <iframe
          ref={iframeRef}
          style={{ width: '100%', height: '100%', border: 'none' }}
          title="Instant Preview"
          sandbox="allow-scripts allow-same-origin"
        />
      )}
    </div>
  );
};

export default PreviewViewer;
