#!/usr/bin/env python3
"""
WhatsApp Assistant with Integrated ChunkHound Code Search
Complete integration between WhatsApp bot and ChunkHound for code searching.
"""

import os
import json
import logging
import requests
import subprocess
from datetime import datetime
from typing import Dict, Any, Optional, List
from flask import Flask, request, jsonify
from twilio.rest import Client
from twilio.twiml.messaging_response import MessagingResponse
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

# Twilio Configuration - Load from environment variables
TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID', 'your_account_sid_here')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN', 'your_auth_token_here')
TWILIO_WHATSAPP_NUMBER = os.getenv('TWILIO_WHATSAPP_NUMBER', 'whatsapp:+1234567890')

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

class ChunkHoundCodeSearch:
    """ChunkHound integration for code searching."""
    
    def __init__(self, project_path: str = "/workspace/test_project"):
        self.project_path = Path(project_path)
        self.server_url = "http://localhost:8001"  # Different port to avoid conflicts
        self.server_process = None
        self.is_running = False
        
    def start_server(self) -> bool:
        """Start ChunkHound MCP server."""
        try:
            if self.is_running:
                return True
                
            # Check if ChunkHound is installed
            result = subprocess.run(["which", "chunkhound"], capture_output=True, text=True)
            if result.returncode != 0:
                logger.warning("ChunkHound not installed - code search disabled")
                return False
            
            # Check if project exists and has .chunkhound.json
            if not self.project_path.exists():
                logger.warning(f"Project path {self.project_path} not found")
                return False
                
            config_file = self.project_path / ".chunkhound.json"
            if not config_file.exists():
                logger.warning("ChunkHound config not found - creating basic config")
                self._create_basic_config()
            
            # Start server
            os.chdir(self.project_path)
            cmd = ["chunkhound", "serve", "--http", "--port", "8001"]
            
            self.server_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=self.project_path
            )
            
            # Wait for server to start
            import time
            time.sleep(3)
            
            # Test server health
            try:
                response = requests.get(f"{self.server_url}/health", timeout=5)
                self.is_running = response.status_code == 200
                if self.is_running:
                    logger.info("ChunkHound server started successfully")
                return self.is_running
            except:
                logger.warning("ChunkHound server failed to start")
                return False
                
        except Exception as e:
            logger.error(f"Failed to start ChunkHound: {e}")
            return False
    
    def _create_basic_config(self):
        """Create basic ChunkHound configuration."""
        config = {
            "include_patterns": ["**/*.py", "**/*.js", "**/*.java", "**/*.cpp", "**/*.h"],
            "exclude_patterns": ["**/node_modules/**", "**/.git/**", "**/__pycache__/**"],
            "chunk_size": 1000,
            "chunk_overlap": 200
        }
        
        config_file = self.project_path / ".chunkhound.json"
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)
    
    def stop_server(self):
        """Stop ChunkHound server."""
        if self.server_process:
            self.server_process.terminate()
            self.server_process.wait()
            self.is_running = False
    
    def search_code(self, query: str) -> Dict[str, Any]:
        """Search code using ChunkHound."""
        if not self.is_running:
            return {"error": "Code search not available"}
            
        try:
            response = requests.post(
                f"{self.server_url}/search_regex_local",
                json={"query": query},
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"Search failed: {response.status_code}"}
                
        except Exception as e:
            return {"error": f"Search error: {e}"}

