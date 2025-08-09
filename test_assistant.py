#!/usr/bin/env python3
"""
Test script for WhatsApp Assistant
Demonstrates the assistant's capabilities without needing a live webhook.
"""

import sys
import os
sys.path.append('/workspace')

from whatsapp_assistant import LLMAssistant, ConversationManager
import asyncio

def test_assistant():
    """Test the assistant's responses to various inputs."""
    
    print("🤖 Testing WhatsApp Assistant Capabilities")
    print("=" * 50)
    
    # Initialize components
    assistant = LLMAssistant()
    conversation_manager = ConversationManager()
    
    # Test phone number
    test_phone = "whatsapp:+1234567890"
    
    # Test cases
    test_messages = [
        "Hello",
        "help",
        "Calculate 15 + 25 * 2",
        "Remind me to call mom tomorrow",
        "Help with Python code",
        "What can you do?",
        "Show tasks",
        "Translate hello to Spanish"
    ]
    
    print(f"📱 Testing with phone number: {test_phone}")
    print()
    
    for i, message in enumerate(test_messages, 1):
        print(f"🔹 Test {i}: User says: '{message}'")
        
        # Get user session
        session = conversation_manager.get_session(test_phone)
        
        # Generate response
        response = assistant.generate_response(
            message, 
            session.conversation_history,
            session.user_context
        )
        
        # Update conversation
        session.conversation_history.extend([
            {"role": "user", "content": message},
            {"role": "assistant", "content": response}
        ])
        
        # Save conversation
        conversation_manager.save_conversation(test_phone, message, response)
        
        print(f"🤖 Assistant responds:")
        print(f"   {response}")
        print("-" * 50)
    
    # Test statistics
    print("\n📊 Testing Statistics:")
    with conversation_manager.db_path.open() as f:
        import sqlite3
        conn = sqlite3.connect(conversation_manager.db_path)
        cursor = conn.execute("SELECT COUNT(*) FROM conversations")
        total_messages = cursor.fetchone()[0]
        print(f"   Total messages stored: {total_messages}")
        conn.close()

def test_twilio_integration():
    """Test Twilio integration without sending actual messages."""
    
    print("\n🔧 Testing Twilio Integration")
    print("=" * 30)
    
    from twilio.rest import Client
    
    # Load credentials from environment
    ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "your_account_sid_here")
    AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "your_auth_token_here")
    
    try:
        client = Client(ACCOUNT_SID, AUTH_TOKEN)
        account = client.api.accounts(ACCOUNT_SID).fetch()
        
        print(f"✅ Twilio Connection: SUCCESS")
        print(f"   Account Name: {account.friendly_name}")
        print(f"   Account SID: {ACCOUNT_SID}")
        print(f"   Status: {account.status}")
        
        # List phone numbers
        phone_numbers = client.incoming_phone_numbers.list(limit=5)
        print(f"\n📞 Available Phone Numbers:")
        for number in phone_numbers:
            print(f"   • {number.phone_number} ({number.friendly_name})")
            
        return True
        
    except Exception as e:
        print(f"❌ Twilio Connection: FAILED")
        print(f"   Error: {e}")
        return False

def demonstrate_features():
    """Demonstrate key features of the WhatsApp assistant."""
    
    print("\n🎯 WhatsApp Assistant Features")
    print("=" * 35)
    
    features = [
        {
            "name": "Natural Language Processing",
            "description": "Understands and responds to natural language",
            "example": "User: 'Hello, how are you?' → Assistant provides friendly greeting"
        },
        {
            "name": "Mathematical Calculations", 
            "description": "Performs math calculations and conversions",
            "example": "User: 'Calculate 15% tip on $45' → Assistant: '$6.75'"
        },
        {
            "name": "Task Management",
            "description": "Helps manage reminders and to-do lists",
            "example": "User: 'Remind me to call mom' → Assistant saves reminder"
        },
        {
            "name": "Code Assistance",
            "description": "Provides programming help and debugging",
            "example": "User: 'Help with Python loops' → Assistant explains loops"
        },
        {
            "name": "Conversation Memory",
            "description": "Remembers conversation context and user preferences",
            "example": "Maintains chat history and user profile across sessions"
        },
        {
            "name": "Multi-language Support",
            "description": "Can handle multiple languages and translations",
            "example": "User: 'Translate hello to Spanish' → Assistant: 'Hola'"
        }
    ]
    
    for i, feature in enumerate(features, 1):
        print(f"{i}. 🔹 {feature['name']}")
        print(f"   📝 {feature['description']}")
        print(f"   💡 Example: {feature['example']}")
        print()

def show_deployment_options():
    """Show deployment options for the WhatsApp assistant."""
    
    print("🚀 Deployment Options")
    print("=" * 25)
    
    options = [
        {
            "platform": "Railway (Recommended)",
            "cost": "Free tier available",
            "setup": "Connect GitHub → Auto-deploy",
            "pros": ["Easy setup", "Auto-scaling", "Free SSL"]
        },
        {
            "platform": "Heroku",
            "cost": "$7/month minimum",
            "setup": "Heroku CLI → git push",
            "pros": ["Mature platform", "Add-ons", "Good docs"]
        },
        {
            "platform": "DigitalOcean",
            "cost": "$5/month minimum", 
            "setup": "App Platform → GitHub",
            "pros": ["Reliable", "Good performance", "Predictable pricing"]
        },
        {
            "platform": "Local + ngrok",
            "cost": "Free for testing",
            "setup": "Run locally → ngrok tunnel",
            "pros": ["Quick testing", "No deployment needed", "Full control"]
        }
    ]
    
    for option in options:
        print(f"🔹 {option['platform']}")
        print(f"   💰 Cost: {option['cost']}")
        print(f"   ⚙️  Setup: {option['setup']}")
        print(f"   ✅ Pros: {', '.join(option['pros'])}")
        print()

if __name__ == "__main__":
    print("🤖 WhatsApp Assistant Test Suite")
    print("=" * 40)
    
    # Test assistant functionality
    test_assistant()
    
    # Test Twilio integration
    twilio_works = test_twilio_integration()
    
    # Show features
    demonstrate_features()
    
    # Show deployment options
    show_deployment_options()
    
    print("\n✅ Test Suite Complete!")
    print("\n🎯 Next Steps:")
    print("1. Deploy to a cloud platform (Railway recommended)")
    print("2. Configure Twilio webhook URL")
    print("3. Test with your WhatsApp number")
    print("4. Add OpenAI API key for advanced features")
    print("5. Customize the assistant for your needs")
    
    if twilio_works:
        print("\n🚀 Your Twilio integration is ready!")
        print("   Just deploy and configure the webhook URL.")
    else:
        print("\n⚠️  Check your Twilio credentials before deploying.")