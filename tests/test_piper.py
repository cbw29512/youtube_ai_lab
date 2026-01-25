"""Test Piper TTS Integration"""
import subprocess
import os

# Correct path to Piper TTS
PIPER_BIN = "/home/chris/piper/piper/piper"
PIPER_MODEL = "/home/chris/piper-voices/en_US-lessac-medium.onnx"
OUTPUT_DIR = "data/audio/cache"

def test_piper_tts():
    """Test Piper text-to-speech"""
    print("="*60)
    print("PIPER TTS INTEGRATION TEST")
    print("="*60)
    
    # Check if Piper exists
    if not os.path.exists(PIPER_BIN):
        print(f"❌ Piper not found at: {PIPER_BIN}")
        return False
    
    # Check if model exists
    if not os.path.exists(PIPER_MODEL):
        print(f"❌ Model not found at: {PIPER_MODEL}")
        return False
    
    # Create output directory
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Test text
    text = "Hello from YouTube AI Lab. This is a test of the text to speech system."
    output_file = f"{OUTPUT_DIR}/test_output.wav"
    
    print(f"\n🎤 Generating speech...")
    print(f"📝 Text: {text}")
    
    try:
        # Run Piper with correct syntax
        process = subprocess.Popen(
            [PIPER_BIN, '--model', PIPER_MODEL, '--output_file', output_file],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        stdout, stderr = process.communicate(input=text.encode())
        
        if process.returncode == 0 and os.path.exists(output_file):
            file_size = os.path.getsize(output_file)
            print(f"✅ Audio generated successfully!")
            print(f"📁 File: {output_file}")
            print(f"📊 Size: {file_size:,} bytes")
            return True
        else:
            print(f"❌ Piper failed!")
            if stderr:
                print(f"Error: {stderr.decode()}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    test_piper_tts()
    print("="*60)
