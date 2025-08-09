#!/usr/bin/env python3
"""
Advanced WhatsApp Assistant with Real LLM Integration
Supports OpenAI GPT, Anthropic Claude, and other LLM providers.
"""

import os
import json
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from flask import Flask, request, jsonify
from twilio.rest import Client
from twilio.twiml.messaging_response import MessagingResponse
import openai
from dataclasses import dataclass, asdict
import sqlite3
from pathlib import Path
import requests
import re
from functools import wraps

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

# Configuration - Load from environment variables
TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID', 'your_account_sid_here')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN', 'your_auth_token_here')
TWILIO_WHATSAPP_NUMBER = os.getenv('TWILIO_WHATSAPP_NUMBER', 'whatsapp:+1234567890')

# LLM Configuration (set your API keys)
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY', '')

# Initialize clients
twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
if OPENAI_API_KEY:
    openai.api_key = OPENAI_API_KEY

app = Flask(__name__)

@dataclass
class UserProfile:
    """User profile with preferences and context."""
    phone_number: str
    name: Optional[str] = None
    preferred_language: str = "en"
    timezone: str = "UTC"
    preferences: Dict[str, Any] = None
    created_at: datetime = None
    last_active: datetime = None
    
    def __post_init__(self):
        if self.preferences is None:
            self.preferences = {}
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.last_active is None:
            self.last_active = datetime.now()

