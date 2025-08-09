#!/usr/bin/env python3
"""
ChunkHound + WhatsApp Assistant Integration
Demonstrates how to integrate code search capabilities into your WhatsApp assistant.
"""

import os
import sys
import json
import requests
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Any

class ChunkHoundIntegration:
    """Integration between ChunkHound code search and WhatsApp Assistant."""
    
    def __init__(self, project_path: str = "/workspace/test_project"):
        self.project_path = Path(project_path)
        self.server_url = "http://localhost:8000"
        self.server_process = None
        
    def start_chunkhound_server(self) -> bool:
        """Start ChunkHound MCP server."""
        try:
            # Change to project directory
            os.chdir(self.project_path)
            
            # Start server in background
            cmd = ["chunkhound", "serve", "--http", "--port", "8000"]
            self.server_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=self.project_path
            )
            
            # Wait a moment for server to start
            import time
            time.sleep(2)
            
            # Test server health
            response = requests.get(f"{self.server_url}/health", timeout=5)
            return response.status_code == 200
            
        except Exception as e:
            print(f"Failed to start ChunkHound server: {e}")
            return False
    
    def stop_chunkhound_server(self):
        """Stop ChunkHound server."""
        if self.server_process:
            self.server_process.terminate()
            self.server_process.wait()
    
    def search_code(self, query: str, search_type: str = "regex") -> Dict[str, Any]:
        """Search code using ChunkHound."""
        try:
            if search_type == "regex":
                endpoint = f"{self.server_url}/search_regex_local"
            else:
                endpoint = f"{self.server_url}/search_semantic_local"
            
            response = requests.post(
                endpoint,
                json={"query": query},
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"Search failed: {response.status_code}"}
                
        except Exception as e:
            return {"error": f"Search error: {e}"}
    
    def format_search_results(self, results: Dict[str, Any], query: str) -> str:
        """Format search results for WhatsApp display."""
        if "error" in results:
            return f"🔍 **Code Search Error**\n{results['error']}"
        
        if not results.get("results"):
            return f"🔍 **No Results Found**\n\nNo code found matching: `{query}`"
        
        # Format results
        formatted = f"🔍 **Code Search Results**\n\n**Query**: `{query}`\n**Found**: {len(results['results'])} matches\n\n"
        
        for i, result in enumerate(results["results"][:3], 1):  # Limit to 3 results
            file_path = result.get("file_path", "unknown")
            content = result.get("content", "")
            
            # Truncate content for WhatsApp
            if len(content) > 200:
                content = content[:200] + "..."
            
            formatted += f"**{i}. {file_path}**\n```\n{content}\n```\n\n"
        
        if len(results["results"]) > 3:
            formatted += f"... and {len(results['results']) - 3} more results\n"
        
        return formatted

class WhatsAppCodeAssistant:
    """Enhanced WhatsApp assistant with code search capabilities."""
    
    def __init__(self):
        self.chunkhound = ChunkHoundIntegration()
        self.code_search_enabled = False
    
    def enable_code_search(self) -> bool:
        """Enable code search functionality."""
        success = self.chunkhound.start_chunkhound_server()
        self.code_search_enabled = success
        return success
    
    def disable_code_search(self):
        """Disable code search functionality."""
        self.chunkhound.stop_chunkhound_server()
        self.code_search_enabled = False
    
    def handle_code_search_request(self, message: str) -> Optional[str]:
        """Handle code search requests from WhatsApp messages."""
        if not self.code_search_enabled:
            return None
        
        message_lower = message.lower()
        
        # Detect code search requests
        search_triggers = [
            "search code",
            "find code",
            "search for",
            "find function",
            "find class",
            "search function",
            "search class"
        ]
        
        if not any(trigger in message_lower for trigger in search_triggers):
            return None
        
        # Extract search query
        query = self._extract_search_query(message)
        if not query:
            return "🔍 **Code Search**\n\nPlease specify what to search for!\n\nExamples:\n• 'Search code for User class'\n• 'Find function calculate_total'\n• 'Search for SQL queries'"
        
        # Perform search
        results = self.chunkhound.search_code(query, "regex")
        return self.chunkhound.format_search_results(results, query)
    
    def _extract_search_query(self, message: str) -> str:
        """Extract search query from message."""
        message_lower = message.lower()
        
        # Remove common prefixes
        prefixes = [
            "search code for",
            "find code for", 
            "search for",
            "find function",
            "find class",
            "search function",
            "search class"
        ]
        
        query = message_lower
        for prefix in prefixes:
            if query.startswith(prefix):
                query = query[len(prefix):].strip()
                break
        
        return query
    
    def get_code_search_help(self) -> str:
        """Get help text for code search functionality."""
        if not self.code_search_enabled:
            return "🔍 **Code Search**: Currently disabled\n\nTo enable code search, the assistant needs access to a ChunkHound server."
        
        return """🔍 **Code Search Available!**

**Commands:**
• `Search code for [query]` - Search all code
• `Find function [name]` - Find specific function
• `Find class [name]` - Find specific class
• `Search for SQL` - Find SQL queries
• `Search for error handling` - Find try/catch blocks

**Examples:**
• "Search code for User class"
• "Find function calculate_total"
• "Search for database connections"
• "Find all TODO comments"

The search uses regex patterns and can find:
✅ Functions and classes
✅ Variable declarations  
✅ SQL queries
✅ Error handling
✅ Comments and TODOs
✅ Import statements"""

