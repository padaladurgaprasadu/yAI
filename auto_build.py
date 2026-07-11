#!/usr/bin/env python3
"""
yAI Auto-Pilot - Full End-to-End Automation with API Key Support
"""

import os
import sys
import subprocess
import time
import webbrowser
import json
import re
from pathlib import Path

class AiONAutoPilot:
    def __init__(self, goal):
        self.goal = goal
        self.project_dir = "generated_project"
        self.backend_process = None
        self.frontend_process = None
        self.backend_port = 3001
        self.frontend_port = 3000
        self.api_keys = {}  # Store all API keys
        
    def run(self):
        """Main execution flow"""
        print("\n" + "="*60)
        print("🚀 yAI AUTO-PILOT - Full Automation")
        print("="*60)
        print(f"📝 Goal: {self.goal}\n")
        
        # Step 1: Generate the project
        if not self.generate_project():
            print("❌ Project generation failed")
            return False
        
        # Step 2: Install dependencies
        if not self.install_dependencies():
            print("❌ Dependency installation failed")
            return False
        
        # Step 3: Fix common issues
        self.fix_missing_files()
        
        # Step 4: 🆕 ASK FOR API KEYS
        self.ask_for_api_keys()
        
        # Step 5: Start the backend
        if not self.start_backend():
            print("❌ Backend failed to start")
            return False
        
        # Step 6: Start the frontend
        if not self.start_frontend():
            print("❌ Frontend failed to start")
            return False
        
        # Step 7: Open browser
        self.open_browser()
        
        # Step 8: Show success
        self.show_success()
        
        return True
    
    def generate_project(self):
        """Step 1: Generate code using yAI"""
        print("📦 [1/8] Generating project with yAI...")
        
        try:
            result = subprocess.run(
                ["python", "backend/main.py", self.goal],
                capture_output=True,
                text=True,
                timeout=120
            )
            
            print(result.stdout)
            if result.stderr:
                print("⚠️ Warnings:", result.stderr)
            
            if os.path.exists(self.project_dir):
                print("✅ Project generated successfully!")
                return True
            else:
                print("❌ Project folder not found")
                return False
                
        except subprocess.TimeoutExpired:
            print("❌ Generation timed out")
            return False
        except Exception as e:
            print(f"❌ Error: {e}")
            return False
    
    def install_dependencies(self):
        """Step 2: Install npm dependencies"""
        print("\n📦 [2/8] Installing dependencies...")
        
        try:
            subprocess.run(
                ["npm", "install"],
                cwd=self.project_dir,
                check=True,
                capture_output=True,
                text=True,
                shell=True
            )
            print("✅ Dependencies installed!")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ npm install failed: {e.stderr}")
            return False
    
    def fix_missing_files(self):
        """Step 3: Fix common missing files"""
        print("\n🔧 [3/8] Fixing common issues...")
        
        src_dir = Path(self.project_dir) / "src"
        
        # Create missing files
        missing_files = [
            (src_dir / "index.css", self.get_index_css()),
            (src_dir / "reportWebVitals.js", self.get_report_web_vitals()),
            (src_dir / "config.js", self.get_config_js()),
            (src_dir / "components" / "styles" / "WeatherDisplay.css", self.get_weather_css())
        ]
        
        for file_path, content in missing_files:
            if not file_path.exists():
                file_path.parent.mkdir(parents=True, exist_ok=True)
                with open(file_path, "w") as f:
                    f.write(content)
                print(f"   ✅ Created: {file_path}")
        
        # Install missing npm packages
        try:
            subprocess.run(
                ["npm", "install", "zustand", "react", "react-dom", "react-router-dom"],
                cwd=self.project_dir,
                check=True,
                capture_output=True,
                text=True,
                shell=True
            )
            print("   ✅ Missing packages installed")
        except:
            pass
        
        print("✅ Fixes applied!")
    
    def ask_for_api_keys(self):
        """🆕 Step 4: Ask user for API keys"""
        print("\n🔑 [4/8] Checking for API keys...")
        
        # Detect what APIs the project needs
        needed_keys = self.detect_needed_apis()
        
        if not needed_keys:
            print("✅ No API keys needed for this project")
            return
        
        print(f"📋 This project needs the following API keys:")
        for key in needed_keys:
            print(f"   - {key}")
        
        print("\n" + "-"*40)
        print("📝 Please enter your API keys (press Enter to skip):")
        print("-"*40)
        
        for key in needed_keys:
            while True:
                value = input(f"🔑 Enter {key}: ").strip()
                if value:
                    self.api_keys[key] = value
                    break
                else:
                    skip = input(f"⚠️ Skip {key}? (y/n): ").strip().lower()
                    if skip == 'y':
                        break
        
        # Write keys to .env file
        self.write_env_file()
        
        print("✅ API keys configured!")
    
    def detect_needed_apis(self):
        """Detect what API keys the project needs"""
        keys = []
        
        # Check for weather API
        weather_patterns = ['weather', 'openweather', 'temp', 'forecast']
        for pattern in weather_patterns:
            if pattern in self.goal.lower():
                keys.append("OPENWEATHER_API_KEY")
                break
        
        # Check for Stripe
        if 'stripe' in self.goal.lower() or 'payment' in self.goal.lower():
            keys.append("STRIPE_SECRET_KEY")
            keys.append("STRIPE_PUBLISHABLE_KEY")
        
        # Check for Twilio
        if 'twilio' in self.goal.lower() or 'sms' in self.goal.lower():
            keys.append("TWILIO_ACCOUNT_SID")
            keys.append("TWILIO_AUTH_TOKEN")
        
        # Check for AWS
        if 'aws' in self.goal.lower() or 's3' in self.goal.lower():
            keys.append("AWS_ACCESS_KEY_ID")
            keys.append("AWS_SECRET_ACCESS_KEY")
            keys.append("AWS_REGION")
        
        # Check for general API keys in the code
        if not keys:
            env_file = Path(self.project_dir) / ".env"
            if env_file.exists():
                with open(env_file, "r") as f:
                    content = f.read()
                    # Find any unset API keys
                    matches = re.findall(r'([A-Z_]+_API_KEY)=', content)
                    if matches:
                        keys = list(set(matches))
        
        return keys
    
    def write_env_file(self):
        """Write API keys to .env file"""
        env_path = Path(self.project_dir) / ".env"
        
        # Read existing .env content
        existing = {}
        if env_path.exists():
            with open(env_path, "r") as f:
                for line in f:
                    if "=" in line:
                        key, val = line.strip().split("=", 1)
                        existing[key] = val
        
        # Update with new keys
        existing.update(self.api_keys)
        
        # Write back
        with open(env_path, "w") as f:
            for key, val in existing.items():
                if val and not val.startswith("your_"):
                    f.write(f"{key}={val}\n")
                else:
                    # Skip placeholder values
                    pass
        
        print(f"✅ .env file updated with {len(self.api_keys)} API keys")
    
    def get_index_css(self):
        return """body {
  margin: 0;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen',
    'Ubuntu', 'Cantarell', 'Fira Sans', 'Droid Sans', 'Helvetica Neue',
    sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}
code {
  font-family: source-code-pro, Menlo, Monaco, Consolas, 'Courier New', monospace;
}
"""
    
    def get_report_web_vitals(self):
        return """const reportWebVitals = onPerfEntry => {
  if (onPerfEntry && onPerfEntry instanceof Function) {
    import('web-vitals').then(({ getCLS, getFID, getFCP, getLCP, getTTFB }) => {
      getCLS(onPerfEntry);
      getFID(onPerfEntry);
      getFCP(onPerfEntry);
      getLCP(onPerfEntry);
      getTTFB(onPerfEntry);
    });
  }
};
export default reportWebVitals;
"""
    
    def get_config_js(self):
        return """export const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:3001/api/v1';
export default { API_BASE_URL };
"""
    
    def get_weather_css(self):
        return """.weather-container {
  padding: 20px;
  background: #f0f4f8;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}
.weather-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.weather-temp {
  font-size: 2.5rem;
  font-weight: bold;
  color: #2c3e50;
}
"""
    
    def start_backend(self):
        """Step 5: Start backend"""
        print("\n🚀 [5/8] Starting backend server...")
        
        try:
            self.backend_process = subprocess.Popen(
                ["node", "server.js"],
                cwd=self.project_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                shell=True
            )
            
            time.sleep(3)
            
            if self.backend_process.poll() is None:
                print(f"✅ Backend running on port {self.backend_port}")
                return True
            else:
                print("❌ Backend failed to start")
                return False
                
        except Exception as e:
            print(f"❌ Error: {e}")
            return False
    
    def start_frontend(self):
        """Step 6: Start frontend"""
        print("\n🌐 [6/8] Starting frontend server...")
        
        frontend_dir = Path(self.project_dir) / "client"
        if not frontend_dir.exists():
            frontend_dir = Path(self.project_dir)
        
        try:
            self.frontend_process = subprocess.Popen(
                ["npm", "start"],
                cwd=str(frontend_dir),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                shell=True
            )
            
            time.sleep(5)
            
            print(f"✅ Frontend running on port {self.frontend_port}")
            return True
            
        except Exception as e:
            print(f"❌ Error: {e}")
            return False
    
    def open_browser(self):
        """Step 7: Open browser"""
        print("\n🌍 [7/8] Opening browser...")
        webbrowser.open(f"http://localhost:{self.frontend_port}")
        print(f"✅ Browser opened at http://localhost:{self.frontend_port}")
    
    def show_success(self):
        """Step 8: Show success"""
        print("\n" + "="*60)
        print("🎉 BUILD COMPLETE!")
        print("="*60)
        print(f"📝 Goal: {self.goal}")
        print(f"🌐 Frontend: http://localhost:{self.frontend_port}")
        print(f"📡 Backend: http://localhost:{self.backend_port}")
        print(f"📁 Project: {os.path.abspath(self.project_dir)}")
        if self.api_keys:
            print(f"🔑 API Keys configured: {', '.join(self.api_keys.keys())}")
        print("\n🛑 Press Ctrl+C to stop servers")
        print("="*60)
        
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            self.shutdown()
    
    def shutdown(self):
        print("\n🛑 Shutting down...")
        if self.backend_process:
            self.backend_process.terminate()
        if self.frontend_process:
            self.frontend_process.terminate()
        print("👋 Goodbye!")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python auto_build.py \"Your app idea\"")
        print("Example: python auto_build.py \"Build a weather dashboard\"")
        sys.exit(1)
    
    goal = " ".join(sys.argv[1:])
    pilot = AiONAutoPilot(goal)
    pilot.run()
