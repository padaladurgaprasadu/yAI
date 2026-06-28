import { useState, useEffect, useRef } from 'react'
import './App.css'
import Auth from './components/Auth'
import Mermaid from './Mermaid'
import { supabase } from './lib/supabaseClient'
import { marked } from 'marked'
import DOMPurify from 'dompurify'

// Configure marked to use breaks
marked.setOptions({
  breaks: true,
  gfm: true
})

const renderMessageContent = (content) => {
  if (!content.includes('<mermaid>')) {
      const htmlContent = DOMPurify.sanitize(marked.parse(content));
      return (
          <div className="markdown-body" dangerouslySetInnerHTML={{ __html: htmlContent }} />
      );
  }
  
  const parts = content.split(/(<mermaid>[\s\S]*?<\/mermaid>)/);
  return parts.map((part, i) => {
      if (part.startsWith('<mermaid>') && part.endsWith('</mermaid>')) {
          const chart = part.replace('<mermaid>', '').replace('</mermaid>', '').trim();
          return <Mermaid key={i} chart={chart} />;
      }
      const htmlContent = DOMPurify.sanitize(marked.parse(part));
      return (
          <div key={i} className="markdown-body" dangerouslySetInnerHTML={{ __html: htmlContent }} />
      );
  });
};

function App() {
  const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
  const WS_URL = API_URL.replace(/^http/, 'ws');
  
  const [goal, setGoal] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [isPlanning, setIsPlanning] = useState(false)
  const [error, setError] = useState(null)
  
  // Auth state
  const [session, setSession] = useState(null)
  
  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session } }) => {
      setSession(session)
    })

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, session) => {
      setSession(session)
    })

    return () => subscription.unsubscribe()
  }, [])
  
  // Wizard state
  const [step, setStep] = useState(1) // 1: Prompt, 2: Review Blueprint, 3: Generation
  const [projectId, setProjectId] = useState(null)
  const [agentRole, setAgentRole] = useState("Fullstack Web Developer") // New: Agent Selector
  
  // Phase 4 additions
  const [blueprintJson, setBlueprintJson] = useState('')
  const [codeFiles, setCodeFiles] = useState(null)
  const [executionLogs, setExecutionLogs] = useState([])
  
  // Phase 5 additions
  const [liveUpdates, setLiveUpdates] = useState([])

  // Phase 7 additions
  const [isPreviewRunning, setIsPreviewRunning] = useState(false)
  const [awaitingApproval, setAwaitingApproval] = useState(false)
  const [previewPort, setPreviewPort] = useState(null)
  
  // Phase 3 additions
  const [showDevModal, setShowDevModal] = useState(false)

  // Chat state
  const [chatInput, setChatInput] = useState('')
  const [chatMessages, setChatMessages] = useState([])
  const [isChatLoading, setIsChatLoading] = useState(false)
  
  // Sidebar History state
  const [chatHistoryList, setChatHistoryList] = useState([])
  const [currentChatId, setCurrentChatId] = useState(() => Date.now().toString())
  
  // New Interactive State
  const [copiedIndex, setCopiedIndex] = useState(null)
  const [feedbackState, setFeedbackState] = useState({})
  const [isRecording, setIsRecording] = useState(false)

  const chatEndRef = useRef(null)

  // Load chat history from localStorage on mount
  useEffect(() => {
    try {
        const savedHistory = localStorage.getItem('aion_chat_history');
        if (savedHistory) {
            setChatHistoryList(JSON.parse(savedHistory));
        }
    } catch (e) {
        console.error("Failed to load chat history", e);
    }
  }, []);

  // Save current chat to localStorage whenever it updates
  useEffect(() => {
      if (chatMessages.length === 0) return;
      
      setChatHistoryList(prev => {
          // If this chat is already in the list, update it. Otherwise, add it.
          const existingIdx = prev.findIndex(c => c.id === currentChatId);
          let title = "New Project";
          if (chatMessages.length > 0 && chatMessages[0].role === 'user') {
              title = chatMessages[0].content.substring(0, 30) + (chatMessages[0].content.length > 30 ? "..." : "");
          }
          
          const currentChatData = {
              id: currentChatId,
              title: title,
              timestamp: Date.now(),
              goal,
              step,
              chatMessages,
              blueprintJson,
              codeFiles,
              executionLogs,
              agentRole
          };
          
          let newList = [...prev];
          if (existingIdx >= 0) {
              newList[existingIdx] = currentChatData;
          } else {
              newList.unshift(currentChatData); // Add to top
          }
          
          try {
              localStorage.setItem('aion_chat_history', JSON.stringify(newList));
          } catch (e) {
              console.error("Failed to save chat history", e);
          }
          
          return newList;
      });
  }, [chatMessages, goal, step, blueprintJson, codeFiles, executionLogs, agentRole]);

  const handleNewChat = () => {
      setCurrentChatId(Date.now().toString());
      setStep(1);
      setGoal('');
      setChatMessages([]);
      setBlueprintJson('');
      setCodeFiles(null);
      setExecutionLogs([]);
      setError(null);
      setChatInput('');
  };

  const handleLoadChat = (chatId) => {
      const chat = chatHistoryList.find(c => c.id === chatId);
      if (chat) {
          setCurrentChatId(chat.id);
          setStep(chat.step || 1);
          setGoal(chat.goal || '');
          setChatMessages(chat.chatMessages || []);
          setBlueprintJson(chat.blueprintJson || '');
          setCodeFiles(chat.codeFiles || null);
          setExecutionLogs(chat.executionLogs || []);
          setAgentRole(chat.agentRole || "Fullstack Web Developer");
          setError(null);
      }
  };

  const handleEditMessage = (idx) => {
    const msgToEdit = chatMessages[idx].content
    setChatInput(msgToEdit)
    setChatMessages(prev => prev.slice(0, idx))
    setTimeout(() => {
      document.querySelector('input[placeholder="Message AiON..."]')?.focus()
    }, 10)
  }

  const handleCopy = (idx, text) => {
    navigator.clipboard.writeText(text)
    setCopiedIndex(idx)
    setTimeout(() => setCopiedIndex(null), 2000)
  }

  const handleFeedback = (idx, type) => {
    setFeedbackState(prev => ({ ...prev, [idx]: type }))
  }

  const startVoiceRecognition = () => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      alert("Your browser does not support voice input.");
      return;
    }
    const recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = false;
    
    recognition.onstart = () => setIsRecording(true);
    recognition.onresult = (event) => {
      const transcript = event.results[0][0].transcript;
      setChatInput(prev => prev + (prev ? ' ' : '') + transcript);
    };
    recognition.onerror = (event) => {
      console.error("Speech recognition error", event.error);
      setIsRecording(false);
    };
    recognition.onend = () => setIsRecording(false);
    recognition.start();
  }

  const handleChatSubmit = async (e) => {
    e.preventDefault()
    if (!chatInput.trim()) return

    const userMessage = chatInput
    setChatMessages(prev => [...prev, { role: 'user', content: userMessage }])
    setChatInput('')
    setIsChatLoading(true)
    
    // Add an empty AI message that we will stream into
    setChatMessages(prev => [...prev, { role: 'ai', content: '' }])

    try {
      const response = await fetch(`${API_URL}/api/chat`, {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${session?.access_token || 'mock-token-for-local-dev'}`
        },
        body: JSON.stringify({ message: userMessage, history: chatMessages })
      })
      
      setIsChatLoading(false) // Stop the spinner once stream starts
      
      if (!response.ok) {
        setChatMessages(prev => {
            const newMsgs = [...prev];
            newMsgs[newMsgs.length - 1].content = `⚠️ Error: Could not connect to AI.`;
            return newMsgs;
        });
        return;
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder("utf-8");
      
      let buffer = "";

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        
        buffer += decoder.decode(value, { stream: true });
        const parts = buffer.split('\n\n');
        
        // Keep the last incomplete part in the buffer
        buffer = parts.pop();
        
        for (const part of parts) {
            if (part.startsWith('data: ')) {
                try {
                    const data = JSON.parse(part.slice(6));
                    if (data.type === 'chat') {
                        // Append token to the last AI message
                        setChatMessages(prev => {
                            const newMsgs = [...prev];
                            newMsgs[newMsgs.length - 1].content += data.token;
                            return newMsgs;
                        });
                    } else if (data.type === 'build') {
                        // It's a build command, remove the empty AI message and trigger build
                        setChatMessages(prev => {
                            const newMsgs = [...prev];
                            newMsgs[newMsgs.length - 1].content = `Starting build process...\nRole: ${data.data.agent_role}\nGoal: ${data.data.goal}`;
                            return newMsgs;
                        });
                        setGoal(data.data.goal);
                        setAgentRole(data.data.agent_role);
                        handlePlan(data.data.goal, data.data.agent_role);
                    }
                } catch (e) {
                    console.error("Error parsing stream line:", part);
                }
            }
        }
      }
      
    } catch (err) {
      setIsChatLoading(false)
      setChatMessages(prev => {
          const newMsgs = [...prev];
          newMsgs[newMsgs.length - 1].content = "Error connecting to AI. Please try again.";
          return newMsgs;
      });
    }
  }

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [chatMessages])

  const handlePlan = async (buildGoal, buildRole) => {
    if (!buildGoal) return

    setIsLoading(true)
    setIsPlanning(true)
    setError(null)
    setBlueprintJson("")
    
    // We immediately go to step 2 so the user can watch the stream!
    setStep(2) 
    setIsLoading(false) // We won't use the generic spinner anymore

    try {
      const response = await fetch(`${API_URL}/api/plan`, {
        method: 'POST',
        headers: { 
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${session?.access_token || 'mock-token-for-local-dev'}`
        },
        body: JSON.stringify({ goal: buildGoal, agent_role: buildRole })
      })
      
      if (!response.ok) {
          const errData = await response.json().catch(() => ({}));
          throw new Error(errData.detail || 'Failed to plan project');
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder("utf-8");
      
      let fullBlueprint = "";
      let buffer = "";

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        
        buffer += decoder.decode(value, { stream: true });
        const parts = buffer.split('\n\n');
        
        // Keep the last incomplete part in the buffer
        buffer = parts.pop();
        
        for (const part of parts) {
            if (part.startsWith('data: ')) {
                try {
                    const data = JSON.parse(part.slice(6));
                    if (data.type === 'metadata') {
                        setProjectId(data.project_id);
                    } else if (data.type === 'token') {
                        fullBlueprint += data.token;
                        setBlueprintJson(fullBlueprint);
                    } else if (data.type === 'error') {
                        setError(data.message);
                    }
                } catch (e) {
                    console.error("Error parsing stream line:", part);
                }
            }
        }
      }
      
    } catch (err) {
      setError(err.message)
      setStep(1)
    } finally {
      setIsPlanning(false)
    }
  }

  const handleGenerate = async (e) => {
    if (e && e.preventDefault) e.preventDefault();
    setIsLoading(true)
    setError(null)
    setLiveUpdates([])
    setAwaitingApproval(false)
    
    let parsedBlueprint;
    try {
        parsedBlueprint = JSON.parse(blueprintJson);
    } catch (e) {
        setError("Invalid JSON format in Blueprint! Please fix it.");
        setIsLoading(false);
        return;
    }

    try {
      const ws = new WebSocket(`${WS_URL}/api/ws/generate`)
      
      ws.onopen = () => {
        ws.send(JSON.stringify({ 
            project_id: projectId,
            goal: goal,
            blueprint: parsedBlueprint,
            agent_role: agentRole
        }))
      }

      ws.onmessage = (event) => {
        const data = JSON.parse(event.data)
        
        if (data.type === "progress") {
          setLiveUpdates(prev => [...prev, data.message])
        } else if (data.type === "file_start") {
          setLiveCodeFiles(prev => ({ ...prev, [data.file]: "" }))
          setLiveUpdates(prev => [...prev, `Writing code for ${data.file}...`])
        } else if (data.type === "code_token") {
          setLiveCodeFiles(prev => {
             const fileKeys = Object.keys(prev);
             if (fileKeys.length === 0) return prev;
             const lastFile = fileKeys[fileKeys.length - 1];
             return {
                 ...prev,
                 [lastFile]: prev[lastFile] + data.token
             };
          })
        } else if (data.type === "complete") {
          setCodeFiles(data.code_files)
          setExecutionLogs(data.execution_logs)
          setStep(3)
          setIsLoading(false)
          // Keep ws open to receive PREVIEW_READY
        } else if (data.type === "INTERRUPT") {
          setAwaitingApproval(true)
          setLiveUpdates(prev => [...prev, "⏸️ " + data.message])
        } else if (data.type === "PREVIEW_READY") {
          setPreviewPort(data.url.split(':').pop())
          setIsPreviewRunning(true)
          ws.close()
        } else if (data.type === "error") {
          setError(data.message)
          setIsLoading(false)
          ws.close()
        }
      }

      ws.onerror = () => {
        setError("WebSocket connection error. Make sure the backend is running.")
        setIsLoading(false)
        setStep(1) // Return to main screen on error
      }
      
    } catch (err) {
      setError(err.message)
      setIsLoading(false)
      setStep(1)
    }
  }

  const handleResume = async (action) => {
    setAwaitingApproval(false)
    try {
        const response = await fetch(`${API_URL}/api/resume_generation`, {
            method: 'POST',
            headers: { 
              'Content-Type': 'application/json',
              'Authorization': `Bearer ${session?.access_token || 'mock-token-for-local-dev'}`
            },
            body: JSON.stringify({ project_id: projectId, action })
        });
        
        const data = await response.json();
        if (data.status === "aborted") {
            setError("Deployment aborted by user.");
            setIsLoading(false);
            setStep(1);
        } else {
            setLiveUpdates(prev => [...prev, "▶️ Resuming deployment..."]);
        }
    } catch (err) {
        setError(err.message);
        setAwaitingApproval(false);
    }
  }

  const handleStartPreview = async () => {
      try {
          setIsLoading(true);
          const response = await fetch(`${API_URL}/api/start-preview/${projectId}`, { method: 'POST' });
          const data = await response.json();
          setPreviewPort(data.port);
          setIsPreviewRunning(true);
          
          // Wait 3 seconds for the server to bind to the port before rendering iframe
          setTimeout(() => {
              setIsLoading(false);
          }, 3000);
      } catch(e) {
          setError(e.message);
          setIsLoading(false);
      }
  }

  const handleStopPreview = async () => {
      try {
          setIsLoading(true);
          await fetch(`${API_URL}/api/stop-preview/${projectId}`, { method: 'POST' });
          setIsPreviewRunning(false);
          setPreviewPort(null);
      } catch(e) {
          setError(e.message);
      }
  }

  if (!session) {
    return <Auth />
  }

  return (
    <div className="app-container" style={{ display: 'flex', flexDirection: 'column', height: '100vh', backgroundColor: '#0f0f0f', color: '#ececec', overflow: 'hidden' }}>
      
      {/* TOP NAV BAR */}
      <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '12px 24px', backgroundColor: '#1a1a1a', borderBottom: '1px solid #2a2a2a', zIndex: 10 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div style={{ width: '32px', height: '32px', borderRadius: '8px', background: 'linear-gradient(135deg, var(--accent), #2563eb)', display: 'flex', justifyContent: 'center', alignItems: 'center', fontWeight: 'bold', fontSize: '1.2rem' }}>A</div>
          <h1 style={{ margin: 0, fontSize: '1.2rem', letterSpacing: '1px', fontWeight: '600' }}>AiON</h1>
        </div>
        <div style={{ display: 'flex', gap: '12px' }}>
          <button onClick={() => supabase.auth.signOut()} style={{ padding: '8px 16px', fontSize: '0.85rem', backgroundColor: '#2a2a2a', color: '#ccc', border: '1px solid #333', borderRadius: '6px', cursor: 'pointer', transition: 'background 0.2s' }} onMouseEnter={(e) => e.target.style.backgroundColor = '#3a3a3a'} onMouseLeave={(e) => e.target.style.backgroundColor = '#2a2a2a'}>
            Sign Out
          </button>
        </div>
      </header>
      
      {/* MAIN CONTENT AREA */}
      <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
        
        {/* LEFT NAVIGATION SIDEBAR */}
        <aside className="sidebar">
          <button className="sidebar-new-chat-btn" onClick={handleNewChat}>
            <span style={{ fontSize: '1.2rem' }}>➕</span> New Chat
          </button>
          
          <div className="sidebar-history-title">Recent Chats</div>
          <div className="sidebar-history-list">
            {chatHistoryList.map(chat => (
              <div 
                key={chat.id} 
                className={`sidebar-history-item ${currentChatId === chat.id ? 'active' : ''}`}
                onClick={() => handleLoadChat(chat.id)}
                title={chat.title}
              >
                💬 <span className="history-item-text">{chat.title}</span>
              </div>
            ))}
          </div>
            <div style={{ marginTop: 'auto', paddingTop: '16px', borderTop: '1px solid rgba(255,255,255,0.1)', fontSize: '0.8rem', color: '#94a3b8', textAlign: 'center' }}>
              AiON v1.0.1
            </div>
        </aside>

        {/* CHAT SECTION (Centers when step=1, shrinks to 30% when step>1) */}
        <div style={{ 
          flex: step === 1 ? '1' : '0 0 35%', 
          maxWidth: step === 1 ? '100%' : '450px',
          display: 'flex', 
          flexDirection: 'column', 
          transition: 'all 0.5s cubic-bezier(0.2, 0.8, 0.2, 1)',
          borderRight: step === 1 ? 'none' : '1px solid #2a2a2a',
          position: 'relative'
        }}>
          
          <div style={{ flex: 1, overflowY: 'auto', padding: '20px 20px 120px 20px', display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
            <div style={{ width: '100%', maxWidth: '800px', display: 'flex', flexDirection: 'column', gap: '24px' }}>
              
              {chatMessages.length === 0 && step === 1 && (
                <div style={{ textAlign: 'center', marginTop: '15vh' }}>
                  <div style={{ fontSize: '3rem', marginBottom: '16px' }}>✨</div>
                  <h2 style={{ fontSize: '2rem', marginBottom: '12px', fontWeight: '500' }}>What do you want to build?</h2>
                  <p style={{ color: '#888', fontSize: '1.1rem' }}>Ask a question or describe an app you want to generate.</p>
                </div>
              )}

              {chatMessages.map((msg, idx) => (
                <div key={idx} style={{ 
                  display: 'flex', 
                  gap: '16px', 
                  alignSelf: msg.role === 'user' ? 'flex-end' : 'flex-start',
                  maxWidth: '85%',
                  flexDirection: msg.role === 'user' ? 'row-reverse' : 'row'
                }}>
                  <div style={{ 
                    width: '32px', height: '32px', borderRadius: '50%', flexShrink: 0,
                    backgroundColor: msg.role === 'user' ? '#333' : 'var(--accent)',
                    display: 'flex', justifyContent: 'center', alignItems: 'center', fontSize: '14px'
                  }}>
                    {msg.role === 'user' ? 'U' : 'A'}
                  </div>
                  <div style={{ 
                    backgroundColor: msg.role === 'user' ? '#2a2a2a' : 'transparent',
                    padding: msg.role === 'user' ? '12px 18px' : '6px 0',
                    borderRadius: '16px',
                    borderTopRightRadius: msg.role === 'user' ? '4px' : '16px',
                    borderTopLeftRadius: msg.role === 'ai' ? '4px' : '16px',
                    lineHeight: '1.6',
                    fontSize: '1rem',
                    color: '#e0e0e0',
                    position: 'relative'
                  }}>
                    {renderMessageContent(msg.content)}
                    {msg.role === 'ai' && (
                      <div style={{ display: 'flex', gap: '12px', marginTop: '12px' }}>
                        <button 
                          onClick={() => handleCopy(idx, msg.content)} 
                          style={{ background: 'none', border: 'none', cursor: 'pointer', opacity: copiedIndex === idx ? 1 : 0.6, fontSize: '0.9rem', transition: 'opacity 0.2s' }}
                          title="Copy response"
                        >
                          {copiedIndex === idx ? '✅' : '📋'}
                        </button>
                        <button 
                          onClick={() => handleFeedback(idx, 'up')} 
                          style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: '0.9rem', transition: 'all 0.2s', opacity: feedbackState[idx] === 'up' ? 1 : 0.6, filter: feedbackState[idx] === 'up' ? 'drop-shadow(0 0 5px #4ade80)' : 'none' }}
                          title="Good response"
                        >
                          👍
                        </button>
                        <button 
                          onClick={() => handleFeedback(idx, 'down')} 
                          style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: '0.9rem', transition: 'all 0.2s', opacity: feedbackState[idx] === 'down' ? 1 : 0.6, filter: feedbackState[idx] === 'down' ? 'drop-shadow(0 0 5px #f87171)' : 'none' }}
                          title="Bad response"
                        >
                          👎
                        </button>
                      </div>
                    )}
                  </div>
                  {msg.role === 'user' && (
                    <button 
                      onClick={() => handleEditMessage(idx)}
                      style={{
                        background: 'none', border: 'none', color: '#888', cursor: 'pointer',
                        fontSize: '0.9rem', padding: '0 8px', alignSelf: 'center', opacity: 0.7
                      }}
                      title="Edit this message"
                      onMouseEnter={(e) => e.currentTarget.style.opacity = 1}
                      onMouseLeave={(e) => e.currentTarget.style.opacity = 0.7}
                    >
                      ✏️
                    </button>
                  )}
                </div>
              ))}
              
              {isChatLoading && (
                <div style={{ display: 'flex', gap: '16px', alignSelf: 'flex-start' }}>
                   <div style={{ width: '32px', height: '32px', borderRadius: '50%', backgroundColor: 'var(--accent)', display: 'flex', justifyContent: 'center', alignItems: 'center' }}>A</div>
                   <div style={{ padding: '6px 0' }}>
                     <div className="spinner" style={{ width: '18px', height: '18px' }}></div>
                   </div>
                </div>
              )}
              
              {/* Add padding at the bottom so the last message isn't hidden behind the input */}
              <div ref={chatEndRef} style={{ height: '20px' }}></div>
            </div>
          </div>
          
          {/* FLOATING INPUT BOX */}
          <div style={{ 
            position: 'absolute', 
            bottom: '20px', 
            left: '0', 
            right: '0', 
            display: 'flex', 
            justifyContent: 'center',
            padding: '0 20px'
          }}>
            <form onSubmit={handleChatSubmit} style={{ 
              width: '100%', 
              maxWidth: '800px', 
              backgroundColor: '#222', 
              borderRadius: '24px', 
              padding: '8px', 
              display: 'flex', 
              alignItems: 'center', 
              border: '1px solid #333',
              boxShadow: '0 10px 30px rgba(0,0,0,0.5)'
            }}>
              <input 
                type="text" 
                value={chatInput} 
                onChange={(e) => setChatInput(e.target.value)} 
                placeholder={step === 1 ? "Message AiON..." : "Update your app..."} 
                style={{ 
                  flex: 1, 
                  padding: '12px 20px', 
                  backgroundColor: 'transparent', 
                  border: 'none', 
                  color: '#fff', 
                  fontSize: '1rem', 
                  outline: 'none' 
                }}
              />
              <button
                type="button"
                onClick={startVoiceRecognition}
                style={{
                  background: 'none', 
                  border: 'none', 
                  color: isRecording ? '#ef4444' : '#888',
                  fontSize: '1.2rem', 
                  cursor: 'pointer', 
                  padding: '0 16px', 
                  transition: 'color 0.2s',
                  transform: isRecording ? 'scale(1.1)' : 'scale(1)'
                }}
                title={isRecording ? "Listening..." : "Voice Input"}
              >
                🎤
              </button>
              <button 
                type="submit" 
                disabled={isChatLoading || !chatInput.trim()} 
                style={{ 
                  width: '40px', 
                  height: '40px', 
                  borderRadius: '50%', 
                  backgroundColor: (isChatLoading || !chatInput.trim()) ? '#333' : 'var(--accent)', 
                  border: 'none', 
                  color: '#fff', 
                  display: 'flex', 
                  justifyContent: 'center', 
                  alignItems: 'center', 
                  cursor: (isChatLoading || !chatInput.trim()) ? 'not-allowed' : 'pointer',
                  transition: 'background 0.2s'
                }}
              >
                ➤
              </button>
            </form>
          </div>
        </div>

        {/* WORKSPACE PANEL (Hidden in step 1, takes remaining width in step 2 & 3) */}
        {step > 1 && (
          <div style={{ flex: 1, backgroundColor: '#0a0a0a', display: 'flex', flexDirection: 'column', position: 'relative' }}>
            
            {/* WORKSPACE CONTENT */}
            <div style={{ flex: 1, overflowY: 'auto', padding: '30px' }}>
              
              {/* STEP 2: REVIEW BLUEPRINT */}
              {step === 2 && (
                <div style={{ animation: 'fadeIn 0.5s ease-out' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
                    <h2 style={{ margin: 0, fontWeight: '500' }}>Architect's Blueprint</h2>
                    <button onClick={handleGenerate} disabled={isLoading} style={{ padding: '10px 20px', borderRadius: '8px', backgroundColor: 'var(--accent)', color: '#fff', border: 'none', fontWeight: 'bold', cursor: isLoading ? 'not-allowed' : 'pointer' }}>
                      {isLoading ? 'Generating Code...' : 'Approve & Build'}
                    </button>
                  </div>
                  <p style={{ color: '#888', marginBottom: '20px' }}>Review the proposed architecture below. You can edit the JSON directly before building.</p>
                  
                  <textarea 
                      style={{ width: '100%', height: 'calc(100vh - 250px)', backgroundColor: '#1e1e1e', color: '#00ff00', padding: '20px', fontFamily: 'monospace', borderRadius: '12px', border: '1px solid #333', resize: 'none', outline: 'none' }}
                      value={blueprintJson}
                      onChange={(e) => setBlueprintJson(e.target.value)}
                      disabled={isLoading}
                  />
                </div>
              )}

      {/* STEP 1: WELCOME SCREEN */}
      {step === 1 && !isLoading && (
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '60vh', color: 'var(--text-secondary)' }}>
          <div style={{ fontSize: '4rem', marginBottom: '20px' }}>🤖</div>
          <h2>Welcome to the Omni-Chat Builder</h2>
          <p>Talk to AiON Advisor on the left.</p>
          <p>Ask questions, or ask it to "build a new project" and watch the magic happen!</p>
        </div>
      )}

      {/* STEP 2: REVIEW BLUEPRINT */}
      {step === 2 && !isLoading && (
        <div className="results-section">
          <div className="glass-panel result-card">
            <h3>Architect's Blueprint</h3>
            <p style={{marginBottom: '10px', color: 'var(--text-secondary)'}}>
                You can edit this JSON to change the Tech Stack or add custom notes before generating!
            </p>
            <textarea 
                style={{width: '100%', minHeight: '300px', backgroundColor: '#1e1e1e', color: '#fff', padding: '15px', fontFamily: 'monospace', borderRadius: '8px', border: '1px solid #333'}}
                value={blueprintJson}
                onChange={(e) => setBlueprintJson(e.target.value)}
                disabled={isLoading}
            />
            <div style={{display: 'flex', gap: '10px', marginTop: '15px'}}>
                <button className="build-btn" style={{backgroundColor: '#333'}} onClick={() => setStep(1)} disabled={isLoading || isPlanning}>
                    ⬅️ Go Back
                </button>
                <button className="build-btn" onClick={handleGenerate} disabled={isLoading || isPlanning}>
                    {isPlanning ? 'Architect is typing...' : (isLoading ? 'Generating Code & Installing...' : '✅ Approve & Generate Code')}
                </button>
            </div>
          </div>
        </div>
      )}

              {/* STEP 3: RESULTS */}
              {step === 3 && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '24px', animation: 'fadeIn 0.5s ease-out' }}>
                  
                  {/* Phase 7: Live Preview */}
                  <div style={{ backgroundColor: '#111', borderRadius: '12px', border: '1px solid #333', overflow: 'hidden' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '15px 20px', borderBottom: '1px solid #333', backgroundColor: '#1a1a1a' }}>
                        <h3 style={{ margin: 0, fontSize: '1.1rem', fontWeight: '500' }}>Live Preview</h3>
                        <div style={{ display: 'flex', gap: '10px' }}>
                            {!isPreviewRunning ? (
                                <button onClick={handleStartPreview} disabled={isLoading} style={{ padding: '6px 14px', borderRadius: '6px', fontSize: '0.85rem', fontWeight: 'bold', border: 'none', cursor: 'pointer', background: 'linear-gradient(135deg, #10b981, #059669)', color: '#fff' }}>
                                    ▶ Start
                                </button>
                            ) : (
                                <button onClick={handleStopPreview} style={{ padding: '6px 14px', borderRadius: '6px', fontSize: '0.85rem', fontWeight: 'bold', border: 'none', cursor: 'pointer', background: 'linear-gradient(135deg, #ef4444, #dc2626)', color: '#fff' }}>
                                    ⏹ Stop
                                </button>
                            )}
                            {isPreviewRunning && !isLoading && (
                                <button onClick={() => window.open(`http://localhost:${previewPort}`, '_blank')} style={{ padding: '6px 14px', borderRadius: '6px', fontSize: '0.85rem', fontWeight: 'bold', border: 'none', cursor: 'pointer', background: 'linear-gradient(135deg, #a855f7, #9333ea)', color: '#fff' }}>
                                    ↗ New Tab
                                </button>
                            )}
                            <button onClick={() => window.location.href = 'http://localhost:8000/api/download'} style={{ padding: '6px 14px', borderRadius: '6px', fontSize: '0.85rem', fontWeight: 'bold', border: 'none', cursor: 'pointer', background: 'linear-gradient(135deg, #3b82f6, #2563eb)', color: '#fff' }}>
                                ↓ Download
                            </button>
                        </div>
                    </div>
                    
                    {isPreviewRunning && !isLoading && (
                        <div style={{ width: '100%', height: '500px', backgroundColor: '#fff', borderRadius: '12px', overflow: 'hidden', border: '1px solid #333' }}>
                            <iframe 
                                src={`http://localhost:${previewPort}`} 
                                width="100%" height="100%" frameBorder="0" title="Live Preview" 
                            />
                        </div>
                    )}
                    {isPreviewRunning && isLoading && (
                        <div style={{ width: '100%', height: '200px', display: 'flex', justifyContent: 'center', alignItems: 'center', flexDirection: 'column', gap: '15px' }}>
                            <div className="spinner" style={{ width: '30px', height: '30px' }}></div>
                            <p style={{ color: '#888' }}>Booting up server and opening tab...</p>
                        </div>
                    )}
                  </div>

                  <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: '24px' }}>
                      {/* Code Files (Simplified for Workspace) */}
                      <div style={{ backgroundColor: '#111', borderRadius: '12px', border: '1px solid #333', padding: '20px' }}>
                        <h3 style={{ margin: '0 0 15px 0', fontSize: '1.1rem', fontWeight: '500' }}>Generated Files</h3>
                        <div style={{ maxHeight: '400px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '15px' }}>
                          {Object.entries(codeFiles || {}).map(([path, content]) => (
                            <div key={path} style={{ border: '1px solid #333', borderRadius: '8px', overflow: 'hidden' }}>
                              <div style={{ backgroundColor: '#1a1a1a', padding: '8px 12px', borderBottom: '1px solid #333', fontSize: '0.85rem', color: '#aaa', fontFamily: 'monospace' }}>📄 {path}</div>
                              <pre style={{ margin: 0, padding: '15px', backgroundColor: '#0d0d0d', color: '#a6accd', fontSize: '0.85rem', overflowX: 'auto' }}>{content}</pre>
                            </div>
                          ))}
                        </div>
                      </div>
                  </div>
                </div>
              )}
              
              {/* LIVE CODE VIEWER OVERLAY for Workspace */}
              {isLoading && step === 2 && (
                <div style={{ position: 'absolute', top: 0, left: 0, right: 0, bottom: 0, backgroundColor: 'rgba(10,10,10,0.95)', display: 'flex', flexDirection: 'column', zIndex: 50, padding: '30px', animation: 'fadeIn 0.3s ease-out' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
                     <h3 style={{ margin: 0, fontWeight: '500', color: '#fff', display: 'flex', alignItems: 'center', gap: '10px' }}>
                        <div className="spinner" style={{ width: '20px', height: '20px' }}></div>
                        Writing Code...
                     </h3>
                     <span style={{ color: '#888', fontSize: '0.9rem' }}>Streaming Live from AiON Coder Agent</span>
                  </div>
                  
                  <div style={{ flex: 1, backgroundColor: '#0d0d0d', borderRadius: '12px', border: '1px solid #333', overflow: 'hidden', display: 'flex', flexDirection: 'column', boxShadow: '0 10px 40px rgba(0,0,0,0.5)' }}>
                     {/* Tab Bar */}
                     <div style={{ backgroundColor: '#1a1a1a', padding: '10px 15px', borderBottom: '1px solid #333', display: 'flex', gap: '10px', overflowX: 'auto' }}>
                        {Object.keys(liveCodeFiles).map(file => (
                           <div key={file} style={{ padding: '6px 12px', backgroundColor: '#333', borderRadius: '6px', fontSize: '0.85rem', color: '#fff', whiteSpace: 'nowrap', border: '1px solid #444' }}>
                              📄 {file}
                           </div>
                        ))}
                     </div>
                     {/* Code View */}
                     <div style={{ flex: 1, padding: '20px', overflowY: 'auto', color: '#a6accd', fontFamily: 'monospace', fontSize: '0.9rem' }}>
                        <pre style={{ margin: 0, whiteSpace: 'pre-wrap' }}>
                           {Object.keys(liveCodeFiles).length > 0 
                             ? liveCodeFiles[Object.keys(liveCodeFiles)[Object.keys(liveCodeFiles).length - 1]] 
                             : "Initializing Coder Agent...\nReading Blueprint...\nSetting up environment..."}
                           <span className="cursor-blink" style={{ display: 'inline-block', width: '8px', height: '14px', backgroundColor: '#a6accd', marginLeft: '2px', verticalAlign: 'middle' }}></span>
                        </pre>
                     </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

export default App