class IntegratedLLMAssistant:
    """LLM assistant with integrated ChunkHound code search."""
    
    def __init__(self):
        self.chunkhound = ChunkHoundCodeSearch()
        self.code_search_enabled = False
        
        # Try to start ChunkHound
        if self.chunkhound.start_server():
            self.code_search_enabled = True
            logger.info("Code search enabled")
        else:
            logger.info("Code search disabled - ChunkHound not available")
        
        self.system_prompt = """
You are a helpful WhatsApp assistant with code search capabilities. You can:

🤖 **Core Functions:**
- Answer questions and provide information
- Help with calculations and conversions
- Assist with writing and text processing
- Provide coding help and debugging
- Search through codebases (when available)
- Manage tasks and reminders

🔍 **Code Search Commands:**
- "search code for [query]" - Search through code files
- "find function [name]" - Find specific functions
- "find class [name]" - Find specific classes
- "search for SQL" - Find SQL queries
- "code search help" - Show code search help

Keep responses concise and helpful. Use emojis appropriately.
"""
    
    def generate_response(self, message: str, conversation_history: list, user_context: Dict[str, Any]) -> str:
        """Generate response with code search integration."""
        try:
            message_lower = message.lower()
            
            # Handle code search requests
            if self.code_search_enabled and self._is_code_search_request(message_lower):
                return self._handle_code_search(message)
            
            # Handle code search help
            if "code search help" in message_lower:
                return self._get_code_search_help()
            
            # Regular assistant responses
            return self._handle_regular_request(message, conversation_history, user_context)
            
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return "Sorry, I encountered an error. Please try again! 🤖"
    
    def _is_code_search_request(self, message: str) -> bool:
        """Check if message is a code search request."""
        search_triggers = [
            "search code", "find code", "search for", "find function", 
            "find class", "search function", "search class", "code search"
        ]
        return any(trigger in message for trigger in search_triggers)
    
    def _handle_code_search(self, message: str) -> str:
        """Handle code search requests."""
        if not self.code_search_enabled:
            return "🔍 **Code Search Unavailable**\n\nCode search is currently disabled. ChunkHound server is not running."
        
        # Extract search query
        query = self._extract_search_query(message)
        if not query:
            return "🔍 **Code Search**\n\nPlease specify what to search for!\n\n**Examples:**\n• 'Search code for User class'\n• 'Find function calculate_total'\n• 'Search for SQL queries'"
        
        # Perform search
        results = self.chunkhound.search_code(query)
        return self._format_search_results(results, query)
    
    def _extract_search_query(self, message: str) -> str:
        """Extract search query from message."""
        message_lower = message.lower()
        
        # Remove common prefixes
        prefixes = [
            "search code for ", "find code for ", "search for ", 
            "find function ", "find class ", "search function ", "search class "
        ]
        
        query = message_lower
        for prefix in prefixes:
            if prefix in query:
                query = query.split(prefix, 1)[1].strip()
                break
        
        return query
    
    def _format_search_results(self, results: Dict[str, Any], query: str) -> str:
        """Format search results for WhatsApp."""
        if "error" in results:
            return f"🔍 **Code Search Error**\n\n{results['error']}"
        
        if not results.get("results"):
            return f"🔍 **No Results Found**\n\nNo code found matching: `{query}`"
        
        # Format results
        formatted = f"🔍 **Code Search Results**\n\n**Query**: `{query}`\n**Found**: {len(results['results'])} matches\n\n"
        
        # Show top 3 results
        for i, result in enumerate(results["results"][:3], 1):
            file_path = result.get("file_path", "unknown")
            content = result.get("content", "")
            
            # Truncate content for WhatsApp (1600 char limit)
            if len(content) > 150:
                content = content[:150] + "..."
            
            formatted += f"**{i}. {file_path}**\n```\n{content}\n```\n\n"
        
        if len(results["results"]) > 3:
            formatted += f"... and {len(results['results']) - 3} more results\n"
        
        return formatted
    
    def _get_code_search_help(self) -> str:
        """Get code search help."""
        if not self.code_search_enabled:
            return "🔍 **Code Search**: Currently disabled\n\nChunkHound server is not running."
        
        return """🔍 **Code Search Available!**

**Commands:**
• `Search code for [query]` - Search all code
• `Find function [name]` - Find specific function  
• `Find class [name]` - Find specific class
• `Search for SQL` - Find SQL queries
• `Search for TODO` - Find TODO comments

**Examples:**
• "Search code for User class"
• "Find function validate_email"
• "Search for database connections"
• "Find all error handling"

**Supported Languages:**
✅ Python, JavaScript, Java, C++, C#
✅ SQL, HTML, CSS, JSON, YAML
✅ And many more!

The search uses regex patterns and can find functions, classes, variables, comments, and code patterns."""
    
    def _handle_regular_request(self, message: str, history: list, context: Dict[str, Any]) -> str:
        """Handle regular (non-code-search) requests."""
        message_lower = message.lower()
        
        # Greeting responses
        if any(word in message_lower for word in ['hello', 'hi', 'hey', 'start']):
            code_status = "✅ Available" if self.code_search_enabled else "❌ Disabled"
            return f"""👋 Hello! I'm your WhatsApp AI assistant.

**Available Features:**
📚 Questions & Information
🧮 Math Calculations  
📝 Task Management
💻 Programming Help
🔍 Code Search: {code_status}

**Quick Commands:**
• "help" - Show all features
• "calculate 15 + 25" - Math
• "code search help" - Code search info

What can I help you with today?"""
        
        # Help command
        if 'help' in message_lower:
            return """🤖 **WhatsApp Assistant Help**

**Core Features:**
• 📚 Answer questions
• 🧮 Math calculations
• 📝 Task reminders
• 💻 Programming help
• 🔍 Code search (if enabled)

**Examples:**
• "What's 15% of 200?"
• "Remind me to call mom"
• "Help with Python loops"
• "Search code for User class"

**Commands:**
• `help` - This help message
• `code search help` - Code search commands
• `calculate [expression]` - Math
• `remind me [task]` - Set reminder

Just ask me anything naturally! 😊"""
        
        # Math calculations
        if any(word in message_lower for word in ['calculate', 'math', '+', '-', '*', '/', '=']):
            return self._handle_math(message)
        
        # Task management
        if any(word in message_lower for word in ['remind', 'todo', 'task']):
            return self._handle_tasks(message, context)
        
        # Default response
        return f"""I understand you said: "{message}"

I can help with:
🧮 **Math**: "Calculate 15 + 25"
📝 **Tasks**: "Remind me to call mom"
💻 **Code**: "Help with Python"
🔍 **Search**: "Search code for User class" {'✅' if self.code_search_enabled else '❌'}

What would you like help with?"""
    
    def _handle_math(self, message: str) -> str:
        """Handle math calculations."""
        try:
            import re
            # Extract mathematical expression
            expr = re.sub(r'[^\d+\-*/().%\s]', '', message)
            if expr.strip():
                result = eval(expr.strip())  # Use safe_eval in production
                return f"🧮 **Calculation Result:**\n\n`{expr.strip()}` = **{result}**"
            else:
                return "🧮 Please provide a mathematical expression!\n\nExample: `15 + 25 * 2`"
        except:
            return "🧮 I couldn't calculate that. Please check the format.\n\nExample: `15 + 25 * 2`"
    
    def _handle_tasks(self, message: str, context: Dict[str, Any]) -> str:
        """Handle task management."""
        if 'tasks' not in context:
            context['tasks'] = []
        
        if 'remind' in message.lower():
            task = message.lower().replace('remind me to', '').replace('remind me', '').strip()
            if task:
                context['tasks'].append({
                    'task': task,
                    'created': datetime.now().isoformat()
                })
                return f"✅ **Reminder Set!**\n\nI'll remember: {task}\n\nType 'show tasks' to see all reminders."
        
        return "📝 **Task Management:**\n\n• 'Remind me to [task]' - Add reminder\n• 'Show tasks' - View all tasks"