def demonstrate_integration():
    """Demonstrate ChunkHound + WhatsApp integration."""
    
    print("🤖 ChunkHound + WhatsApp Assistant Integration Demo")
    print("=" * 55)
    
    # Initialize assistant
    assistant = WhatsAppCodeAssistant()
    
    # Enable code search
    print("🔍 Starting ChunkHound server...")
    if assistant.enable_code_search():
        print("✅ Code search enabled!")
    else:
        print("❌ Failed to enable code search")
        return
    
    # Test search queries
    test_queries = [
        "Search code for User class",
        "Find function validate_email", 
        "Search for SQL queries",
        "Find error handling",
        "Search for database connections"
    ]
    
    print("\n📱 Testing WhatsApp Code Search Queries:")
    print("-" * 45)
    
    for query in test_queries:
        print(f"\n🔹 User: '{query}'")
        response = assistant.handle_code_search_request(query)
        if response:
            print("🤖 Assistant:")
            # Truncate for demo
            lines = response.split('\n')
            for line in lines[:10]:  # Show first 10 lines
                print(f"   {line}")
            if len(lines) > 10:
                print(f"   ... ({len(lines) - 10} more lines)")
        else:
            print("🤖 Assistant: (No code search response)")
        print("-" * 45)
    
    # Show help
    print(f"\n📚 Code Search Help:")
    help_text = assistant.get_code_search_help()
    for line in help_text.split('\n'):
        print(f"   {line}")
    
    # Cleanup
    print(f"\n🧹 Cleaning up...")
    assistant.disable_code_search()
    print("✅ Demo complete!")

def create_enhanced_whatsapp_assistant():
    """Create enhanced WhatsApp assistant with ChunkHound integration."""
    
    enhanced_code = '''
# Add this to your whatsapp_assistant.py

from chunkhound_whatsapp_integration import WhatsAppCodeAssistant

class EnhancedLLMAssistant(LLMAssistant):
    """Enhanced LLM assistant with code search capabilities."""
    
    def __init__(self):
        super().__init__()
        self.code_assistant = WhatsAppCodeAssistant()
        
        # Try to enable code search
        if self.code_assistant.enable_code_search():
            print("✅ Code search enabled")
        else:
            print("⚠️  Code search disabled - ChunkHound not available")
    
    async def generate_response(self, message: str, conversation_history: list, user_context: Dict[str, Any]) -> str:
        """Enhanced response generation with code search."""
        
        # Check for code search requests first
        code_search_response = self.code_assistant.handle_code_search_request(message)
        if code_search_response:
            return code_search_response
        
        # Check for code search help
        if "code search help" in message.lower():
            return self.code_assistant.get_code_search_help()
        
        # Fall back to regular LLM response
        return await super().generate_response(message, conversation_history, user_context)
'''
    
    print("🔧 Enhanced WhatsApp Assistant Code:")
    print("=" * 40)
    print(enhanced_code)

if __name__ == "__main__":
    print("🚀 ChunkHound + WhatsApp Integration")
    print("=" * 40)
    
    # Check if test project exists
    test_project = Path("/workspace/test_project")
    if not test_project.exists():
        print("❌ Test project not found at /workspace/test_project")
        print("   Run the ChunkHound setup first to create test code.")
        sys.exit(1)
    
    # Run demonstration
    try:
        demonstrate_integration()
    except KeyboardInterrupt:
        print("\n🛑 Demo interrupted")
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
    
    # Show integration code
    print("\n" + "=" * 60)
    create_enhanced_whatsapp_assistant()
    
    print("\n🎯 Integration Benefits:")
    print("• 🔍 Search your codebase via WhatsApp")
    print("• 📱 Find functions, classes, and patterns instantly")
    print("• 🤖 Combine AI assistance with code search")
    print("• 🚀 Perfect for code reviews and debugging")
    print("• 📊 Works with any programming language")