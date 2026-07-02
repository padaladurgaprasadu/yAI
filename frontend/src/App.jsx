import { useState, useEffect, useRef } from 'react'
import './App.css'
import Auth from './components/Auth'
import Chat from './components/Chat'
import { supabase } from './lib/supabaseClient'
import ArchitectureViewer from './components/ArchitectureViewer'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import remarkBreaks from 'remark-breaks'

const handleMarkdownClick = async (e) => {
  const target = e.target;
  if (target.classList.contains('copy-code-btn')) {
    const code = decodeURIComponent(target.getAttribute('data-code'));
    navigator.clipboard.writeText(code);
    target.innerText = 'Copied!';
    setTimeout(() => { target.innerText = 'Copy'; }, 2000);
  } else if (target.classList.contains('run-code-btn')) {
    const code = decodeURIComponent(target.getAttribute('data-code'));
    const lang = target.getAttribute('data-lang');
    const blockId = target.getAttribute('data-block-id');
    const outputDiv = document.getElementById(`sandbox-${blockId}`);
    
    if (!outputDiv) return;
    
    outputDiv.style.display = 'block';
    outputDiv.innerHTML = '<div style="padding: 12px; color: #888; font-family: monospace; font-size: 0.85rem;">Running...</div>';
    target.innerText = 'Running...';
    target.style.color = '#888';
    target.disabled = true;
    
    // Map languages for Piston API
    let pistonLang = lang;
    if (lang === 'js' || lang === 'node') pistonLang = 'javascript';
    if (lang === 'py') pistonLang = 'python';
    
    // Use VITE_API_URL or local fallback
    const apiUrl = import.meta.env.VITE_API_URL || window.location.origin;
    
    try {
      const res = await fetch(`${apiUrl}/api/execute`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          language: pistonLang,
          code: code
        })
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || JSON.stringify(data) || "Execution API failed with status " + res.status);
      }
      const output = data.output || data.message || "No output returned.";
      outputDiv.innerHTML = `<pre style="margin:0; padding:12px; background:#050505; color:#4ade80; font-family:monospace; font-size:0.85rem; overflow-x:auto;">${output.replace(/</g, '&lt;').replace(/>/g, '&gt;')}</pre>`;
    } catch (err) {
      outputDiv.innerHTML = `<div style="padding: 12px; color: #ef4444; font-family: monospace; font-size: 0.85rem;">Error: ${err.message}</div>`;
    } finally {
      target.innerText = 'Run';
      target.style.color = '#4ade80';
      target.disabled = false;
    }
  }
};

const CodeBlock = ({ node, inline, className, children, ...props }) => {
  const match = /language-(\w+)/.exec(className || '');
  const language = match ? match[1] : 'text';
  const text = String(children).replace(/\n$/, '');
  
  if (inline) {
    return <code className={className} {...props}>{children}</code>;
  }
  
  const encodedCode = encodeURIComponent(text);
  const blockId = Math.random().toString(36).substring(2, 9);
  
  const supportedRunLangs = ['python', 'py', 'javascript', 'js', 'node'];
  const runBtnHTML = supportedRunLangs.includes(language.toLowerCase()) 
    ? <button className="run-code-btn" data-code={encodedCode} data-lang={language} data-block-id={blockId} style={{background: 'none', border: 'none', color: '#4ade80', cursor: 'pointer', fontSize: '0.75rem', transition: 'color 0.2s'}} onMouseOver={(e)=>e.target.style.color='#fff'} onMouseOut={(e)=>e.target.style.color='#4ade80'}>Run</button>
    : null;
    
  return (
    <div className="code-block-wrapper" style={{ position: 'relative', margin: '1em 0', borderRadius: '8px', overflow: 'hidden', border: '1px solid var(--border-color)' }}>
      <div style={{ background: '#1e1e1e', padding: '6px 12px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid var(--border-color)', color: '#888', fontSize: '0.75rem', fontFamily: 'monospace' }}>
        <span>{language}</span>
        <div style={{ display: 'flex', gap: '16px' }}>
          {runBtnHTML}
          <button className="copy-code-btn" data-code={encodedCode} style={{ background: 'none', border: 'none', color: '#aaa', cursor: 'pointer', fontSize: '0.75rem', transition: 'color 0.2s' }} onMouseOver={(e)=>e.target.style.color='#fff'} onMouseOut={(e)=>e.target.style.color='#aaa'}>Copy</button>
        </div>
      </div>
      <pre style={{ margin: 0, borderRadius: 0, padding: '16px', background: '#0d0d0d', overflowX: 'auto' }}>
        <code className={className} {...props}>{children}</code>
      </pre>
      <div id={`sandbox-${blockId}`} style={{ display: 'none', borderTop: '1px dashed var(--border-color)', background: '#050505' }}></div>
    </div>
  );
};