class ConversationManager:
    """Manages user conversations and context."""
    
    def __init__(self, db_path: str = "whatsapp_conversations.db"):
        self.db_path = Path(db_path)
        self.sessions: Dict[str, UserSession] = {}
        self._init_database()
    
    def _init_database(self):
        """Initialize SQLite database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    phone_number TEXT NOT NULL,
                    message TEXT NOT NULL,
                    response TEXT NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
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
                SELECT message, response FROM conversations 
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
            
            return list(reversed(history))
    
    def save_conversation(self, phone_number: str, message: str, response: str):
        """Save conversation to database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO conversations (phone_number, message, response)
                VALUES (?, ?, ?)
            """, (phone_number, message, response))
    
    def update_user_context(self, phone_number: str, context: Dict[str, Any]):
        """Update user context."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO user_context (phone_number, context_data)
                VALUES (?, ?)
            """, (phone_number, json.dumps(context)))

# Initialize components
conversation_manager = ConversationManager()
llm_assistant = IntegratedLLMAssistant()

@app.route('/webhook', methods=['POST'])
def whatsapp_webhook():
    """Handle incoming WhatsApp messages with code search integration."""
    try:
        # Get message details
        incoming_msg = request.values.get('Body', '').strip()
        from_number = request.values.get('From', '')
        
        logger.info(f"Received message from {from_number}: {incoming_msg}")
        
        # Get user session
        session = conversation_manager.get_session(from_number)
        
        # Generate response using integrated assistant
        response_text = llm_assistant.generate_response(
            incoming_msg, 
            session.conversation_history,
            session.user_context
        )
        
        # Update conversation history
        session.conversation_history.append({"role": "user", "content": incoming_msg})
        session.conversation_history.append({"role": "assistant", "content": response_text})
        session.last_activity = datetime.now()
        
        # Keep only last 20 messages
        if len(session.conversation_history) > 20:
            session.conversation_history = session.conversation_history[-20:]
        
        # Save to database
        conversation_manager.save_conversation(from_number, incoming_msg, response_text)
        conversation_manager.update_user_context(from_number, session.user_context)
        
        # Send response via Twilio
        resp = MessagingResponse()
        resp.message(response_text)
        
        logger.info(f"Sent response to {from_number}")
        return str(resp)
        
    except Exception as e:
        logger.error(f"Error in webhook: {e}")
        resp = MessagingResponse()
        resp.message("Sorry, I encountered an error. Please try again! 🤖")
        return str(resp)

@app.route('/health', methods=['GET'])
def health_check():
    """Health check with ChunkHound status."""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "twilio_configured": bool(TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN),
        "code_search_enabled": llm_assistant.code_search_enabled,
        "chunkhound_running": llm_assistant.chunkhound.is_running,
        "database_connected": conversation_manager.db_path.exists()
    })

@app.route('/code_search', methods=['POST'])
def code_search_api():
    """API endpoint for code search."""
    try:
        data = request.json
        query = data.get('query', '')
        
        if not query:
            return jsonify({"error": "Query parameter required"}), 400
        
        if not llm_assistant.code_search_enabled:
            return jsonify({"error": "Code search not available"}), 503
        
        results = llm_assistant.chunkhound.search_code(query)
        return jsonify(results)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    print("🤖 WhatsApp Assistant with ChunkHound Integration")
    print("=" * 55)
    print(f"📱 WhatsApp Number: {TWILIO_WHATSAPP_NUMBER}")
    print(f"🔍 Code Search: {'✅ Enabled' if llm_assistant.code_search_enabled else '❌ Disabled'}")
    print(f"🔗 Webhook: http://your-domain.com/webhook")
    print(f"📊 Health: http://localhost:5000/health")
    print(f"🔍 Code Search API: http://localhost:5000/code_search")
    
    try:
        app.run(host='0.0.0.0', port=5000, debug=True)
    finally:
        # Cleanup ChunkHound server on exit
        llm_assistant.chunkhound.stop_server()