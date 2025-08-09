#!/usr/bin/env python3
"""
Setup script for WhatsApp Assistant
This script helps configure and test your WhatsApp assistant.
"""

import os
import sys
import json
import requests
from twilio.rest import Client
from pathlib import Path

# Your Twilio credentials
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "your_account_sid_here")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "your_auth_token_here")
TWILIO_WHATSAPP_NUMBER = os.getenv("TWILIO_WHATSAPP_NUMBER", "whatsapp:+1234567890")

def test_twilio_connection():
    """Test Twilio API connection."""
    print("🔍 Testing Twilio connection...")
    
    try:
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        
        # Get account info
        account = client.api.accounts(TWILIO_ACCOUNT_SID).fetch()
        print(f"✅ Connected to Twilio account: {account.friendly_name}")
        print(f"📱 Account SID: {TWILIO_ACCOUNT_SID}")
        print(f"📞 WhatsApp Number: {TWILIO_WHATSAPP_NUMBER}")
        
        # List phone numbers
        print("\n📋 Available phone numbers:")
        phone_numbers = client.incoming_phone_numbers.list()
        for number in phone_numbers:
            print(f"  • {number.phone_number} ({number.friendly_name})")
        
        return True
        
    except Exception as e:
        print(f"❌ Twilio connection failed: {e}")
        return False

def send_test_message(to_number: str):
    """Send a test message to verify WhatsApp integration."""
    print(f"\n📤 Sending test message to {to_number}...")
    
    try:
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        
        # Ensure WhatsApp format
        if not to_number.startswith('whatsapp:'):
            to_number = f"whatsapp:{to_number}"
        
        message = client.messages.create(
            body="🤖 Hello! Your WhatsApp Assistant is now active and ready to help!\n\nTry sending me:\n• 'Hello'\n• 'Help'\n• 'Calculate 15 + 25'\n• 'Remind me to call mom'\n\nI'm here to assist you! 😊",
            from_=TWILIO_WHATSAPP_NUMBER,
            to=to_number
        )
        
        print(f"✅ Test message sent successfully!")
        print(f"📧 Message SID: {message.sid}")
        print(f"📱 Status: {message.status}")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to send test message: {e}")
        return False

def create_env_file():
    """Create .env file with configuration."""
    print("\n📝 Creating .env configuration file...")
    
    env_content = f"""# Twilio Configuration
TWILIO_ACCOUNT_SID={TWILIO_ACCOUNT_SID}
TWILIO_AUTH_TOKEN={TWILIO_AUTH_TOKEN}
TWILIO_WHATSAPP_NUMBER={TWILIO_WHATSAPP_NUMBER}

# Flask Configuration
FLASK_ENV=development
FLASK_DEBUG=True

# OpenAI Configuration (optional - for advanced LLM features)
# OPENAI_API_KEY=your_openai_api_key_here

# Database Configuration
DATABASE_PATH=conversations.db

# Webhook Configuration
WEBHOOK_URL=https://your-domain.com/webhook
"""
    
    with open('.env', 'w') as f:
        f.write(env_content)
    
    print("✅ Created .env file with your configuration")

def setup_webhook_info():
    """Display webhook setup information."""
    print("\n🔗 WEBHOOK SETUP INSTRUCTIONS:")
    print("=" * 50)
    print("To complete your WhatsApp assistant setup, you need to:")
    print()
    print("1. 📡 Deploy your Flask app to a public server:")
    print("   • Use services like Heroku, Railway, or DigitalOcean")
    print("   • Or use ngrok for local testing: ngrok http 5000")
    print()
    print("2. 🔧 Configure Twilio WhatsApp Webhook:")
    print("   • Go to: https://console.twilio.com/us1/develop/sms/settings/whatsapp-sandbox")
    print("   • Set webhook URL to: https://your-domain.com/webhook")
    print("   • Set HTTP method to: POST")
    print()
    print("3. 📱 Test your WhatsApp number:")
    print(f"   • Send 'join [sandbox-keyword]' to: {TWILIO_WHATSAPP_NUMBER}")
    print("   • Then send any message to start chatting!")
    print()
    print("4. 🚀 Optional Enhancements:")
    print("   • Add OpenAI API key for advanced LLM features")
    print("   • Set up database backups")
    print("   • Configure logging and monitoring")

def create_deployment_files():
    """Create deployment configuration files."""
    print("\n📦 Creating deployment files...")
    
    # Procfile for Heroku
    with open('Procfile', 'w') as f:
        f.write('web: gunicorn whatsapp_assistant:app\n')
    
    # Runtime for Heroku
    with open('runtime.txt', 'w') as f:
        f.write('python-3.11.0\n')
    
    # Docker configuration
    dockerfile_content = """FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "whatsapp_assistant:app"]
"""
    
    with open('Dockerfile', 'w') as f:
        f.write(dockerfile_content)
    
    # Railway configuration
    railway_config = {
        "build": {
            "builder": "NIXPACKS"
        },
        "deploy": {
            "startCommand": "gunicorn whatsapp_assistant:app",
            "healthcheckPath": "/health",
            "healthcheckTimeout": 100,
            "restartPolicyType": "ON_FAILURE",
            "restartPolicyMaxRetries": 10
        }
    }
    
    with open('railway.json', 'w') as f:
        json.dump(railway_config, f, indent=2)
    
    print("✅ Created deployment files:")
    print("  • Procfile (Heroku)")
    print("  • runtime.txt (Heroku)")
    print("  • Dockerfile (Docker)")
    print("  • railway.json (Railway)")

def main():
    """Main setup function."""
    print("🤖 WhatsApp Assistant Setup")
    print("=" * 40)
    
    # Test Twilio connection
    if not test_twilio_connection():
        print("\n❌ Setup failed - please check your Twilio credentials")
        return
    
    # Create configuration files
    create_env_file()
    create_deployment_files()
    
    # Ask for test message
    print("\n📱 Would you like to send a test message?")
    test_phone = input("Enter your WhatsApp number (with country code, e.g., +1234567890): ").strip()
    
    if test_phone:
        send_test_message(test_phone)
    
    # Show webhook setup instructions
    setup_webhook_info()
    
    print("\n✅ Setup completed successfully!")
    print("\n🚀 Next steps:")
    print("1. Install dependencies: pip install -r requirements.txt")
    print("2. Run locally: python whatsapp_assistant.py")
    print("3. Deploy to a public server")
    print("4. Configure Twilio webhook")
    print("5. Start chatting with your assistant!")

if __name__ == "__main__":
    main()