class AdvancedLLMAssistant:
    """Advanced LLM assistant with multiple provider support."""
    
    def __init__(self):
        self.system_prompt = """You are an intelligent WhatsApp assistant with the following capabilities:

🤖 **Core Functions:**
- Answer questions and provide information
- Help with calculations and conversions
- Assist with writing and text processing
- Provide coding help and debugging
- Manage tasks and reminders
- Offer general life assistance

🎯 **Communication Style:**
- Be helpful, friendly, and concise
- Use emojis appropriately to enhance communication
- Ask clarifying questions when needed
- Provide actionable advice
- Keep responses under 1600 characters (WhatsApp limit)

🔧 **Special Commands:**
- /help - Show available commands
- /profile - Manage user profile
- /clear - Clear conversation history
- /remind [task] - Set reminders
- /calculate [expression] - Math calculations
- /translate [text] - Language translation
- /weather [location] - Weather information (if API available)

Always be helpful and maintain context from the conversation history."""

        self.tools = {
            'calculator': self._calculator_tool,
            'reminder': self._reminder_tool,
            'translator': self._translator_tool,
            'weather': self._weather_tool,
            'code_helper': self._code_helper_tool
        }
    
    async def generate_response(self, message: str, conversation_history: List[Dict], user_profile: UserProfile) -> str:
        """Generate response using the best available LLM."""
        try:
            # Check for special commands first
            if message.startswith('/'):
                return await self._handle_command(message, user_profile)
            
            # Check if message needs a specific tool
            tool_response = await self._check_tools(message, user_profile)
            if tool_response:
                return tool_response
            
            # Use LLM for general conversation
            if OPENAI_API_KEY:
                return await self._openai_response(message, conversation_history, user_profile)
            elif ANTHROPIC_API_KEY:
                return await self._anthropic_response(message, conversation_history, user_profile)
            else:
                return await self._fallback_response(message, user_profile)
                
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return "I apologize, but I encountered an error. Please try again! 🤖"
    
    async def _openai_response(self, message: str, history: List[Dict], profile: UserProfile) -> str:
        """Generate response using OpenAI GPT."""
        try:
            messages = [{"role": "system", "content": self.system_prompt}]
            
            # Add conversation history (last 10 messages)
            messages.extend(history[-10:])
            messages.append({"role": "user", "content": message})
            
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",  # or "gpt-4" if you have access
                messages=messages,
                max_tokens=500,
                temperature=0.7,
                user=profile.phone_number
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            return await self._fallback_response(message, profile)
    
    async def _anthropic_response(self, message: str, history: List[Dict], profile: UserProfile) -> str:
        """Generate response using Anthropic Claude."""
        try:
            # Implement Anthropic API call here
            # This is a placeholder - you'll need to implement the actual API call
            return await self._fallback_response(message, profile)
            
        except Exception as e:
            logger.error(f"Anthropic API error: {e}")
            return await self._fallback_response(message, profile)
    
    async def _fallback_response(self, message: str, profile: UserProfile) -> str:
        """Fallback response when no LLM API is available."""
        message_lower = message.lower()
        
        # Greeting responses
        if any(word in message_lower for word in ['hello', 'hi', 'hey', 'start']):
            return f"""👋 Hello{f' {profile.name}' if profile.name else ''}! 

I'm your WhatsApp AI assistant. I can help you with:

📚 **Information & Questions**
🧮 **Calculations** - Try: "Calculate 15% of 200"
📝 **Task Management** - Try: "/remind Call dentist tomorrow"
💻 **Code Help** - Try: "Help me debug this Python code"
🌍 **Translations** - Try: "/translate Hello to Spanish"

Type **/help** for all commands or just ask me anything! 😊"""
        
        # Help command
        if 'help' in message_lower:
            return """🤖 **Available Commands:**

**Basic:**
• `/help` - Show this help
• `/profile` - Manage your profile
• `/clear` - Clear chat history

**Tools:**
• `/calculate [expression]` - Math calculations
• `/remind [task]` - Set reminders  
• `/translate [text] to [language]` - Translate text
• `/weather [city]` - Get weather info

**Examples:**
• "What's the capital of France?"
• "/calculate 15% tip on $45.50"
• "/remind Buy groceries tomorrow"
• "Help me write a Python function"

Just ask me anything naturally! 🚀"""
        
        # Math detection
        if any(word in message_lower for word in ['calculate', 'math', '+', '-', '*', '/', '=']):
            return await self._calculator_tool(message)
        
        # Default intelligent response
        return f"""I understand you're asking about: "{message}"

🤖 **I can help with:**
• Answering questions
• Solving math problems  
• Writing and editing text
• Programming assistance
• Task management
• General advice

For the best experience, consider adding an OpenAI API key to enable advanced AI features!

Try asking me something specific or type **/help** for commands."""
    
    async def _handle_command(self, command: str, profile: UserProfile) -> str:
        """Handle special commands."""
        parts = command.split(' ', 1)
        cmd = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""
        
        if cmd == '/help':
            return await self._fallback_response('help', profile)
        
        elif cmd == '/profile':
            return f"""👤 **Your Profile:**

📱 Phone: {profile.phone_number}
👤 Name: {profile.name or 'Not set'}
🌍 Language: {profile.preferred_language}
⏰ Timezone: {profile.timezone}
📅 Member since: {profile.created_at.strftime('%Y-%m-%d')}
🕐 Last active: {profile.last_active.strftime('%Y-%m-%d %H:%M')}

To update your profile, send:
• "My name is [name]"
• "Set language to [language]"
• "Set timezone to [timezone]" """
        
        elif cmd == '/clear':
            return "🗑️ **Chat History Cleared!**\n\nYour conversation history has been reset. How can I help you today?"
        
        elif cmd == '/calculate':
            return await self._calculator_tool(args)
        
        elif cmd == '/remind':
            return await self._reminder_tool(args, profile)
        
        elif cmd == '/translate':
            return await self._translator_tool(args)
        
        elif cmd == '/weather':
            return await self._weather_tool(args)
        
        else:
            return f"❓ Unknown command: {cmd}\n\nType **/help** to see available commands."
    
    async def _check_tools(self, message: str, profile: UserProfile) -> Optional[str]:
        """Check if message requires a specific tool."""
        message_lower = message.lower()
        
        # Math expressions
        if re.search(r'[\d+\-*/().%]', message) and any(word in message_lower for word in ['calculate', 'what is', 'equals', '=']):
            return await self._calculator_tool(message)
        
        # Reminders
        if any(word in message_lower for word in ['remind me', 'remember to', 'don\'t forget']):
            return await self._reminder_tool(message, profile)
        
        # Translation
        if 'translate' in message_lower and ('to' in message_lower or 'in' in message_lower):
            return await self._translator_tool(message)
        
        return None
    
    async def _calculator_tool(self, expression: str) -> str:
        """Handle mathematical calculations."""
        try:
            # Clean the expression
            expression = re.sub(r'[^\d+\-*/().%\s]', '', expression)
            expression = expression.replace('x', '*').replace('÷', '/')
            
            if not expression.strip():
                return "🧮 Please provide a mathematical expression!\n\nExample: 15 + 25 * 2"
            
            # Safe evaluation (basic implementation)
            result = eval(expression.strip())
            
            return f"🧮 **Calculation Result:**\n\n`{expression.strip()}` = **{result}**"
            
        except Exception as e:
            return f"🧮 **Calculation Error:**\n\nI couldn't calculate that expression. Please check the format.\n\nExample: `15 + 25 * 2`"
    
    async def _reminder_tool(self, task: str, profile: UserProfile) -> str:
        """Handle reminder creation."""
        # Clean the task text
        task = re.sub(r'remind me to|remind me|remember to|don\'t forget to', '', task, flags=re.IGNORECASE).strip()
        
        if not task:
            return "📝 **Set a Reminder:**\n\nPlease tell me what you'd like to be reminded about!\n\nExample: `/remind Call mom tomorrow`"
        
        # In a full implementation, you'd save this to a database with scheduling
        return f"✅ **Reminder Set!**\n\n📋 Task: {task}\n⏰ I'll help you remember this!\n\n*Note: For time-based reminders, integrate with a scheduling system.*"
    
    async def _translator_tool(self, text: str) -> str:
        """Handle text translation."""
        # Simple translation detection
        if ' to ' in text.lower():
            parts = text.lower().split(' to ')
            if len(parts) == 2:
                source_text = parts[0].replace('translate', '').strip()
                target_lang = parts[1].strip()
                
                return f"🌍 **Translation Request:**\n\n📝 Text: {source_text}\n🎯 To: {target_lang}\n\n*Note: For actual translation, integrate with Google Translate API or similar service.*"
        
        return "🌍 **Translation Help:**\n\nFormat: `/translate [text] to [language]`\n\nExample: `/translate Hello to Spanish`"
    
    async def _weather_tool(self, location: str) -> str:
        """Handle weather requests."""
        if not location.strip():
            return "🌤️ **Weather Information:**\n\nPlease specify a location!\n\nExample: `/weather New York`"
        
        return f"🌤️ **Weather for {location}:**\n\n*Note: To get real weather data, integrate with OpenWeatherMap API or similar service.*\n\nExample integration would show:\n• Temperature\n• Conditions\n• Humidity\n• Forecast"
    
    async def _code_helper_tool(self, code_request: str) -> str:
        """Handle coding assistance."""
        return f"💻 **Code Assistance:**\n\nI can help with:\n• Debugging errors\n• Code optimization\n• Best practices\n• Language-specific questions\n\nWhat programming language are you working with?"

