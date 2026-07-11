import { useState, useEffect, useRef } from 'react'
import './App.css'
import Auth from './components/Auth'
import Chat from './components/Chat'
import { supabase } from './lib/supabaseClient'
import ArchitectureViewer from './components/ArchitectureViewer'
import ArtifactViewer from './components/ArtifactViewer'
import ProgressDashboard from './components/ProgressDashboard'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import remarkBreaks from 'remark-breaks'
import PlatformDashboards from './components/PlatformDashboards'

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
      const res = await fetch(`${apiUrl}/api/run-code`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          language: pistonLang,
          code: btoa(unescape(encodeURIComponent(code))),
          is_base64: true
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
  
  const parts = content.split(/(<architecture>[\s\S]*?(?:<\/architecture>|$))/);
  return parts.map((part, i) => {
      if (part.startsWith('<architecture>')) {
          if (part.endsWith('</architecture>')) {
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
          } else {
              // Streaming/Incomplete state
              return (
                <div key={i} style={{ margin: '16px 0', padding: '12px 20px', backgroundColor: 'rgba(59, 130, 246, 0.1)', border: '1px solid rgba(59, 130, 246, 0.3)', borderRadius: '8px', display: 'flex', alignItems: 'center', gap: '12px', color: '#60a5fa' }}>
                  <div className="spinner" style={{ width: '16px', height: '16px', borderWidth: '2px', borderTopColor: '#60a5fa' }}></div>
                  <span style={{ fontWeight: '500' }}>Designing your architecture...</span>
                </div>
              );
          }
      }
      
      if (!part.trim()) return null;
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
  
  const [activeView, setActiveView] = useState('workspace'); // 'workspace' | 'dashboards'
  
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
  const [previewUrl, setPreviewUrl] = useState(null)
  const [previewError, setPreviewError] = useState(null)
  const [isBackend, setIsBackend] = useState(false)
  
  // Streaming state  
  const [streamedCode, setStreamedCode] = useState("")
  const [streamFileName, setStreamFileName] = useState("")
  const streamBufferRef = useRef("")
  const streamFileNameRef = useRef("")
  
  const [liveUpdates, setLiveUpdates] = useState([])
  const [agentState, setAgentState] = useState({
    activeAgent: null,
    timeline: []
  })

  
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
  const [selectedNode, setSelectedNode] = useState(null)

  const chatEndRef = useRef(null)

  // Advanced Streaming Engine: Flush JS Buffer to React State using RequestAnimationFrame
  useEffect(() => {
    let animationFrameId;
    const flushBuffer = () => {
      if (streamBufferRef.current !== "") {
        setStreamedCode(prev => prev + streamBufferRef.current);
        streamBufferRef.current = ""; // Clear buffer after flush
      }
      animationFrameId = requestAnimationFrame(flushBuffer);
    };
    animationFrameId = requestAnimationFrame(flushBuffer);
    return () => cancelAnimationFrame(animationFrameId);
  }, []);

  // Cloud Sync Logic
  const saveTimeoutRef = useRef(null);
  const syncToCloud = (historyList) => {
      if (!session?.access_token) return;
      if (saveTimeoutRef.current) clearTimeout(saveTimeoutRef.current);
      
      saveTimeoutRef.current = setTimeout(() => {
          fetch(`${API_URL}/api/user/history`, {
              method: 'POST',
              headers: { 
                  'Content-Type': 'application/json',
                  'Authorization': `Bearer ${session.access_token}`
              },
              body: JSON.stringify({ history: historyList })
          }).catch(err => console.error("Failed to sync history to cloud", err));
      }, 1500); // 1.5s debounce
  };

  // Load chat history from localStorage on mount, then sync from Cloud
  useEffect(() => {
    try {
        const savedHistory = localStorage.getItem('aion_chat_history');
        if (savedHistory) {
            setChatHistoryList(JSON.parse(savedHistory));
        }
    } catch (e) {}
    
    if (session?.access_token) {
        fetch(`${API_URL}/api/user/history`, {
            headers: { 'Authorization': `Bearer ${session.access_token}` }
        })
        .then(res => res.json())
        .then(data => {
            const savedHistoryStr = localStorage.getItem('aion_chat_history');
            let localData = savedHistoryStr ? JSON.parse(savedHistoryStr) : [];
            
            if (data && data.history && data.history.length > 0) {
                // Merge cloud and local data
                let merged = [...data.history];
                let hasLocalChanges = false;
                
                localData.forEach(localChat => {
                    const exists = merged.find(c => c.id === localChat.id);
                    if (!exists) {
                        merged.push(localChat);
                        hasLocalChanges = true;
                    } else if (localChat.timestamp > exists.timestamp) {
                        // If local chat is newer, overwrite the cloud version
                        merged = merged.map(c => c.id === localChat.id ? localChat : c);
                        hasLocalChanges = true;
                    }
                });
                
                // Sort by timestamp descending
                merged.sort((a, b) => b.timestamp - a.timestamp);
                
                setChatHistoryList(merged);
                localStorage.setItem('aion_chat_history', JSON.stringify(merged));
                
                // Sync back to cloud if we merged local data
                if (hasLocalChanges) {
                    syncToCloud(merged);
                }
            } else if (localData.length > 0) {
                // Cloud is empty, push local data to cloud
                syncToCloud(localData);
            }
        })
        .catch(err => console.error("Failed to load chat history from cloud", err));
    }
  }, [session?.access_token]);

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
          } catch (e) {}
          
          syncToCloud(newList);
          
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
        syncToCloud(newList);
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
        syncToCloud(newList);
        
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
      document.querySelector('input[placeholder="Message yAI..."]')?.focus()
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
    if (isRecording) return;
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      alert("Voice AI requires Google Chrome, Edge, or Safari to function.");
      return;
    }
    try {
        const recognition = new SpeechRecognition();
        recognition.continuous = false;
        recognition.interimResults = false;
        
        recognition.onstart = () => {
            setIsRecording(true);
            window.isVoiceMode = true; // Flag for TTS playback
        };
        recognition.onresult = (event) => {
            const transcript = event.results[0][0].transcript;
            setChatInput(transcript);
            handleChatSubmit(null, transcript);
        };
        recognition.onerror = (event) => {
            console.error("Speech recognition error", event.error);
            setIsRecording(false);
        };
        recognition.onend = () => setIsRecording(false);
        recognition.start();
    } catch(err) {
        console.error(err);
        setIsRecording(false);
    }
  }

  const handleChatSubmit = async (e, directMessage = null) => {
    if (e) e.preventDefault()
    
    const userMessage = directMessage || chatInput
    if (!userMessage.trim() && selectedImages.length === 0) return
    
    const imagePayload = selectedImages.length > 0 ? selectedImages : null
    
    // Add User message immediately
    const userMsgObj = { role: 'user', content: userMessage };
    if (imagePayload) userMsgObj.image = imagePayload;
    
    setChatMessages(prev => [...prev, userMsgObj])
    setChatInput('')
    setSelectedImages([])
    setIsChatLoading(true)
    
    try {
      setChatMessages(prev => [...prev, { role: 'ai', content: '' }])
      
      const payload = { 
        message: userMessage, 
        history: chatMessages, 
        image: imagePayload 
      };
      
      // If we are in ArtifactViewer (Step 3), pass the projectId so backend knows to Refine
      if (step === 3 && projectId) {
        payload.projectId = projectId;
      }

      let wakeTimer = setTimeout(() => {
          setChatStatus("✨ Generating...");
      }, 3000);

      const response = await fetch(`${API_URL}/api/chat`, {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${session?.access_token || 'mock-token-for-local-dev'}`
        },
        body: JSON.stringify(payload)
      })
      
      clearTimeout(wakeTimer);
      
      if (!response.ok) {
        setIsChatLoading(false)
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
                    } else if (data.type === 'visual') {
                        // Use the beautiful dedicated visual card renderer (supports multiple images)
                        setChatMessages(prev => {
                            const newMsgs = [...prev];
                            const lastMsg = newMsgs[newMsgs.length - 1];
                            const existingVisuals = lastMsg.visuals || [];
                            newMsgs[newMsgs.length - 1] = {
                                ...lastMsg,
                                visuals: [...existingVisuals, data]
                            };
                            return newMsgs;
                        });
                    } else if (data.type === 'fast_build') {
                        setChatMessages(prev => {
                            const newMsgs = [...prev];
                            newMsgs[newMsgs.length - 1].content = `⚡ 0-Shot Fast Lane Execution...\nGoal: ${data.data.goal}`;
                            return newMsgs;
                        });
                        setGoal(data.data.goal);
                        // Trigger fast generation directly
                        handleFastGenerate(data.data.goal, data.data.agent_role);
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
                    } else if (data.type === 'refine_file') {
                        // Seamlessly update codeFiles without a full rebuild!
                        setCodeFiles(prev => ({
                            ...prev,
                            [data.file]: data.content
                        }));
                    } else if (data.type === 'refine_done') {
                        setChatStatus('');
                        // Trigger an iframe refresh by toggling isPreviewRunning
                        setIsPreviewRunning(false);
                        setTimeout(() => setIsPreviewRunning(true), 500);
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
          
          // Trigger Voice AI Text-to-Speech if active
          if (window.isVoiceMode && window.speechSynthesis) {
              window.isVoiceMode = false;
              // Strip markdown from AI response for clean speech
              const cleanText = finalMsg.replace(/```[\s\S]*?```/g, 'Here is the code.').replace(/[#*_~>]/g, '').trim();
              if (cleanText) {
                  const utterance = new SpeechSynthesisUtterance(cleanText);
                  utterance.rate = 1.05;
                  utterance.pitch = 1;
                  window.speechSynthesis.speak(utterance);
              }
          }
          
          return newMsgs;
      });
      setIsChatLoading(false);
      setChatStatus("");

    } catch (err) {
      setIsChatLoading(false);
      setChatStatus("");
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

  const handleFastGenerate = async (fastGoal, role) => {
    setIsLoading(true);
    setError(null);
    setLiveUpdates([]);
    setAgentState({ activeAgent: 'coder', timeline: [] });
    setAwaitingApproval(false);
    setStep(2); // Move to coding view
    
    let parsedBlueprint = { tech_stack: [], file_structure: [], blueprint_notes: "" };
    try {
        if (blueprintJson) {
            let cleanJson = blueprintJson.replace(/```json/g, '').replace(/```/g, '').trim();
            const startIdx = cleanJson.indexOf('{');
            const endIdx = cleanJson.lastIndexOf('}');
            if (startIdx !== -1 && endIdx !== -1) cleanJson = cleanJson.substring(startIdx, endIdx + 1);
            parsedBlueprint = JSON.parse(cleanJson);
        }
    } catch (e) {
        console.warn("No valid blueprint found, proceeding zero-shot.");
    }
    
    // Auto-generate project ID if this is a true 0-shot without prior context
    const currentProjectId = projectId || `proj-${Math.random().toString(36).substr(2, 8)}`;
    if (!projectId) setProjectId(currentProjectId);

    try {
      const ws = new WebSocket(`${WS_URL}/api/ws/generate`)
      
      ws.onopen = () => {
        ws.send(JSON.stringify({ 
            project_id: currentProjectId,
            goal: fastGoal,
            blueprint: parsedBlueprint,
            agent_role: role,
            execution_mode: "fast",
            code_files: codeFiles // Pass existing files so backend can edit them
        }))
      }
      
      // We will reuse the same message handler for generation
      ws.onmessage = (event) => {
        const data = JSON.parse(event.data)
        if (data.type === 'token') {
          // Ignore architect tokens in fast mode
        } else if (data.type === 'agent_state') {
          setAgentState(prev => ({ ...prev, activeAgent: data.agent }))
        } else if (data.type === 'timeline') {
          setAgentState(prev => ({
            ...prev,
            timeline: [...prev.timeline, { title: data.title, reason: data.reason, status: data.status }]
          }))
        } else if (data.type === 'timeline_update') {
          setAgentState(prev => {
            const newTimeline = [...prev.timeline]
            if (newTimeline.length > 0) {
              newTimeline[newTimeline.length - 1].status = data.status
            }
            return { ...prev, timeline: newTimeline }
          })
        } else if (data.type === 'progress') {
          setLiveUpdates(prev => [...prev.slice(-4), data.message])
        } else if (data.type === 'file_created') {
          setCodeFiles(prev => ({ ...prev, [data.file]: data.content }))
        } else if (data.type === 'error') {
          setError(data.message)
          setIsLoading(false)
        } else if (data.type === 'done') {
          setIsLoading(false)
          setStep(3)
        }
      }
      
      ws.onerror = () => {
        setError("WebSocket connection failed")
        setIsLoading(false)
      }
      
      ws.onclose = () => {
        if (isLoading) setIsLoading(false)
      }
    } catch (err) {
      setError(err.message)
      setIsLoading(false)
    }
  }

  const handleGenerate = async (e) => {
    if (e && e.preventDefault) e.preventDefault();
    setIsLoading(true)
    setError(null)
    setLiveUpdates([])
    setAgentState({ activeAgent: 'architect', timeline: [] })
    setAwaitingApproval(false)
    
    let parsedBlueprint;
    let rawJson = blueprintJson.trim();
    try {
        // Strip out any trailing markdown ticks and text before/after JSON
        rawJson = rawJson.replace(/```json/g, '').replace(/```/g, '').trim();
        const startIdx = rawJson.indexOf('{');
        const endIdx = rawJson.lastIndexOf('}');
        if (startIdx !== -1 && endIdx !== -1) rawJson = rawJson.substring(startIdx, endIdx + 1);
        
        // Strip trailing commas before closing braces/brackets (common LLM hallucination)
        rawJson = rawJson.replace(/,(?=\s*[}\]])/g, '');
        
        parsedBlueprint = JSON.parse(rawJson);
    } catch (e) {
        try {
            // Attempt auto-repair for truncated JSON arrays/objects
            if (rawJson.endsWith(',')) rawJson = rawJson.slice(0, -1);
            if (rawJson.endsWith('"')) rawJson += '"]}'; // cut off mid-string in file_structure
            else if (!rawJson.endsWith('}')) {
                if (rawJson.includes('"file_structure": [') && !rawJson.includes(']')) {
                    rawJson += ']}';
                } else {
                    rawJson += '}';
                }
            }
            // Strip trailing commas one last time just in case the repair added something weird
            rawJson = rawJson.replace(/,(?=\s*[}\]])/g, '');
            
            parsedBlueprint = JSON.parse(rawJson);
        } catch (repairError) {
            setError("Invalid JSON format in Blueprint! Scroll down and fix the missing brackets or trailing commas.");
            setIsLoading(false);
            return;
        }
    }

    try {
      const currentProjectId = projectId || `proj-${Math.random().toString(36).substr(2, 8)}`;
      if (!projectId) setProjectId(currentProjectId);
      
      const ws = new WebSocket(`${WS_URL}/api/ws/generate`)
      
      ws.onopen = () => {
        ws.send(JSON.stringify({ 
            project_id: currentProjectId,
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
          setLiveUpdates(prev => [...prev, `Writing code for ${data.file}...`])
          setStreamFileName(data.file)
          streamFileNameRef.current = data.file;
          streamBufferRef.current = ""; // Reset buffer for new file
          setStreamedCode(""); // Reset UI state for new file
        } else if (data.type === "code_token") {
          // Push to JS buffer instead of React State to prevent 100hz re-renders
          if (data.file === streamFileNameRef.current) {
            streamBufferRef.current += data.token;
          }

        } else if (data.type === "code_complete") {
          // [ZERO-LATENCY] Instantly unlock the UI and show the Artifact Viewer!
          setCodeFiles(data.code_files)
          setStep(3)
          setIsLoading(false)
        } else if (data.type === "complete") {
          // The background executor has finished. Update any final logs.
          if (data.code_files) setCodeFiles(data.code_files)
          setExecutionLogs(data.execution_logs)
          setStep(3)
          setIsLoading(false)
          // Keep ws open to receive PREVIEW_READY
        } else if (data.type === "INTERRUPT") {
          setAwaitingApproval(true)
          setLiveUpdates(prev => [...prev, "⏸️ " + data.message])
        } else if (data.type === "PREVIEW_ERROR") {
          setAgentState(prev => ({ ...prev, activeAgent: 'error' }))
          setPreviewError(data.message)
          setIsBackend(true) // So ExecutionManager routes to BackendSandbox to show the error
          setIsPreviewRunning(true)
          ws.close()
        } else if (data.type === "PREVIEW_READY") {
          setAgentState(prev => ({ ...prev, activeAgent: 'ready' }))
          setPreviewError(null)
          if (data.isBackend) {
             setPreviewUrl(data.url);
             setIsBackend(true);
          } else {
             setPreviewUrl(null);
             setIsBackend(false);
          }
          setIsPreviewRunning(true)
          ws.close()
        } else if (data.type === "agent_state") {
          setAgentState(prev => ({ ...prev, activeAgent: data.agent }))
        } else if (data.type === "timeline") {
          setAgentState(prev => ({ 
            ...prev, 
            timeline: [...prev.timeline, { title: data.title, reason: data.reason, status: data.status }] 
          }))
        } else if (data.type === "timeline_update") {
          setAgentState(prev => {
            const newTimeline = [...prev.timeline];
            if (newTimeline.length > 0) {
               newTimeline[newTimeline.length - 1].status = data.status;
            }
            return { ...prev, timeline: newTimeline };
          });
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
          <h1 style={{ margin: 0, fontSize: '1.2rem', letterSpacing: '1px', fontWeight: '600' }}>yAI</h1>
        </div>
        <div style={{ display: 'flex', gap: '12px' }}>
          <button 
            onClick={() => setActiveView(activeView === 'workspace' ? 'dashboards' : 'workspace')}
            style={{ 
              background: 'linear-gradient(135deg, rgba(59, 130, 246, 0.2), rgba(37, 99, 235, 0.2))', 
              border: '1px solid rgba(59, 130, 246, 0.5)', 
              color: 'var(--accent)', 
              padding: '6px 12px', 
              borderRadius: '8px', 
              cursor: 'pointer', 
              fontWeight: '600',
              display: 'flex',
              alignItems: 'center',
              gap: '6px'
            }}
          >
            {activeView === 'workspace' ? '📊 Open Dashboards' : '💻 Back to Workspace'}
          </button>
        </div>
      </header>
      
      {/* MAIN CONTENT AREA */}
      <div className="main-content-wrapper" style={{ display: 'flex', flex: 1, overflow: 'hidden', position: 'relative' }}>
        
        {activeView === 'dashboards' ? (
           <div style={{ flex: 1, width: '100%', backgroundColor: 'var(--app-bg)' }}>
              <PlatformDashboards API_URL={API_URL} />
           </div>
        ) : (
           <>
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
              yAI 2.0
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
                    {msg.visuals && msg.visuals.length > 0 && (
                      <div style={{ 
                          display: 'grid', 
                          gridTemplateColumns: msg.visuals.length > 1 ? 'repeat(auto-fit, minmax(200px, 1fr))' : '1fr', 
                          gap: '12px', 
                          marginBottom: '16px', 
                          width: '100%',
                          maxWidth: '600px'
                      }}>
                        {msg.visuals.filter(v => v.media_type === 'image').map((v, i) => (
                          <div key={i} style={{ borderRadius: '12px', overflow: 'hidden', border: '1px solid var(--border-color)', boxShadow: '0 4px 20px rgba(0,0,0,0.2)' }}>
                            <img src={v.url} alt={v.alt || 'Visual'} style={{ width: '100%', height: '100%', maxHeight: msg.visuals.length > 1 ? '200px' : '300px', objectFit: 'cover', display: 'block' }} />
                          </div>
                        ))}
                      </div>
                    )}
                    {console.log("RENDERING MSG CONTENT:", msg.content)}
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
                   <div style={{ width: '32px', height: '32px', borderRadius: '50%', backgroundColor: 'var(--accent)', display: 'flex', justifyContent: 'center', alignItems: 'center', color: '#fff', fontWeight: 'bold' }}>A</div>
                   <div style={{ padding: '6px 0', display: 'flex', alignItems: 'center', gap: '12px' }}>
                     <div className="spinner" style={{ width: '18px', height: '18px' }}></div>
                     {chatStatus && (
                         <span style={{ fontSize: '0.9rem', color: '#9ca3af', fontStyle: 'italic', animation: 'pulse 2s infinite' }}>{chatStatus}</span>
                     )}
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
                placeholder={step === 1 ? "Message yAI..." : "Update your app..."} 
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
                  cursor: 'pointer', 
                  padding: '0 10px', 
                  transition: 'all 0.2s',
                  transform: isRecording ? 'scale(1.05)' : 'scale(1)'
                }}
                title={isRecording ? "Listening..." : "Voice Input"}
              >
                {isRecording ? (
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px', background: 'rgba(239, 68, 68, 0.1)', padding: '6px 12px', borderRadius: '20px', border: '1px solid rgba(239, 68, 68, 0.3)' }}>
                        <span style={{ fontSize: '1rem', animation: 'pulse 1.5s infinite' }}>🔴</span>
                        <span style={{ fontSize: '0.8rem', fontWeight: '600', color: '#ef4444' }}>Listening</span>
                    </div>
                ) : (
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px', background: 'rgba(59, 130, 246, 0.1)', padding: '6px 12px', borderRadius: '20px', border: '1px solid rgba(59, 130, 246, 0.3)', transition: 'all 0.3s', boxShadow: '0 0 10px rgba(59, 130, 246, 0.1)' }} onMouseEnter={(e) => { e.currentTarget.style.background = 'rgba(59, 130, 246, 0.2)'; e.currentTarget.style.boxShadow = '0 0 15px rgba(59, 130, 246, 0.3)'; }} onMouseLeave={(e) => { e.currentTarget.style.background = 'rgba(59, 130, 246, 0.1)'; e.currentTarget.style.boxShadow = '0 0 10px rgba(59, 130, 246, 0.1)'; }}>
                        <span style={{ fontSize: '1rem' }}>✨</span>
                        <span style={{ fontSize: '0.8rem', fontWeight: '600', color: '#60a5fa', letterSpacing: '0.5px' }}>Voice AI</span>
                    </div>
                )}
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
              {step === 4 && activeArchitecture && (() => {
                const archData = typeof activeArchitecture === 'string' ? JSON.parse(activeArchitecture) : activeArchitecture;
                const review = archData.review;
                
                return (
                  <div style={{ animation: 'fadeIn 0.5s ease-out', width: '100%', height: 'calc(100dvh - 60px)', display: 'flex', flexDirection: 'column' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                      <h2 style={{ margin: 0, fontWeight: '500' }}>yAI Architect Studio</h2>
                      {review && review.score && (
                        <div style={{ background: 'rgba(16, 185, 129, 0.1)', border: '1px solid #10b981', color: '#10b981', padding: '6px 12px', borderRadius: '20px', fontWeight: 'bold', fontSize: '14px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                          <span>🏆 Architecture Score:</span> {review.score}/100
                        </div>
                      )}
                    </div>
                    <div style={{ flex: 1, display: 'flex', gap: '20px', overflow: 'hidden' }}>
                      <div style={{ flex: 1, backgroundColor: '#0a0a0a', borderRadius: '12px', border: '1px solid var(--border-color)', overflow: 'hidden' }} onClick={() => setSelectedNode(null)}>
                        <ArchitectureViewer architectureJson={activeArchitecture} onNodeSelect={setSelectedNode} />
                      </div>
                      
                    </div>
                  </div>
                );
              })()}

      {/* STEP 1: WELCOME SCREEN */}
      {step === 1 && !isLoading && (
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '60vh', color: 'var(--text-secondary)' }}>
          <div style={{ fontSize: '4rem', marginBottom: '20px' }}>🤖</div>
          <h2>Welcome to the Omni-Chat Builder</h2>
          <p>Talk to yAI Advisor on the left.</p>
          <p>Ask questions, or ask it to "build a new project" and watch the magic happen!</p>
        </div>
      )}

      {/* STEP 2: REVIEW BLUEPRINT */}
      {step === 2 && !isLoading && (
        <div className="results-section">
          <div className="glass-panel result-card">
            <h3>Architect's Blueprint</h3>
            {error && (
                <div style={{ backgroundColor: 'rgba(239, 68, 68, 0.2)', border: '1px solid #ef4444', color: '#fca5a5', padding: '12px', borderRadius: '8px', marginBottom: '15px', fontWeight: 'bold' }}>
                    {error}
                </div>
            )}
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

              {/* STEP 3: ARTIFACT VIEWER (CODE + PREVIEW) */}
              {step === 3 && (
                <div style={{ height: 'calc(100dvh - 60px)', animation: 'fadeIn 0.5s ease-out' }}>
                  <ArtifactViewer 
                    codeFiles={codeFiles} 
                    setCodeFiles={setCodeFiles}
                    onClose={() => setStep(0)} 
                    previewUrl={previewUrl}
                    previewError={previewError}
                    isBackend={isBackend}
                    projectId={projectId}
                    isPreviewRunning={isPreviewRunning}
                    previewPort={previewPort}
                    API_URL={API_URL}
                    executionLogs={executionLogs}
                  />
                </div>
              )}
              
              {/* LIVE PROGRESS DASHBOARD OVERLAY for Workspace */}
              {isLoading && step === 2 && (
                <div style={{ position: 'absolute', top: 0, left: 0, right: 0, bottom: 0, backgroundColor: 'rgba(10,10,10,0.95)', display: 'flex', flexDirection: 'column', zIndex: 50, padding: '30px', animation: 'fadeIn 0.3s ease-out' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
                     <h3 style={{ margin: 0, fontWeight: '500', color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '10px' }}>
                        {awaitingApproval ? (
                           <div style={{ width: '20px', height: '20px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>⏸️</div>
                        ) : (
                           <div className="spinner" style={{ width: '20px', height: '20px' }}></div>
                        )}
                        {awaitingApproval ? 'Paused for Approval' : 'yAI is engineering your application...'}
                     </h3>
                     <div style={{ display: 'flex', alignItems: 'center', gap: '15px' }}>
                       {awaitingApproval && (
                          <div style={{ display: 'flex', gap: '10px' }}>
                             <button 
                               onClick={() => handleResume('approve')}
                               style={{ padding: '6px 12px', backgroundColor: 'var(--accent-color)', color: 'white', border: 'none', borderRadius: '6px', fontWeight: '500', cursor: 'pointer', fontSize: '0.85rem' }}>
                               Approve
                             </button>
                             <button 
                               onClick={() => handleResume('abort')}
                               style={{ padding: '6px 12px', backgroundColor: 'transparent', color: 'var(--modal-text-color)', border: '1px solid var(--border-color)', borderRadius: '6px', fontWeight: '500', cursor: 'pointer', fontSize: '0.85rem' }}>
                               Abort
                             </button>
                          </div>
                       )}
                     </div>
                  </div>
                  
                  {/* Dashboard Component */}
                  <ProgressDashboard 
                     activeAgent={agentState.activeAgent} 
                     timeline={agentState.timeline} 
                     liveUpdates={liveUpdates} 
                     streamFileName={streamFileName}
                     streamedCode={streamedCode}
                  />
                </div>
              )}
            </div>
          </div>
        )}
           </>
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
      
      {/* Tutor Chat Widget Removed per user request */}
    </div>
  )
}

export default App
