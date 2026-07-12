import asyncio
from backend.gateway import AIGateway
from backend.orchestrator.state import AiONState
from queue import Queue

prompt = """
### **Library Management System Overview**
#### A Comprehensive System for Efficient Library Operations

### **System Requirements**
* User-friendly interface for patrons and librarians
* Efficient cataloging and borrowing system
* Real-time tracking of book availability and reservations
* Automated reminders and notifications for due dates and renewals
* Scalable architecture for easy integration with existing systems

### **System Components**
#### **Patron Module**
* User registration and login system
* Profile management for patrons
* Search and reserve books functionality
* Borrowing and returning books with due date tracking

#### **Librarian Module**
* User registration and login system
* Profile management for librarians
* Cataloging and classification of books
* Borrowing and returning books with due date tracking
* Real-time tracking of book availability and reservations

#### **System Architecture**
* **Database**: MySQL or PostgreSQL for efficient data storage and retrieval
* **Frontend**: React or Angular for a user-friendly interface
* **Backend**: Node.js or Django for efficient API handling and data processing
* **Scalability**: Microservices architecture for easy integration with existing systems
"""

def test_routing():
    gateway = AIGateway()
    state = AiONState(goal=prompt, project_id="test1234", revision_count=0, execution_retries=0, visual_revision_count=0)
    q = Queue()
    
    # We will just patch _run_builder, _run_quick_chat, _run_specialist to intercept
    def mock_run_builder(state, q, project_id):
        print("SUCCESS! Gateway routed to BUILDER mode.")
        return state
        
    def mock_run_quick_chat(state, q):
        print("FAIL! Gateway routed to QUICK CHAT mode.")
        return state
        
    def mock_run_specialist(state, q, goal):
        print("FAIL! Gateway routed to SPECIALIST mode.")
        return state
        
    def mock_run_safety(state):
        return state
        
    gateway._run_builder = mock_run_builder
    gateway._run_quick_chat = mock_run_quick_chat
    gateway._run_specialist = mock_run_specialist
    gateway._run_safety_check = mock_run_safety
    
    gateway.run(state, q, "test1234")

if __name__ == "__main__":
    test_routing()
