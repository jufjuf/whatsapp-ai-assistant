#!/usr/bin/env python3
"""
WhatsApp Assistant with LLM Integration
A complete WhatsApp bot that can handle various tasks through natural language.
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from flask import Flask, request, jsonify
from twilio.rest import Client
from twilio.twiml.messaging_response import MessagingResponse
import openai
from dataclasses import dataclass
import sqlite3
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('whatsapp_assistant.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Twilio Configuration
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "your_account_sid_here")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "your_auth_token_here")
TWILIO_WHATSAPP_NUMBER = os.getenv("TWILIO_WHATSAPP_NUMBER", "whatsapp:+1234567890")

# Initialize Twilio client
twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

# Flask app
app = Flask(__name__)

@dataclass
class UserSession:
    """Represents a user session with conversation history."""
    phone_number: str
    conversation_history: list
    last_activity: datetime
    user_context: Dict[str, Any]

class ConversationManager:
    """Manages user conversations and context."""
    
    def __init__(self, db_path: str = "conversations.db"):
        self.db_path = Path(db_path)
        self.sessions: Dict[str, UserSession] = {}
        self._init_database()
    
    def _init_database(self):
        """Initialize SQLite database for conversation storage."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    phone_number TEXT NOT NULL,
                    message TEXT NOT NULL,
                    response TEXT NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    message_type TEXT DEFAULT 'text'
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS user_context (
                    phone_number TEXT PRIMARY KEY,
                    context_data TEXT,
                    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
    
    def get_session(self, phone_number: str) -> UserSession:
        """Get or create user session."""
        if phone_number not in self.sessions:
            # Load from database or create new
            context = self._load_user_context(phone_number)
            history = self._load_conversation_history(phone_number, limit=10)
            
            self.sessions[phone_number] = UserSession(
                phone_number=phone_number,
                conversation_history=history,
                last_activity=datetime.now(),
                user_context=context
            )
        
        return self.sessions[phone_number]
    
    def _load_user_context(self, phone_number: str) -> Dict[str, Any]:
        """Load user context from database."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT context_data FROM user_context WHERE phone_number = ?",
                (phone_number,)
            )
            result = cursor.fetchone()
            if result:
                return json.loads(result[0])
        return {}
    
    def _load_conversation_history(self, phone_number: str, limit: int = 10) -> list:
        """Load recent conversation history."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT message, response, timestamp FROM conversations 
                WHERE phone_number = ? 
                ORDER BY timestamp DESC 
                LIMIT ?
            """, (phone_number, limit))
            
            history = []
            for row in cursor.fetchall():
                history.extend([
                    {"role": "user", "content": row[0]},
                    {"role": "assistant", "content": row[1]}
                ])
            
            return list(reversed(history))  # Chronological order
    
    def save_conversation(self, phone_number: str, message: str, response: str):
        """Save conversation to database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO conversations (phone_number, message, response)
                VALUES (?, ?, ?)
            """, (phone_number, message, response))
    
    def update_user_context(self, phone_number: str, context: Dict[str, Any]):
        """Update user context in database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO user_context (phone_number, context_data)
                VALUES (?, ?)
            """, (phone_number, json.dumps(context)))

class LLMAssistant:
    """LLM-powered assistant with various capabilities."""
    
    def __init__(self):
        # You can use OpenAI, Anthropic, or any other LLM API
        # For this example, I'll use a simple response system
        # Replace with your preferred LLM integration
        self.system_prompt = """
You are a helpful WhatsApp assistant. You can help users with:

1. **Information & Research**: Answer questions, provide explanations
2. **Task Management**: Create reminders, to-do lists, schedule management  
3. **Calculations**: Math problems, unit conversions, financial calculations
4. **Text Processing**: Summarize text, translate languages, write content
5. **Code Help**: Programming questions, code review, debugging
6. **General Assistance**: Weather, news, recommendations

Keep responses concise but helpful. Use emojis when appropriate.
If you need more information to help, ask clarifying questions.

Current capabilities:
- ✅ Text analysis and generation
- ✅ Math and calculations  
- ✅ General knowledge questions
- ✅ Task organization
- ✅ Code assistance
- ❌ Real-time data (weather, news) - would need API integration
- ❌ File processing - text only through WhatsApp
"""
    
    def generate_response(self, message: str, conversation_history: list, user_context: Dict[str, Any]) -> str:
        """Generate response using LLM."""
        try:
            # Simple rule-based responses for demo
            # Replace this with actual LLM API call
            
            message_lower = message.lower()
            
            # Greeting responses
            if any(greeting in message_lower for greeting in ['hello', 'hi', 'hey', 'start']):
                return """👋 Hello! I'm your WhatsApp AI assistant.

I can help you with:
📚 Questions & research
📝 Task management  
🧮 Calculations
✍️ Text processing
💻 Code assistance
🎯 General tasks

What would you like help with today?"""
            
            # Math calculations
            if any(math_word in message_lower for math_word in ['calculate', 'math', '+', '-', '*', '/', 'equals']):
                return self._handle_math(message)
            
            # Task management
            if any(task_word in message_lower for task_word in ['remind', 'todo', 'task', 'schedule']):
                return self._handle_tasks(message, user_context)
            
            # Code help
            if any(code_word in message_lower for code_word in ['code', 'python', 'javascript', 'programming', 'debug']):
                return self._handle_code(message)
            
            # General help
            if any(help_word in message_lower for help_word in ['help', 'what can you do', 'commands']):
                return """🤖 I can assist you with:

📋 **Commands:**
• "calculate [expression]" - Math calculations
• "remind me [task]" - Set reminders  
• "help with code [language]" - Programming help
• "summarize [text]" - Text summarization
• "translate [text]" - Language translation

📱 **Examples:**
• "Calculate 15% tip on $45"
• "Remind me to call mom tomorrow"
• "Help with Python loops"
• "What's the weather like?" (coming soon)

Just ask me anything naturally! 😊"""
            
            # Default response
            return f"""I understand you said: "{message}"

I'm a demo assistant right now. In a full implementation, I would:

🧠 Use an advanced LLM (GPT-4, Claude, etc.) to understand your request
🔍 Search for information if needed
⚡ Perform the requested task
📱 Give you a helpful response

For now, try asking me to:
• Calculate something
• Help with code
• Set a reminder
• Or type "help" for more options"""
            
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return "Sorry, I encountered an error. Please try again! 🤖"
    
    def _handle_math(self, message: str) -> str:
        """Handle math calculations."""
        try:
            # Extract numbers and operators (simple implementation)
            import re
            
            # Look for mathematical expressions
            math_pattern = r'[\d+\-*/().%\s]+'
            expressions = re.findall(math_pattern, message)
            
            if expressions:
                # Simple eval (in production, use a safer math parser)
                expr = expressions[0].strip()
                if expr:
                    result = eval(expr)  # WARNING: Use safe_eval in production
                    return f"🧮 **Calculation Result:**\n{expr} = **{result}**"
            
            return "🧮 I can help with calculations! Try:\n• 'Calculate 15 + 25'\n• 'What's 20% of 150?'\n• '(45 * 2) + 10'"
            
        except Exception as e:
            return "🧮 I couldn't parse that calculation. Try a simpler format like '15 + 25' or '20 * 3'"
    
    def _handle_tasks(self, message: str, user_context: Dict[str, Any]) -> str:
        """Handle task management."""
        # Simple task storage in user context
        if 'tasks' not in user_context:
            user_context['tasks'] = []
        
        if 'remind' in message.lower():
            # Extract task (simple implementation)
            task = message.lower().replace('remind me to', '').replace('remind me', '').strip()
            if task:
                user_context['tasks'].append({
                    'task': task,
                    'created': datetime.now().isoformat(),
                    'completed': False
                })
                return f"✅ **Reminder Set!**\nI'll remember: {task}\n\nType 'show tasks' to see all your reminders."
        
        if 'show tasks' in message.lower() or 'my tasks' in message.lower():
            tasks = user_context.get('tasks', [])
            if not tasks:
                return "📝 You don't have any tasks yet!\nTry: 'Remind me to call mom'"
            
            task_list = "📝 **Your Tasks:**\n"
            for i, task in enumerate(tasks, 1):
                status = "✅" if task.get('completed') else "⏳"
                task_list += f"{i}. {status} {task['task']}\n"
            
            return task_list
        
        return "📝 **Task Management:**\n• 'Remind me to [task]' - Add reminder\n• 'Show tasks' - View all tasks\n• 'Complete task [number]' - Mark done"
    
    def _handle_code(self, message: str) -> str:
        """Handle code-related questions."""
        message_lower = message.lower()
        
        if 'python' in message_lower:
            return """🐍 **Python Help Available!**

I can help with:
• Syntax questions
• Debugging errors  
• Code optimization
• Best practices
• Library recommendations

**Example questions:**
• "How do I read a CSV file in Python?"
• "Debug this Python code: [paste code]"
• "What's the best way to handle exceptions?"

What specific Python help do you need?"""
        
        elif 'javascript' in message_lower:
            return """⚡ **JavaScript Help Available!**

I can assist with:
• DOM manipulation
• Async/await patterns
• React/Node.js questions
• Debugging tips
• Performance optimization

What JavaScript topic can I help with?"""
        
        else:
            return """💻 **Programming Help Available!**

Supported languages:
• Python 🐍
• JavaScript ⚡  
• Java ☕
• C++ ⚙️
• And many more!

**How to get help:**
• "Help with Python loops"
• "Debug this JavaScript code: [code]"
• "Best practices for [language]"

What programming language are you working with?"""

# Initialize managers
conversation_manager = ConversationManager()
llm_assistant = LLMAssistant()

@app.route('/webhook', methods=['POST'])
def whatsapp_webhook():
    """Handle incoming WhatsApp messages."""
    try:
        # Get message details
        incoming_msg = request.values.get('Body', '').strip()
        from_number = request.values.get('From', '')
        to_number = request.values.get('To', '')
        
        logger.info(f"Received message from {from_number}: {incoming_msg}")
        
        # Get user session
        session = conversation_manager.get_session(from_number)
        
        # Generate response using LLM
        response_text = llm_assistant.generate_response(
            incoming_msg, 
            session.conversation_history,
            session.user_context
        )
        
        # Update conversation history
        session.conversation_history.append({"role": "user", "content": incoming_msg})
        session.conversation_history.append({"role": "assistant", "content": response_text})
        session.last_activity = datetime.now()
        
        # Keep only last 20 messages to manage memory
        if len(session.conversation_history) > 20:
            session.conversation_history = session.conversation_history[-20:]
        
        # Save to database
        conversation_manager.save_conversation(from_number, incoming_msg, response_text)
        conversation_manager.update_user_context(from_number, session.user_context)
        
        # Send response via Twilio
        resp = MessagingResponse()
        resp.message(response_text)
        
        logger.info(f"Sent response to {from_number}: {response_text[:100]}...")
        
        return str(resp)
        
    except Exception as e:
        logger.error(f"Error in webhook: {e}")
        resp = MessagingResponse()
        resp.message("Sorry, I encountered an error. Please try again! 🤖")
        return str(resp)

@app.route('/send_message', methods=['POST'])
def send_message():
    """API endpoint to send messages programmatically."""
    try:
        data = request.json
        to_number = data.get('to')
        message = data.get('message')
        
        if not to_number or not message:
            return jsonify({"error": "Missing 'to' or 'message' parameter"}), 400
        
        # Ensure WhatsApp format
        if not to_number.startswith('whatsapp:'):
            to_number = f"whatsapp:{to_number}"
        
        # Send message
        message_instance = twilio_client.messages.create(
            body=message,
            from_=TWILIO_WHATSAPP_NUMBER,
            to=to_number
        )
        
        logger.info(f"Sent message to {to_number}: {message}")
        
        return jsonify({
            "success": True,
            "message_sid": message_instance.sid,
            "to": to_number,
            "message": message
        })
        
    except Exception as e:
        logger.error(f"Error sending message: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "twilio_configured": bool(TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN),
        "database_connected": conversation_manager.db_path.exists()
    })

@app.route('/stats', methods=['GET'])
def get_stats():
    """Get conversation statistics."""
    try:
        with sqlite3.connect(conversation_manager.db_path) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM conversations")
            total_messages = cursor.fetchone()[0]
            
            cursor = conn.execute("SELECT COUNT(DISTINCT phone_number) FROM conversations")
            unique_users = cursor.fetchone()[0]
            
            cursor = conn.execute("""
                SELECT phone_number, COUNT(*) as message_count 
                FROM conversations 
                GROUP BY phone_number 
                ORDER BY message_count DESC 
                LIMIT 5
            """)
            top_users = cursor.fetchall()
        
        return jsonify({
            "total_messages": total_messages,
            "unique_users": unique_users,
            "top_users": [{"phone": user[0], "messages": user[1]} for user in top_users],
            "active_sessions": len(conversation_manager.sessions)
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    print("🤖 WhatsApp Assistant Starting...")
    print(f"📱 WhatsApp Number: {TWILIO_WHATSAPP_NUMBER}")
    print(f"🔗 Webhook URL: http://your-domain.com/webhook")
    print(f"📊 Health Check: http://localhost:5000/health")
    print(f"📈 Stats: http://localhost:5000/stats")
    
    # Run Flask app
    app.run(host='0.0.0.0', port=5000, debug=True)