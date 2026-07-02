import React, { useState, useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkBreaks from 'remark-breaks';
import Mermaid from '../Mermaid';
import ArchitectureViewer from './ArchitectureViewer';
const renderMessageContent = (content) => {
  if (!content.includes('<architecture>')) {
      return (
        <ReactMarkdown 
          remarkPlugins={[remarkGfm, remarkBreaks]}
          components={{
            pre: ({node, ...props}) => <pre style={{background: '#0d0d0d', padding: '12px', borderRadius: '4px', overflowX: 'auto', marginTop: '8px'}} {...props} />,
            code: ({node, inline, className, children, ...props}) => {
              const match = /language-(\w+)/.exec(className || '');
              if (!inline && match && match[1] === 'mermaid') {
                return <Mermaid chart={String(children).replace(/\n$/, '')} />;
              }
              return inline ? (
                <code style={{background: '#222', padding: '2px 4px', borderRadius: '4px'}} {...props}>{children}</code>
              ) : (
                <code className={className} {...props}>{children}</code>
              );
            }
          }}
        >
          {content}
        </ReactMarkdown>
      );
  }
  
  const parts = content.split(/(<architecture>[\s\S]*?<\/architecture>)/);
  return parts.map((part, i) => {
      if (part.startsWith('<architecture>') && part.endsWith('</architecture>')) {
          const jsonStr = part.replace('<architecture>', '').replace('</architecture>', '').replace(/```json/g, '').replace(/```/g, '').trim();
          return <ArchitectureViewer key={i} architectureJson={jsonStr} />;
      }
      return (
        <ReactMarkdown key={i}
          remarkPlugins={[remarkGfm, remarkBreaks]}
          components={{
            pre: ({node, ...props}) => <pre style={{background: '#0d0d0d', padding: '12px', borderRadius: '4px', overflowX: 'auto', marginTop: '8px'}} {...props} />,
            code: ({node, inline, className, children, ...props}) => {
              const match = /language-(\w+)/.exec(className || '');
              if (!inline && match && match[1] === 'mermaid') {
                return <Mermaid chart={String(children).replace(/\n$/, '')} />;
              }
              return inline ? (
                <code style={{background: '#222', padding: '2px 4px', borderRadius: '4px'}} {...props}>{children}</code>
              ) : (
                <code className={className} {...props}>{children}</code>
              );
            }
          }}
        >
          {part}
        </ReactMarkdown>
      );
  });
};

export default function Chat() {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef(null);

  // Auto-scroll to bottom of chat
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isOpen]);

  const handleAsk = async (e) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const query = input;
    setInput('');
    setIsLoading(true);

    // Snapshot history before adding the new user message (for the API call)
    const historyPayload = messages.map(m => ({
      role: m.role,
      content: m.content
    }));

    // Add user message to UI
    setMessages(prev => [...prev, { role: 'user', content: query }]);

    try {
      // Use VITE_API_URL if defined, otherwise fallback to the current window's origin
      // This ensures it works seamlessly in production (e.g. Render) where frontend/backend share a host
      const apiUrl = import.meta.env.VITE_API_URL || window.location.origin;
      const response = await fetch(`${apiUrl}/api/tutor`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          query: query,
          history: historyPayload
        }),
      });
      
      const data = await response.json();
      
      if (!response.ok) {
        throw new Error(data.detail || 'Failed to get response');
      }

      setMessages(prev => [...prev, { role: 'assistant', content: data.response }]);
    } catch (err) {
      setMessages(prev => [...prev, { role: 'assistant', content: `**Error:** ${err.message}` }]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className={`tutor-chat-widget ${isOpen ? 'open' : ''}`}>
      <button 
        className="chat-toggle-btn"
        onClick={() => setIsOpen(!isOpen)}
        style={{
          position: 'fixed',
          bottom: '24px',
          right: '24px',
          width: '56px',
          height: '56px',
          borderRadius: '50%',
          background: 'var(--primary-color)',
          color: 'white',
          border: 'none',
          boxShadow: '0 4px 12px rgba(0,0,0,0.3)',
          cursor: 'pointer',
          zIndex: 1000,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: '24px'
        }}
      >
        {isOpen ? '✕' : '💬'}
      </button>

      {isOpen && (
        <div style={{
          position: 'fixed',
          bottom: '90px',
          right: '24px',
          width: '380px',
          height: '600px',
          maxHeight: '80vh',
          background: 'var(--bg-color)',
          border: '1px solid var(--border-color)',
          borderRadius: '12px',
          boxShadow: '0 8px 24px rgba(0,0,0,0.5)',
          display: 'flex',
          flexDirection: 'column',
          zIndex: 999,
          overflow: 'hidden'
        }}>
          <div style={{
            padding: '16px',
            borderBottom: '1px solid var(--border-color)',
            background: 'var(--card-bg)',
            fontWeight: 'bold',
            display: 'flex',
            alignItems: 'center',
            gap: '8px'
          }}>
            <span>🎓</span> AiON Mentor
          </div>
          
          <div style={{
            flex: 1,
            overflowY: 'auto',
            padding: '16px',
            display: 'flex',
            flexDirection: 'column',
            gap: '16px'
          }}>
            {messages.length === 0 && (
              <div style={{ color: '#888', textAlign: 'center', marginTop: '20px' }}>
                Ask me anything about code, architecture, or AiON concepts! I will format perfectly every time.
              </div>
            )}
            
            {messages.map((msg, i) => (
              <div key={i} style={{
                alignSelf: msg.role === 'user' ? 'flex-end' : 'flex-start',
                background: msg.role === 'user' ? 'var(--primary-color)' : 'var(--card-bg)',
                color: msg.role === 'user' ? 'white' : 'inherit',
                padding: '12px',
                borderRadius: '8px',
                maxWidth: '85%',
                border: msg.role === 'assistant' ? '1px solid var(--border-color)' : 'none'
              }}>
                {msg.role === 'user' ? (
                  <div style={{ whiteSpace: 'pre-wrap' }}>{msg.content}</div>
                ) : (
                  renderMessageContent(msg.content)
                )}
              </div>
            ))}
            
            {isLoading && (
              <div style={{
                alignSelf: 'flex-start',
                background: 'var(--card-bg)',
                padding: '12px',
                borderRadius: '8px',
                color: '#888',
                border: '1px solid var(--border-color)'
              }}>
                Thinking...
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          <form onSubmit={handleAsk} style={{
            padding: '16px',
            borderTop: '1px solid var(--border-color)',
            background: 'var(--card-bg)',
            display: 'flex',
            gap: '8px'
          }}>
            <input 
              type="text" 
              value={input}
              onChange={e => setInput(e.target.value)}
              placeholder="Ask AiON Mentor..."
              disabled={isLoading}
              style={{
                flex: 1,
                padding: '12px',
                borderRadius: '8px',
                border: '1px solid var(--border-color)',
                background: 'var(--bg-color)',
                color: 'white',
                outline: 'none'
              }}
            />
            <button 
              type="submit" 
              disabled={isLoading || !input.trim()}
              style={{
                padding: '0 16px',
                background: 'var(--primary-color)',
                color: 'white',
                border: 'none',
                borderRadius: '8px',
                cursor: (isLoading || !input.trim()) ? 'not-allowed' : 'pointer',
                opacity: (isLoading || !input.trim()) ? 0.5 : 1
              }}
            >
              Send
            </button>
          </form>
        </div>
      )}
    </div>
  );
}
