with open('frontend/src/App.jsx', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Add userMemory state
if "const [userMemory, setUserMemory]" not in content:
    content = content.replace(
        "const [chatInput, setChatInput] = useState('')",
        "const [userMemory, setUserMemory] = useState(() => localStorage.getItem('aion_memory') || '')\n  const [chatInput, setChatInput] = useState('')"
    )

# 2. Update POST request body
if "memory: userMemory" not in content:
    content = content.replace(
        "body: JSON.stringify({ message: userMessage, history: chatMessages, image: imagePayload })",
        "body: JSON.stringify({ message: userMessage, history: chatMessages, image: imagePayload, memory: userMemory })"
    )

# 3. Intercept [MEMORY_ADD] after streaming loop finishes
memory_interceptor_code = """      }
      
      // Process Memory Tags after stream completes
      setChatMessages(prev => {
          const newMsgs = [...prev];
          let finalMsg = newMsgs[newMsgs.length - 1].content;
          const memoryMatch = finalMsg.match(/\\[MEMORY_ADD\\](.*)/);
          if (memoryMatch) {
              const newFact = memoryMatch[1].trim();
              setUserMemory(prevMem => {
                  const updatedMem = prevMem + (prevMem ? '\\n' : '') + "- " + newFact;
                  localStorage.setItem('aion_memory', updatedMem);
                  return updatedMem;
              });
              finalMsg = finalMsg.replace(/\\[MEMORY_ADD\\].*/, '').trim();
              newMsgs[newMsgs.length - 1].content = finalMsg;
          }
          return newMsgs;
      });

    } catch (err) {"""

if "// Process Memory Tags after stream completes" not in content:
    content = content.replace("      }\n      \n    } catch (err) {", memory_interceptor_code)

with open('frontend/src/App.jsx', 'w', encoding='utf-8') as f:
    f.write(content)
print("Frontend memory updated successfully.")