const renderMessageContent = (content, onOpenArchitecture) => {
  if (!content.includes('<architecture>')) {
      return (
          <div className="markdown-body" onClick={handleMarkdownClick}>
              <ReactMarkdown remarkPlugins={[remarkGfm, remarkBreaks]} components={{ code: CodeBlock }}>
                  {content}
              </ReactMarkdown>
          </div>
      );
  }
  
  const parts = content.split(/(<architecture>[\s\S]*?<\/architecture>)/);
  return parts.map((part, i) => {
      if (part.startsWith('<architecture>') && part.endsWith('</architecture>')) {
          const jsonStr = part.replace('<architecture>', '').replace('</architecture>', '').replace(/```json/g, '').replace(/```/g, '').trim();
          return (
            <div key={i} style={{ margin: '16px 0' }}>
              <button 
                onClick={() => onOpenArchitecture(jsonStr)}
                style={{
                  background: 'linear-gradient(135deg, #3b82f6, #2563eb)',
                  color: 'white',
                  border: 'none',
                  padding: '12px 24px',
                  borderRadius: '8px',
                  fontWeight: '600',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '12px',
                  boxShadow: '0 4px 12px rgba(59, 130, 246, 0.3)'
                }}
              >
                <span>📐</span> View Architecture Diagram in Workspace
              </button>
            </div>
          );
      }
      return (
          <div key={i} className="markdown-body" onClick={handleMarkdownClick}>
              <ReactMarkdown remarkPlugins={[remarkGfm, remarkBreaks]} components={{ code: CodeBlock }}>
                  {part}
              </ReactMarkdown>
          </div>
      );
  });
};