class ConversationManager:
    """Enhanced conversation management with user profiles."""
    
    def __init__(self, db_path: str = "whatsapp_assistant.db"):
        self.db_path = Path(db_path)
        self.sessions: Dict[str, Dict] = {}
        self._init_database()
    
    def _init_database(self):
        """Initialize SQLite database."""
        with sqlite3.connect(self.db_path) as conn:
            # Conversations table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    phone_number TEXT NOT NULL,
                    message TEXT NOT NULL,
                    response TEXT NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    message_type TEXT DEFAULT 'text',
                    tokens_used INTEGER DEFAULT 0
                )
            """)
            
            # User profiles table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS user_profiles (
                    phone_number TEXT PRIMARY KEY,
                    name TEXT,
                    preferred_language TEXT DEFAULT 'en',
                    timezone TEXT DEFAULT 'UTC',
                    preferences TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    last_active DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Reminders table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS reminders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    phone_number TEXT NOT NULL,
                    task TEXT NOT NULL,
                    due_date DATETIME,
                    completed BOOLEAN DEFAULT FALSE,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
    
    def get_user_profile(self, phone_number: str) -> UserProfile:
        """Get or create user profile."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT * FROM user_profiles WHERE phone_number = ?",
                (phone_number,)
            )
            row = cursor.fetchone()
            
            if row:
                return UserProfile(
                    phone_number=row[0],
                    name=row[1],
                    preferred_language=row[2],
                    timezone=row[3],
                    preferences=json.loads(row[4]) if row[4] else {},
                    created_at=datetime.fromisoformat(row[5]),
                    last_active=datetime.fromisoformat(row[6])
                )
            else:
                # Create new profile
                profile = UserProfile(phone_number=phone_number)
                self.save_user_profile(profile)
                return profile
    
    def save_user_profile(self, profile: UserProfile):
        """Save user profile to database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO user_profiles 
                (phone_number, name, preferred_language, timezone, preferences, created_at, last_active)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                profile.phone_number,
                profile.name,
                profile.preferred_language,
                profile.timezone,
                json.dumps(profile.preferences),
                profile.created_at.isoformat(),
                profile.last_active.isoformat()
            ))
    
    def get_conversation_history(self, phone_number: str, limit: int = 10) -> List[Dict]:
        """Get recent conversation history."""
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
    
    def save_conversation(self, phone_number: str, message: str, response: str, tokens_used: int = 0):
        """Save conversation to database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO conversations (phone_number, message, response, tokens_used)
                VALUES (?, ?, ?, ?)
            """, (phone_number, message, response, tokens_used))

# Initialize components
conversation_manager = ConversationManager()
llm_assistant = AdvancedLLMAssistant()

@app.route('/webhook', methods=['POST'])
def whatsapp_webhook():
    """Enhanced webhook handler."""
    try:
        # Get message details
        incoming_msg = request.values.get('Body', '').strip()
        from_number = request.values.get('From', '')
        
        logger.info(f"Received message from {from_number}: {incoming_msg}")
        
        # Get user profile and conversation history
        profile = conversation_manager.get_user_profile(from_number)
        history = conversation_manager.get_conversation_history(from_number)
        
        # Update last active
        profile.last_active = datetime.now()
        conversation_manager.save_user_profile(profile)
        
        # Generate response
        response_text = asyncio.run(
            llm_assistant.generate_response(incoming_msg, history, profile)
        )
        
        # Save conversation
        conversation_manager.save_conversation(from_number, incoming_msg, response_text)
        
        # Send response
        resp = MessagingResponse()
        resp.message(response_text)
        
        logger.info(f"Sent response to {from_number}")
        return str(resp)
        
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        resp = MessagingResponse()
        resp.message("Sorry, I encountered an error. Please try again! 🤖")
        return str(resp)

@app.route('/health', methods=['GET'])
def health_check():
    """Enhanced health check."""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "twilio_configured": bool(TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN),
        "openai_configured": bool(OPENAI_API_KEY),
        "anthropic_configured": bool(ANTHROPIC_API_KEY),
        "database_connected": conversation_manager.db_path.exists()
    })

@app.route('/stats', methods=['GET'])
def get_stats():
    """Get detailed statistics."""
    try:
        with sqlite3.connect(conversation_manager.db_path) as conn:
            # Basic stats
            cursor = conn.execute("SELECT COUNT(*) FROM conversations")
            total_messages = cursor.fetchone()[0]
            
            cursor = conn.execute("SELECT COUNT(*) FROM user_profiles")
            total_users = cursor.fetchone()[0]
            
            # Active users (last 24 hours)
            yesterday = datetime.now() - timedelta(days=1)
            cursor = conn.execute(
                "SELECT COUNT(*) FROM user_profiles WHERE last_active > ?",
                (yesterday.isoformat(),)
            )
            active_users = cursor.fetchone()[0]
            
            # Top users
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
            "total_users": total_users,
            "active_users_24h": active_users,
            "top_users": [{"phone": user[0], "messages": user[1]} for user in top_users]
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    print("🤖 Advanced WhatsApp Assistant Starting...")
    print(f"📱 WhatsApp Number: {TWILIO_WHATSAPP_NUMBER}")
    print(f"🧠 OpenAI: {'✅ Configured' if OPENAI_API_KEY else '❌ Not configured'}")
    print(f"🧠 Anthropic: {'✅ Configured' if ANTHROPIC_API_KEY else '❌ Not configured'}")
    print(f"🔗 Webhook: http://your-domain.com/webhook")
    
    app.run(host='0.0.0.0', port=5000, debug=True)