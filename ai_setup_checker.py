#!/usr/bin/env python3
"""
AI Setup Checker - Verify AI system configuration
Checks Llama server, models, and configuration before testing
"""

import os
import sys
import requests
import subprocess
from pathlib import Path


def check_ollama_installation():
    """Check if Ollama is installed"""
    print("🔍 Checking Ollama installation...")

    try:
        result = subprocess.run(['ollama', '--version'],
                                capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            version = result.stdout.strip()
            print(f"✅ Ollama installed: {version}")
            return True
        else:
            print("❌ Ollama not found")
            return False
    except FileNotFoundError:
        print("❌ Ollama not installed")
        return False
    except subprocess.TimeoutExpired:
        print("❌ Ollama check timed out")
        return False


def check_ollama_server():
    """Check if Ollama server is running"""
    print("\n🌐 Checking Ollama server...")

    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        if response.status_code == 200:
            print("✅ Ollama server is running")
            return True, response.json()
        else:
            print(f"❌ Server error: {response.status_code}")
            return False, None
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to Ollama server")
        print("   Run: ollama serve")
        return False, None
    except Exception as e:
        print(f"❌ Server check error: {e}")
        return False, None


def check_models(api_response):
    """Check available models"""
    print("\n🤖 Checking available models...")

    if not api_response:
        return False

    models = api_response.get('models', [])
    if not models:
        print("❌ No models installed")
        return False

    print("📋 Available models:")
    for model in models:
        name = model.get('name', 'unknown')
        size = model.get('size', 0)
        size_mb = size / (1024 * 1024) if size else 0
        print(f"   • {name} ({size_mb:.1f}MB)")

    # Check for llama2
    llama_models = [m for m in models if 'llama2' in m.get('name', '').lower()]
    if llama_models:
        print("✅ Llama2 model found")
        return True
    else:
        print("❌ Llama2 model not found")
        print("   Run: ollama pull llama2")
        return False


def check_project_structure():
    """Check if project files exist"""
    print("\n📁 Checking project structure...")

    required_files = [
        'config.py',
        'services/llama_ai.py',
        'models/message.py',
        'models/product.py',
        'utils/logger.py'
    ]

    missing_files = []
    for file_path in required_files:
        if os.path.exists(file_path):
            print(f"✅ {file_path}")
        else:
            print(f"❌ {file_path} - MISSING")
            missing_files.append(file_path)

    return len(missing_files) == 0


def check_environment_variables():
    """Check environment variables"""
    print("\n🔧 Checking environment configuration...")

    env_vars = {
        'LLAMA_SERVER_URL': 'http://localhost:11434',
        'LLAMA_MODEL_NAME': 'llama2',
        'LLAMA_TEMPERATURE': '0.7',
        'AUTO_REPLY_ENABLED': 'True'
    }

    for var, default in env_vars.items():
        value = os.getenv(var, default)
        print(f"   {var}: {value}")

    return True


def check_dependencies():
    """Check Python dependencies"""
    print("\n📦 Checking Python dependencies...")

    required_packages = ['requests', 'selenium', 'webdriver-manager']
    missing_packages = []

    for package in required_packages:
        try:
            __import__(package)
            print(f"✅ {package}")
        except ImportError:
            print(f"❌ {package} - MISSING")
            missing_packages.append(package)

    if missing_packages:
        print(f"\n💡 Install missing packages:")
        print(f"   pip install {' '.join(missing_packages)}")
        return False

    return True


def provide_setup_instructions():
    """Provide setup instructions if checks fail"""
    print("\n🛠️  SETUP INSTRUCTIONS")
    print("=" * 50)
    print("1. Install Ollama:")
    print("   • Visit: https://ollama.ai")
    print("   • Download and install for your OS")
    print()
    print("2. Install Llama2 model:")
    print("   ollama pull llama2")
    print()
    print("3. Start Ollama server:")
    print("   ollama serve")
    print()
    print("4. Install Python dependencies:")
    print("   pip install requests selenium webdriver-manager")
    print()
    print("5. Create .env file with:")
    print("   LLAMA_SERVER_URL=http://localhost:11434")
    print("   LLAMA_MODEL_NAME=llama2")
    print("   AUTO_REPLY_ENABLED=True")


def main():
    """Main checker function"""
    print("🔧 AI Setup Checker")
    print("=" * 40)
    print("Verifying AI system configuration...\n")

    checks = []

    # Run all checks
    checks.append(("Ollama Installation", check_ollama_installation()))

    server_running, api_response = check_ollama_server()
    checks.append(("Ollama Server", server_running))

    if server_running:
        checks.append(("Models Available", check_models(api_response)))
    else:
        checks.append(("Models Available", False))

    checks.append(("Project Structure", check_project_structure()))
    checks.append(("Dependencies", check_dependencies()))
    checks.append(("Environment Config", check_environment_variables()))

    # Summary
    print("\n📋 SETUP SUMMARY")
    print("-" * 40)

    passed = 0
    for check_name, result in checks:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{check_name:20} {status}")
        if result:
            passed += 1

    print(f"\nPassed: {passed}/{len(checks)} checks")

    if passed == len(checks):
        print("\n🎉 All checks passed! AI system ready for testing.")
        print("   Run: python ai_test_script.py")
        return True
    else:
        print(f"\n⚠️  {len(checks) - passed} checks failed.")
        provide_setup_instructions()
        return False


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⏹️  Setup check interrupted")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)