function App() {
  // API_URL resolution (works for localhost and production)
  const API_URL = import.meta.env.VITE_API_URL || window.location.origin;
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
  const [chatStatus, setChatStatus] = useState("") // New: Pipeline Status
  const [activeArchitecture, setActiveArchitecture] = useState(null) // New: Architecture Mode
  // Phase 4 additions
  const [blueprintJson, setBlueprintJson] = useState('')
  const [codeFiles, setCodeFiles] = useState(null)
  const [executionLogs, setExecutionLogs] = useState([])
  
  // Streaming state
  const [liveUpdates, setLiveUpdates] = useState([])
  const [liveCodeFiles, setLiveCodeFiles] = useState({})
  
  // Execution state
  const [isPreviewRunning, setIsPreviewRunning] = useState(false)
  const [awaitingApproval, setAwaitingApproval] = useState(false)
  const [previewPort, setPreviewPort] = useState(null)
  const [showSidebar, setShowSidebar] = useState(true)
  
  // Phase 3 additions
  const [showDevModal, setShowDevModal] = useState(false)
  const [showSettingsModal, setShowSettingsModal] = useState(false)

  // Chat state
  const [chatInput, setChatInput] = useState('')
  const [chatMessages, setChatMessages] = useState([])
  const [isChatLoading, setIsChatLoading] = useState(false)
  const [selectedImages, setSelectedImages] = useState([])
  const fileInputRef = useRef(null)
  
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

  // Effect to automatically open architecture if the AI outputs it
  useEffect(() => {
    if (chatMessages.length > 0) {
      const lastMessage = chatMessages[chatMessages.length - 1];
      if (lastMessage.role === 'ai' && lastMessage.content.includes('<architecture>')) {
        const parts = lastMessage.content.split(/(<architecture>[\s\S]*?<\/architecture>)/);
        const archPart = parts.find(p => p.startsWith('<architecture>') && p.endsWith('</architecture>'));
        if (archPart) {
          const jsonStr = archPart.replace('<architecture>', '').replace('</architecture>', '').replace(/```json/g, '').replace(/```/g, '').trim();
          setActiveArchitecture(jsonStr);
          setStep(4);
        }
      }
    }
  }, [chatMessages]);

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

  
  const handleRenameChat = (chatId, e) => {
    e.stopPropagation();
    const chat = chatHistoryList.find(c => c.id === chatId);
    if (!chat) return;
    const newTitle = window.prompt("Enter new title for this chat:", chat.title);
    if (newTitle && newTitle.trim() !== "") {
        const newList = chatHistoryList.map(c => c.id === chatId ? { ...c, title: newTitle.trim() } : c);
        setChatHistoryList(newList);
        try {
            localStorage.setItem('aion_chat_history', JSON.stringify(newList));
        } catch (err) {}
    }
  };

  const handleDeleteChat = (chatId, e) => {
    e.stopPropagation();
    if (window.confirm("Are you sure you want to delete this chat thread?")) {
        const newList = chatHistoryList.filter(c => c.id !== chatId);
        setChatHistoryList(newList);
        try {
            localStorage.setItem('aion_chat_history', JSON.stringify(newList));
        } catch (err) {}
        
        // If we deleted the active chat, clear the screen
        if (currentChatId === chatId) {
            handleNewChat();
        }
    }
  };

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

  const handleImageUpload = (e) => {
    const files = Array.from(e.target.files);
    
    // Check if adding these files exceeds the limit of 4
    if (selectedImages.length + files.length > 4) {
      alert("You can only upload a maximum of 4 images.");
      return;
    }

    files.forEach(file => {
      const reader = new FileReader();
      reader.onloadend = () => {
        setSelectedImages(prev => [...prev, reader.result]);
      };
      reader.readAsDataURL(file);
    });
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
    if (!chatInput.trim() && selectedImages.length === 0) return
    
    const userMessage = chatInput
    const imagePayload = selectedImages.length > 0 ? selectedImages : null
    
    // Add User message immediately
    const userMsgObj = { role: 'user', content: userMessage };
    if (imagePayload) userMsgObj.image = imagePayload;
    
    setChatMessages(prev => [...prev, userMsgObj])
    setChatInput('')
    setSelectedImages([])
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
        body: JSON.stringify({ message: userMessage, history: chatMessages, image: imagePayload })
      })
      
      setIsChatLoading(false) // Stop the spinner once stream starts
      
      if (!response.ok) {
        let errorDetail = `⚠️ Error: Could not connect to AI.`;
        try {
            const errData = await response.json();
            if (errData.detail) errorDetail = `⚠️ Error: ${errData.detail}`;
        } catch(e) {}
        
        setChatMessages(prev => {
            const newMsgs = [...prev];
            newMsgs[newMsgs.length - 1].content = errorDetail;
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
                            newMsgs[newMsgs.length - 1] = {
                                ...newMsgs[newMsgs.length - 1],
                                content: newMsgs[newMsgs.length - 1].content + data.token
                            };
                            return newMsgs;
                        });
                    } else if (data.type === 'status') {
                        setChatStatus(data.message);
                    } else if (data.type === 'build') {
                        // It's a build command, remove the empty AI message and trigger build
                        setChatMessages(prev => {
                            const newMsgs = [...prev];
                            newMsgs[newMsgs.length - 1].content = `Starting build process...\nRole: ${data.data.agent_role}\nGoal: ${data.data.goal}`;
                            return newMsgs;
                        });
                        setGoal(data.data.goal);
                        setAgentRole(data.data.agent_role);
                        handlePlan(data.data.goal, data.data.agent_role, imagePayload);
                    } else if (data.type === 'visual') {
                        setChatMessages(prev => {
                            const newMsgs = [...prev];
                            newMsgs[newMsgs.length - 1] = {
                                ...newMsgs[newMsgs.length - 1],
                                visual: data
                            };
                            return newMsgs;
                        });
                    }
                } catch (e) {
                    console.error("Error parsing stream line:", part);
                }
            }
        }
      }
      
      // Process Memory Tags after stream completes
      setChatMessages(prev => {
          const newMsgs = [...prev];
          let finalMsg = newMsgs[newMsgs.length - 1].content;
          const memoryMatch = finalMsg.match(/\[MEMORY_ADD\](.*)/);
          if (memoryMatch) {
              finalMsg = finalMsg.replace(/\[MEMORY_ADD\].*/, '').trim();
              newMsgs[newMsgs.length - 1].content = finalMsg;
          }
          return newMsgs;
      });

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

  const handlePlan = async (buildGoal, buildRole, buildImage = null) => {
    if (!buildGoal) return

    setIsLoading(true)
    setIsPlanning(true)
    setError(null)
    setBlueprintJson("")
    
    // We immediately go to step 2 so the user can watch the stream!
    setStep(2) 
    setIsLoading(false) // We won't use the generic spinner anymore

    try {
      const payload = { goal: buildGoal, agent_role: buildRole };
      if (buildImage) {
          payload.image = buildImage;
      }
      
      const response = await fetch(`${API_URL}/api/plan`, {
        method: 'POST',
        headers: { 
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${session?.access_token || 'mock-token-for-local-dev'}`
        },
        body: JSON.stringify(payload)
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
      
      // Process Memory Tags after stream completes
      setChatMessages(prev => {
          const newMsgs = [...prev];
          let finalMsg = newMsgs[newMsgs.length - 1].content;
          const memoryMatch = finalMsg.match(/\[MEMORY_ADD\](.*)/);
          if (memoryMatch) {
              finalMsg = finalMsg.replace(/\[MEMORY_ADD\].*/, '').trim();
              newMsgs[newMsgs.length - 1].content = finalMsg;
          }
          return newMsgs;
      });

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
      
      // Process Memory Tags after stream completes
      setChatMessages(prev => {
          const newMsgs = [...prev];
          let finalMsg = newMsgs[newMsgs.length - 1].content;
          const memoryMatch = finalMsg.match(/\[MEMORY_ADD\](.*)/);
          if (memoryMatch) {
              finalMsg = finalMsg.replace(/\[MEMORY_ADD\].*/, '').trim();
              newMsgs[newMsgs.length - 1].content = finalMsg;
          }
          return newMsgs;
      });

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
    <div className="app-container" style={{ display: 'flex', flexDirection: 'column', height: '100dvh', backgroundColor: 'var(--app-bg)', color: 'var(--text-primary)', overflow: 'hidden' }}>
      
      {/* TOP NAV BAR */}
      <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '12px 24px', backgroundColor: 'var(--sidebar-bg)', borderBottom: '1px solid var(--border-color)', zIndex: 10 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '15px' }}>
          <button onClick={() => setShowSidebar(!showSidebar)} style={{ background: 'none', border: 'none', color: 'var(--text-secondary)', fontSize: '1.5rem', cursor: 'pointer', padding: 0, display: 'flex', alignItems: 'center', justifyContent: 'center' }} title="Toggle Sidebar">
            ☰
          </button>
          <div style={{ width: '32px', height: '32px', borderRadius: '8px', background: 'linear-gradient(135deg, var(--accent), #2563eb)', display: 'flex', justifyContent: 'center', alignItems: 'center', fontWeight: 'bold', fontSize: '1.2rem' }}>A</div>
          <h1 style={{ margin: 0, fontSize: '1.2rem', letterSpacing: '1px', fontWeight: '600' }}>AiON</h1>
        </div>
        <div style={{ display: 'flex', gap: '12px' }}>
          {/* Header right side is now empty, profile moved to sidebar */}
        </div>
      </header>
      
      {/* MAIN CONTENT AREA */}
      <div className="main-content-wrapper" style={{ display: 'flex', flex: 1, overflow: 'hidden', position: 'relative' }}>
        
        {/* LEFT NAVIGATION SIDEBAR */}
        {showSidebar && (
        <aside className="sidebar" style={{ display: 'flex', flexDirection: 'column' }}>
          <button className="sidebar-new-chat-btn" onClick={handleNewChat}>
            <span style={{ fontSize: '1.2rem' }}>➕</span> New Chat
          </button>
          
          <div className="sidebar-history-title">Recent Chats</div>
          <div className="sidebar-history-list" style={{ flex: 1, overflowY: 'auto' }}>
            {chatHistoryList.map(chat => (
              <div 
                key={chat.id} 
                className={`sidebar-history-item ${currentChatId === chat.id ? 'active' : ''}`}
                onClick={() => handleLoadChat(chat.id)}
                title={chat.title}
                style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '10px 12px' }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', overflow: 'hidden' }}>
                    💬 <span className="history-item-text" style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{chat.title}</span>
                </div>
                <div className="history-actions" style={{ display: 'flex', gap: '6px' }}>
                    <button onClick={(e) => handleRenameChat(chat.id, e)} style={{ background: 'transparent', border: 'none', cursor: 'pointer', opacity: 0.7, fontSize: '0.8rem' }} title="Rename">✏️</button>
                    <button onClick={(e) => handleDeleteChat(chat.id, e)} style={{ background: 'transparent', border: 'none', cursor: 'pointer', opacity: 0.7, fontSize: '0.8rem' }} title="Delete">🗑️</button>
                </div>
              </div>
            ))}
          </div>
          
          <div style={{ marginTop: 'auto', paddingTop: '16px', borderTop: '1px solid rgba(255,255,255,0.1)', display: 'flex', flexDirection: 'column', gap: '10px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', padding: '0 10px', marginBottom: '10px' }}>
              <div style={{ width: '32px', height: '32px', borderRadius: '50%', backgroundColor: 'var(--border-color)', display: 'flex', justifyContent: 'center', alignItems: 'center', fontSize: '14px', textTransform: 'uppercase' }}>
                {session?.user?.email?.[0] || 'U'}
              </div>
              <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {session?.user?.email || 'User'}
              </div>
            </div>
            
            <div style={{ display: 'flex', gap: '8px' }}>
              <button onClick={() => setShowSettingsModal(true)} style={{ flex: 1, padding: '8px 0', fontSize: '0.8rem', backgroundColor: 'transparent', color: 'var(--text-secondary)', border: '1px solid var(--border-color)', borderRadius: '6px', cursor: 'pointer', transition: 'background 0.2s', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '6px' }} onMouseEnter={(e) => e.target.style.backgroundColor = 'var(--border-color)'} onMouseLeave={(e) => e.target.style.backgroundColor = 'transparent'}>
                ⚙️ Settings
              </button>
              <button onClick={() => supabase.auth.signOut()} style={{ flex: 1, padding: '8px 0', fontSize: '0.8rem', backgroundColor: 'var(--border-color)', color: 'var(--text-secondary)', border: '1px solid var(--border-color)', borderRadius: '6px', cursor: 'pointer', transition: 'background 0.2s' }} onMouseEnter={(e) => e.target.style.backgroundColor = '#3a3a3a'} onMouseLeave={(e) => e.target.style.backgroundColor = 'var(--border-color)'}>
                Sign Out
              </button>
            </div>
            
            <div style={{ fontSize: '0.75rem', color: '#94a3b8', textAlign: 'center', marginTop: '10px' }}>
              AiON v1.0.1
            </div>
          </div>
        </aside>
        )}

        {/* CHAT SECTION (Centers when step=1, shrinks to 30% when step>1) */}
        <div className="chat-section" style={{ 
          flex: step === 1 ? '1' : '0 0 35%', 
          minHeight: 0,
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
                  <p style={{ color: 'var(--modal-text-color)', fontSize: '1.1rem' }}>Ask a question or describe an app you want to generate.</p>
                </div>
              )}

              {chatMessages.map((msg, idx) => (
                <div key={idx} className="chat-message-container" style={{ 
                  display: 'flex', 
                  gap: '16px', 
                  alignSelf: msg.role === 'user' ? 'flex-end' : 'flex-start',
                  maxWidth: '85%',
                  flexDirection: msg.role === 'user' ? 'row-reverse' : 'row'
                }}>
                  <div style={{ 
                    width: '32px', height: '32px', borderRadius: '50%', flexShrink: 0,
                    backgroundColor: msg.role === 'user' ? 'var(--border-color)' : 'var(--accent)',
                    display: 'flex', justifyContent: 'center', alignItems: 'center', fontSize: '14px',
                    textTransform: 'uppercase'
                  }}>
                    {msg.role === 'user' ? (session?.user?.email?.[0] || 'U') : 'A'}
                  </div>
                  <div style={{ 
                    backgroundColor: msg.role === 'user' ? 'var(--border-color)' : 'transparent',
                    padding: msg.role === 'user' ? '12px 18px' : '6px 0',
                    borderRadius: '16px',
                    borderTopRightRadius: msg.role === 'user' ? '4px' : '16px',
                    borderTopLeftRadius: msg.role === 'ai' ? '4px' : '16px',
                    lineHeight: '1.6',
                    fontSize: '1rem',
                    color: '#e0e0e0',
                    position: 'relative'
                  }}>
                    {msg.image && (
                      <div style={{ marginBottom: '10px' }}>
                        <img src={msg.image} alt="Uploaded" style={{ maxWidth: '300px', maxHeight: '300px', borderRadius: '8px', border: '1px solid #444', objectFit: 'contain' }} />
                      </div>
                    )}
                    {msg.visual && msg.visual.media_type === 'image' && (
                      <div style={{ marginBottom: '16px', borderRadius: '12px', overflow: 'hidden', border: '1px solid var(--border-color)', boxShadow: '0 4px 20px rgba(0,0,0,0.3)', width: 'fit-content' }}>
                        <img src={msg.visual.url} alt={msg.visual.alt} style={{ maxWidth: '400px', maxHeight: '300px', width: '100%', objectFit: 'cover', display: 'block' }} />
                      </div>
                    )}
                    {renderMessageContent(msg.content + (idx === chatMessages.length - 1 && isChatLoading && msg.role === 'ai' ? ' ▋' : ''), (jsonStr) => { setActiveArchitecture(jsonStr); setStep(4); })}
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
                        background: 'none', border: 'none', color: 'var(--modal-text-color)', cursor: 'pointer',
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
            flexDirection: 'column',
            alignItems: 'center',
            padding: '0 20px'
          }}>
            {/* Image Preview Thumbnail */}
            {selectedImages.length > 0 && (
              <div style={{
                position: 'relative',
                marginBottom: '10px',
                width: '100%',
                maxWidth: '800px',
                display: 'flex',
                gap: '12px',
                overflowX: 'auto',
                padding: '4px 0'
              }}>
                {selectedImages.map((img, idx) => (
                  <div key={idx} style={{ position: 'relative', display: 'inline-block' }}>
                    <img src={img} alt={`Upload preview ${idx}`} style={{ height: '60px', borderRadius: '8px', border: '2px solid #444', objectFit: 'cover' }} />
                    <button 
                      type="button"
                      onClick={() => setSelectedImages(prev => prev.filter((_, i) => i !== idx))} 
                      style={{ position: 'absolute', top: '-8px', right: '-8px', background: '#ef4444', color: 'white', border: 'none', borderRadius: '50%', width: '22px', height: '22px', fontSize: '14px', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', boxShadow: '0 2px 5px rgba(0,0,0,0.3)' }}
                    >×</button>
                  </div>
                ))}
              </div>
            )}
            
            {chatStatus && (
              <div style={{
                marginBottom: '12px',
                padding: '8px 16px',
                backgroundColor: 'rgba(10, 10, 10, 0.7)',
                border: '1px solid var(--border-color)',
                borderRadius: '16px',
                color: '#a6accd',
                fontSize: '0.85rem',
                display: 'flex',
                alignItems: 'center',
                gap: '10px',
                animation: 'fadeIn 0.3s ease-in-out'
              }}>
                <div className="spinner" style={{ width: '14px', height: '14px', borderWidth: '2px', borderTopColor: 'var(--accent)' }}></div>
                ✨ {chatStatus}
              </div>
            )}

            <form onSubmit={handleChatSubmit} style={{ 
              width: '100%', 
              maxWidth: '800px', 
              backgroundColor: 'var(--btn-bg)', 
              borderRadius: '24px', 
              padding: '8px', 
              display: 'flex', 
              alignItems: 'center', 
              border: '1px solid var(--border-color)',
              boxShadow: '0 10px 30px rgba(0,0,0,0.5)'
            }}>
              <input type="file" multiple accept="image/*" ref={fileInputRef} onChange={handleImageUpload} style={{ display: 'none' }} />
              <button 
                type="button" 
                onClick={() => fileInputRef.current?.click()}
                style={{
                  background: 'none', 
                  border: 'none', 
                  color: 'var(--modal-text-color)',
                  fontSize: '1.4rem', 
                  cursor: 'pointer', 
                  padding: '0 12px', 
                  transition: 'color 0.2s',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center'
                }}
                title="Attach Image"
                onMouseEnter={(e) => e.target.style.color = '#fff'}
                onMouseLeave={(e) => e.target.style.color = '#888'}
              >
                +
              </button>
              <input 
                type="text" 
                value={chatInput} 
                onChange={(e) => setChatInput(e.target.value)} 
                placeholder={step === 1 ? "Message AiON..." : "Update your app..."} 
                style={{ 
                  flex: 1, 
                  minWidth: 0,
                  padding: '12px 20px', 
                  backgroundColor: 'transparent', 
                  border: 'none', 
                  color: 'var(--text-primary)', 
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
                  backgroundColor: (isChatLoading || !chatInput.trim()) ? 'var(--border-color)' : 'var(--accent)', 
                  border: 'none', 
                  color: 'var(--text-primary)', 
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
          <div className="preview-section" style={{ flex: 1, minHeight: 0, backgroundColor: '#0a0a0a', display: 'flex', flexDirection: 'column', position: 'relative' }}>
            
            {/* WORKSPACE CONTENT */}
            <div style={{ flex: 1, overflowY: 'auto', padding: '30px' }}>
              
              {/* STEP 2: REVIEW BLUEPRINT */}
              {step === 2 && (
                <div style={{ animation: 'fadeIn 0.5s ease-out' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
                    <h2 style={{ margin: 0, fontWeight: '500' }}>Architect's Blueprint</h2>
                    <button onClick={handleGenerate} disabled={isLoading} style={{ padding: '10px 20px', borderRadius: '8px', backgroundColor: 'var(--accent)', color: 'var(--text-primary)', border: 'none', fontWeight: 'bold', cursor: isLoading ? 'not-allowed' : 'pointer' }}>
                      {isLoading ? 'Generating Code...' : 'Approve & Build'}
                    </button>
                  </div>
                  <p style={{ color: 'var(--modal-text-color)', marginBottom: '20px' }}>Review the proposed architecture below. You can edit the JSON directly before building.</p>
                  
                  <textarea 
                      style={{ width: '100%', height: 'calc(100dvh - 250px)', backgroundColor: '#1e1e1e', color: '#00ff00', padding: '20px', fontFamily: 'monospace', borderRadius: '12px', border: '1px solid var(--border-color)', resize: 'none', outline: 'none' }}
                      value={blueprintJson}
                      onChange={(e) => setBlueprintJson(e.target.value)}
                      disabled={isLoading}
                  />
                </div>
              )}

              {/* STEP 4: ARCHITECTURE STUDIO */}
              {step === 4 && activeArchitecture && (
                <div style={{ animation: 'fadeIn 0.5s ease-out', width: '100%', height: 'calc(100dvh - 60px)', display: 'flex', flexDirection: 'column' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                    <h2 style={{ margin: 0, fontWeight: '500' }}>AiON Architect Studio</h2>
                  </div>
                  <div style={{ flex: 1, backgroundColor: '#0a0a0a', borderRadius: '12px', border: '1px solid var(--border-color)', overflow: 'hidden' }}>
                    <ArchitectureViewer architectureJson={activeArchitecture} />
                  </div>
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
                style={{width: '100%', minHeight: '300px', backgroundColor: '#1e1e1e', color: 'var(--text-primary)', padding: '15px', fontFamily: 'monospace', borderRadius: '8px', border: '1px solid var(--border-color)'}}
                value={blueprintJson}
                onChange={(e) => setBlueprintJson(e.target.value)}
                disabled={isLoading}
            />
            <div style={{display: 'flex', gap: '10px', marginTop: '15px'}}>
                <button className="build-btn" style={{backgroundColor: 'var(--border-color)'}} onClick={() => setStep(1)} disabled={isLoading || isPlanning}>
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
                <div className="preview-section" style={{ display: 'flex', flexDirection: 'column', gap: '24px', animation: 'fadeIn 0.5s ease-out' }}>
                  
                  {/* Phase 7: Live Preview */}
                  <div style={{ backgroundColor: 'var(--sidebar-bg)', borderRadius: '12px', border: '1px solid var(--border-color)', overflow: 'hidden' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '15px 20px', borderBottom: '1px solid var(--border-color)', backgroundColor: 'var(--sidebar-bg)' }}>
                        <h3 style={{ margin: 0, fontSize: '1.1rem', fontWeight: '500' }}>Live Preview</h3>
                        <div style={{ display: 'flex', gap: '10px' }}>
                            {!isPreviewRunning ? (
                                <button onClick={handleStartPreview} disabled={isLoading} style={{ padding: '6px 14px', borderRadius: '6px', fontSize: '0.85rem', fontWeight: 'bold', border: 'none', cursor: 'pointer', background: 'linear-gradient(135deg, #10b981, #059669)', color: 'var(--text-primary)' }}>
                                    ▶ Start
                                </button>
                            ) : (
                                <button onClick={handleStopPreview} style={{ padding: '6px 14px', borderRadius: '6px', fontSize: '0.85rem', fontWeight: 'bold', border: 'none', cursor: 'pointer', background: 'linear-gradient(135deg, #ef4444, #dc2626)', color: 'var(--text-primary)' }}>
                                    ⏹ Stop
                                </button>
                            )}
                            {isPreviewRunning && !isLoading && (
                                <button onClick={() => window.open(`http://localhost:${previewPort}`, '_blank')} style={{ padding: '6px 14px', borderRadius: '6px', fontSize: '0.85rem', fontWeight: 'bold', border: 'none', cursor: 'pointer', background: 'linear-gradient(135deg, #a855f7, #9333ea)', color: 'var(--text-primary)' }}>
                                    ↗ New Tab
                                </button>
                            )}
                            <button onClick={() => window.location.href = `${API_URL}/api/download`} style={{ padding: '6px 14px', borderRadius: '6px', fontSize: '0.85rem', fontWeight: 'bold', border: 'none', cursor: 'pointer', background: 'linear-gradient(135deg, #3b82f6, #2563eb)', color: 'var(--text-primary)' }}>
                                ↓ Download
                            </button>
                        </div>
                    </div>
                    
                    {isPreviewRunning && !isLoading && (
                        <div style={{ width: '100%', height: '500px', backgroundColor: '#fff', borderRadius: '12px', overflow: 'hidden', border: '1px solid var(--border-color)' }}>
                            <iframe 
                                src={`http://localhost:${previewPort}`} 
                                width="100%" height="100%" frameBorder="0" title="Live Preview" 
                            />
                        </div>
                    )}
                    {isPreviewRunning && isLoading && (
                        <div style={{ width: '100%', height: '200px', display: 'flex', justifyContent: 'center', alignItems: 'center', flexDirection: 'column', gap: '15px' }}>
                            <div className="spinner" style={{ width: '30px', height: '30px' }}></div>
                            <p style={{ color: 'var(--modal-text-color)' }}>Booting up server and opening tab...</p>
                        </div>
                    )}
                  </div>

                  <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: '24px' }}>
                      {/* Code Files (Simplified for Workspace) */}
                      <div style={{ backgroundColor: 'var(--sidebar-bg)', borderRadius: '12px', border: '1px solid var(--border-color)', padding: '20px' }}>
                        <h3 style={{ margin: '0 0 15px 0', fontSize: '1.1rem', fontWeight: '500' }}>Generated Files</h3>
                        <div style={{ maxHeight: '400px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '15px' }}>
                          {Object.entries(codeFiles || {}).map(([path, content]) => (
                            <div key={path} style={{ border: '1px solid var(--border-color)', borderRadius: '8px', overflow: 'hidden' }}>
                              <div style={{ backgroundColor: 'var(--sidebar-bg)', padding: '8px 12px', borderBottom: '1px solid var(--border-color)', fontSize: '0.85rem', color: 'var(--modal-text-color)', fontFamily: 'monospace' }}>📄 {path}</div>
                              <pre style={{ margin: 0, padding: '15px', backgroundColor: 'var(--input-bg)', color: '#a6accd', fontSize: '0.85rem', overflowX: 'auto' }}>{content}</pre>
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
                     <h3 style={{ margin: 0, fontWeight: '500', color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '10px' }}>
                        <div className="spinner" style={{ width: '20px', height: '20px' }}></div>
                        Writing Code...
                     </h3>
                     <span style={{ color: 'var(--modal-text-color)', fontSize: '0.9rem' }}>Streaming Live from AiON Coder Agent</span>
                  </div>
                  
                  <div style={{ flex: 1, backgroundColor: 'var(--input-bg)', borderRadius: '12px', border: '1px solid var(--border-color)', overflow: 'hidden', display: 'flex', flexDirection: 'column', boxShadow: '0 10px 40px rgba(0,0,0,0.5)' }}>
                     {/* Tab Bar */}
                     <div style={{ backgroundColor: 'var(--sidebar-bg)', padding: '10px 15px', borderBottom: '1px solid var(--border-color)', display: 'flex', gap: '10px', overflowX: 'auto' }}>
                        {Object.keys(liveCodeFiles).map(file => (
                           <div key={file} style={{ padding: '6px 12px', backgroundColor: 'var(--border-color)', borderRadius: '6px', fontSize: '0.85rem', color: 'var(--text-primary)', whiteSpace: 'nowrap', border: '1px solid #444' }}>
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
        
        {/* SETTINGS MODAL */}
        {showSettingsModal && (
          <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, backgroundColor: 'var(--modal-overlay)', display: 'flex', justifyContent: 'center', alignItems: 'center', zIndex: 999 }}>
            <div style={{ backgroundColor: 'var(--sidebar-bg)', padding: '30px', borderRadius: '16px', width: '90%', maxWidth: '400px', border: '1px solid var(--border-color)', boxShadow: '0 20px 40px rgba(0,0,0,0.5)' }}>
              <h2 style={{ margin: '0 0 20px 0', fontSize: '1.5rem', fontWeight: '600' }}>Settings</h2>
              
              <div style={{ marginBottom: '20px' }}>
                <label style={{ display: 'block', color: 'var(--modal-text-color)', marginBottom: '8px', fontSize: '0.9rem' }}>Account Email</label>
                <div style={{ padding: '12px', backgroundColor: 'var(--input-bg)', border: '1px solid var(--border-color)', borderRadius: '8px', color: 'var(--text-secondary)' }}>
                  {session?.user?.email}
                </div>
              </div>
              


              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px' }}>
                <button onClick={() => setShowSettingsModal(false)} style={{ padding: '10px 20px', backgroundColor: 'var(--accent)', color: 'var(--text-primary)', border: 'none', borderRadius: '8px', cursor: 'pointer', fontWeight: 'bold' }}>
                  Save & Close
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
      
      {/* Tutor Chat Widget */}
      <Chat />
    </div>
  )
}

export default App
