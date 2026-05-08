#!/usr/bin/env python3
"""
Script to update configuration files from config.json
Run this script when you need to update configuration for build/deployment
"""

import os
import json
import sys

def update_chrome_extension_config():
    """Update chrome-extension/config.js from config.json"""
    config_path = os.path.join(os.path.dirname(__file__), "config.json")
    output_path = os.path.join(os.path.dirname(__file__), "chrome-extension", "config.js")
    
    if not os.path.exists(config_path):
        print(f"❌ config.json not found at {config_path}")
        return False
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # Generate config.js content
        content = f"""// Configuration for Chrome Extension
// Auto-generated from config.json - DO NOT EDIT MANUALLY
// Last updated: {sys.argv[1] if len(sys.argv) > 1 else "manual"}

const CONFIG = {{
  apiEndpoints: {{
    backend: "{config['apiEndpoints']['backend']}",
    queueSystem: "{config['apiEndpoints']['queueSystem']}"
  }},
  targetUrl: "{config['targetUrl']}",
  settings: {{
    autoDetect: {str(config['extensionSettings']['autoDetect']).lower()},
    debugMode: {str(config['extensionSettings']['debugMode']).lower()},
    timeout: {config['extensionSettings']['timeout']}
  }}
}};
"""
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"✅ Updated {output_path}")
        return True
        
    except Exception as e:
        print(f"❌ Error updating chrome extension config: {e}")
        return False

def check_backend_config():
    """Check if backend config.py is compatible with config.json"""
    config_path = os.path.join(os.path.dirname(__file__), "config.json")
    
    if not os.path.exists(config_path):
        print(f"❌ config.json not found at {config_path}")
        return False
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        print("📋 Current configuration from config.json:")
        print(f"  • Backend API: {config['apiEndpoints']['backend']}")
        print(f"  • Queue System API: {config['apiEndpoints']['queueSystem']}")
        print(f"  • Target URL: {config['targetUrl']}")
        print(f"  • Backend Host: {config['backendSettings']['host']}")
        print(f"  • Backend Port: {config['backendSettings']['port']}")
        print(f"  • Upload Dir: {config['backendSettings']['uploadDir']}")
        print(f"  • PDF Dir: {config['backendSettings']['pdfDir']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error reading config.json: {e}")
        return False

def main():
    print("🔄 Updating configuration files...")
    print("=" * 50)
    
    if check_backend_config():
        print("\n" + "=" * 50)
        
        if update_chrome_extension_config():
            print("\n✅ Configuration update completed successfully!")
            print("\n📝 Next steps:")
            print("  1. Reload Chrome extension in chrome://extensions/")
            print("  2. Restart backend server if needed")
            print("  3. Test the system with new configuration")
        else:
            print("\n❌ Failed to update chrome extension configuration")
    else:
        print("\n❌ Failed to read config.json")

if __name__ == "__main__":
    main()