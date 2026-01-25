"""Test Ollama AI Integration"""
import requests
import json

OLLAMA_HOST = "http://localhost:11434"

def test_ollama_connection():
    """Test if Ollama is responding"""
    try:
        response = requests.get(f"{OLLAMA_HOST}/api/tags")
        if response.status_code == 200:
            models = response.json()
            print("✅ Ollama is running!")
            print(f"📦 Available models: {len(models.get('models', []))}")
            for model in models.get('models', []):
                print(f"   - {model['name']}")
            return True
        else:
            print("❌ Ollama responded but with error")
            return False
    except Exception as e:
        print(f"❌ Cannot connect to Ollama: {e}")
        return False

def test_ollama_generate():
    """Test AI text generation"""
    print("\n🤖 Testing AI generation...")
    
    prompt = "Write a 10-word YouTube video title about AI testing limits"
    
    payload = {
        "model": "llama3.2:3b-instruct-q4_0",
        "prompt": prompt,
        "stream": False
    }
    
    try:
        response = requests.post(
            f"{OLLAMA_HOST}/api/generate",
            json=payload,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            generated_text = result.get('response', '')
            print(f"✅ AI Response: {generated_text.strip()}")
            return True
        else:
            print(f"❌ Generation failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error during generation: {e}")
        return False

if __name__ == "__main__":
    print("="*60)
    print("OLLAMA AI INTEGRATION TEST")
    print("="*60)
    
    if test_ollama_connection():
        test_ollama_generate()
    
    print("\n" + "="*60)
