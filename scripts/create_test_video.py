"""
Create First Test Video
Demonstrates full pipeline: AI → TTS → Video
"""

import subprocess
import json
import requests
import os
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont

# Configuration
OLLAMA_HOST = "http://localhost:11434"
PIPER_BIN = "/home/chris/piper/piper/piper"
PIPER_MODEL = "/home/chris/piper-voices/en_US-lessac-medium.onnx"
OUTPUT_DIR = "data/videos/pending"

def generate_script():
    """Generate video script using Ollama"""
    print("\n🤖 Generating script with AI...")
    
    prompt = """Write a 15-second YouTube Short script introducing the channel "Testing the Limits of AI". 
Make it exciting and mention that an AI created this video. Keep it under 40 words."""
    
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
            script = result.get('response', '').strip()
            print(f"✅ Script generated: {script[:100]}...")
            return script
        else:
            print(f"❌ AI generation failed")
            return None
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

def text_to_speech(text, output_file):
    """Convert text to speech using Piper"""
    print(f"\n🎤 Converting to speech...")
    
    try:
        process = subprocess.Popen(
            [PIPER_BIN, '--model', PIPER_MODEL, '--output_file', output_file],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        stdout, stderr = process.communicate(input=text.encode())
        
        if process.returncode == 0 and os.path.exists(output_file):
            file_size = os.path.getsize(output_file)
            print(f"✅ Audio created: {file_size:,} bytes")
            return True
        else:
            print(f"❌ TTS failed")
            if stderr:
                print(f"Error: {stderr.decode()}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def create_background_image(width, height, text, output_file):
    """Create simple background image with text"""
    print(f"\n🎨 Creating visual...")
    
    # Create gradient background
    img = Image.new('RGB', (width, height))
    draw = ImageDraw.Draw(img)
    
    # Purple gradient
    for y in range(height):
        r = int(102 + (118 - 102) * y / height)
        g = int(126 + (75 - 126) * y / height)
        b = int(234 + (162 - 234) * y / height)
        draw.rectangle([(0, y), (width, y + 1)], fill=(r, g, b))
    
    # Add text
    try:
        # Try to use a system font
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 80)
    except:
        font = ImageFont.load_default()
    
    # Add title
    title = "YouTube AI Lab"
    subtitle = "Testing the Limits of AI"
    
    # Calculate text positions (centered)
    bbox1 = draw.textbbox((0, 0), title, font=font)
    text_width1 = bbox1[2] - bbox1[0]
    text_height1 = bbox1[3] - bbox1[1]
    
    x1 = (width - text_width1) // 2
    y1 = height // 3
    
    # Draw title with shadow
    draw.text((x1+3, y1+3), title, fill=(0, 0, 0, 128), font=font)
    draw.text((x1, y1), title, fill=(255, 255, 255), font=font)
    
    # Add subtitle
    try:
        font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 40)
    except:
        font_small = font
    
    bbox2 = draw.textbbox((0, 0), subtitle, font=font_small)
    text_width2 = bbox2[2] - bbox2[0]
    x2 = (width - text_width2) // 2
    y2 = y1 + text_height1 + 40
    
    draw.text((x2+2, y2+2), subtitle, fill=(0, 0, 0, 128), font=font_small)
    draw.text((x2, y2), subtitle, fill=(255, 255, 255), font=font_small)
    
    # Add "AI Generated" badge
    badge_text = "🤖 AI Generated"
    try:
        font_badge = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 30)
    except:
        font_badge = font_small
    
    bbox3 = draw.textbbox((0, 0), badge_text, font=font_badge)
    text_width3 = bbox3[2] - bbox3[0]
    x3 = (width - text_width3) // 2
    y3 = height - 150
    
    draw.text((x3, y3), badge_text, fill=(255, 255, 255, 200), font=font_badge)
    
    img.save(output_file)
    print(f"✅ Visual created: {output_file}")
    return True

def create_video(image_file, audio_file, output_file):
    """Combine image and audio into video using FFmpeg"""
    print(f"\n🎬 Creating video...")
    
    try:
        # Get audio duration
        duration_cmd = [
            'ffprobe', '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            audio_file
        ]
        
        duration = float(subprocess.check_output(duration_cmd).decode().strip())
        print(f"📏 Audio duration: {duration:.2f} seconds")
        
        # Create video with FFmpeg
        cmd = [
            'ffmpeg', '-y',
            '-loop', '1',
            '-i', image_file,
            '-i', audio_file,
            '-c:v', 'libx264',
            '-tune', 'stillimage',
            '-c:a', 'aac',
            '-b:a', '192k',
            '-pix_fmt', 'yuv420p',
            '-t', str(duration),
            '-shortest',
            output_file
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0 and os.path.exists(output_file):
            file_size = os.path.getsize(output_file)
            print(f"✅ Video created: {file_size:,} bytes")
            print(f"📁 Location: {output_file}")
            return True
        else:
            print(f"❌ FFmpeg failed")
            print(f"Error: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    """Main video generation pipeline"""
    print("="*70)
    print("🎥 YOUTUBE AI LAB - FIRST VIDEO GENERATION TEST")
    print("="*70)
    
    # Create output directory
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs("data/audio/cache", exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # File paths
    audio_file = f"data/audio/cache/test_{timestamp}.wav"
    image_file = f"data/audio/cache/test_{timestamp}.png"
    video_file = f"{OUTPUT_DIR}/test_video_{timestamp}.mp4"
    
    # Step 1: Generate script
    script = generate_script()
    if not script:
        print("\n❌ Failed to generate script")
        return
    
    # Step 2: Convert to speech
    if not text_to_speech(script, audio_file):
        print("\n❌ Failed to create audio")
        return
    
    # Step 3: Create visual
    if not create_background_image(1080, 1920, script, image_file):
        print("\n❌ Failed to create visual")
        return
    
    # Step 4: Combine into video
    if not create_video(image_file, audio_file, video_file):
        print("\n❌ Failed to create video")
        return
    
    print("\n" + "="*70)
    print("🎉 SUCCESS! First video created!")
    print("="*70)
    print(f"📁 Video: {video_file}")
    print(f"📝 Script: {script}")
    print("\nNext steps:")
    print("  1. Download and watch the video")
    print("  2. Set up YouTube API")
    print("  3. Upload to YouTube")
    print("="*70)

if __name__ == "__main__":
    main()
