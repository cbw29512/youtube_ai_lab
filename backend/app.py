"""
YouTube AI Lab - Fixed Button Handlers & Error Handling
"""

from flask import Flask, render_template, jsonify, request, send_from_directory
from flask_cors import CORS
from flask_socketio import SocketIO
import os
import json
import sqlite3
from datetime import datetime
import subprocess
import requests
import threading
import textwrap
import traceback

# Initialize Flask app
app = Flask(__name__, 
            template_folder='../dashboard/templates',
            static_folder='../dashboard/static')
app.config['SECRET_KEY'] = os.environ.get('YOUTUBE_AI_LAB_SECRET_KEY') or os.urandom(32)

def _env_bool(name, default=False):
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {'1', 'true', 'yes', 'on'}

def _allowed_origins():
    raw = os.environ.get('YOUTUBE_AI_LAB_ALLOWED_ORIGINS', 'http://127.0.0.1:8056,http://localhost:8056')
    return [origin.strip() for origin in raw.split(',') if origin.strip()]

ALLOWED_ORIGINS = _allowed_origins()
CORS(app, origins=ALLOWED_ORIGINS)
socketio = SocketIO(app, cors_allowed_origins=ALLOWED_ORIGINS)

# Load configuration
with open('config/config.json', 'r') as f:
    config = json.load(f)

# Local-first environment overrides. Committed config stays portable and safe.
config['ollama']['host'] = os.environ.get('OLLAMA_HOST', config['ollama']['host'])
config['piper']['binary_path'] = os.environ.get('PIPER_BIN', config['piper']['binary_path'])
config['piper']['model_path'] = os.environ.get('PIPER_MODEL', config['piper']['model_path'])
config['dashboard']['host'] = os.environ.get('YOUTUBE_AI_LAB_HOST', config['dashboard']['host'])
config['dashboard']['port'] = int(os.environ.get('YOUTUBE_AI_LAB_PORT', config['dashboard']['port']))
config['dashboard']['debug'] = _env_bool('YOUTUBE_AI_LAB_DEBUG', config['dashboard'].get('debug', False))

DB_PATH = os.environ.get('YOUTUBE_AI_LAB_DB_PATH', 'data/database/requests.db')

def init_db():
    """Initialize database"""
    os.makedirs('data/database', exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            request_text TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            video_path TEXT,
            script TEXT,
            processed_at TIMESTAMP,
            progress INTEGER DEFAULT 0
        )
    ''')
    conn.commit()
    conn.close()

init_db()

def update_progress(request_id, progress, message):
    """Update progress and emit to client"""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('UPDATE requests SET progress = ? WHERE id = ?', (progress, request_id))
        conn.commit()
        conn.close()
        
        socketio.emit('progress', {
            'request_id': request_id,
            'progress': progress,
            'message': message
        })
    except Exception as e:
        print(f"Error updating progress: {e}")

@app.route('/')
def index():
    """Main dashboard"""
    return render_template('index.html')

@app.route('/api/status')
def status():
    """System status check"""
    return jsonify({
        'status': 'online',
        'timestamp': datetime.now().isoformat(),
        'project': 'YouTube AI Lab',
        'version': '0.4.1'
    })

@app.route('/api/requests', methods=['GET'])
def get_requests():
    """Get all requests"""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('SELECT id, request_text, status, created_at, video_path, script, processed_at, progress FROM requests ORDER BY created_at DESC')
        rows = c.fetchall()
        conn.close()
        
        requests_list = []
        for row in rows:
            requests_list.append({
                'id': row[0],
                'request_text': row[1],
                'status': row[2],
                'created_at': row[3],
                'video_path': row[4],
                'script': row[5],
                'processed_at': row[6],
                'progress': row[7]
            })
        
        return jsonify(requests_list)
    except Exception as e:
        print(f"Error getting requests: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/requests', methods=['POST'])
def add_request():
    """Add new request"""
    try:
        data = request.json
        request_text = data.get('request_text', '').strip()
        
        if not request_text:
            return jsonify({'error': 'Request text required'}), 400
        
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('INSERT INTO requests (request_text) VALUES (?)', (request_text,))
        request_id = c.lastrowid
        conn.commit()
        conn.close()
        
        print(f"✅ Created request #{request_id}")
        return jsonify({'id': request_id, 'status': 'pending'})
    except Exception as e:
        print(f"Error adding request: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/requests/<int:request_id>/approve', methods=['POST'])
def approve_request(request_id):
    """Approve request and generate video"""
    try:
        print(f"📝 Approving request #{request_id}")
        
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('SELECT request_text FROM requests WHERE id = ?', (request_id,))
        row = c.fetchone()
        
        if not row:
            conn.close()
            return jsonify({'error': 'Request not found'}), 404
        
        request_text = row[0]
        
        # Update status to processing
        c.execute('UPDATE requests SET status = ?, progress = ? WHERE id = ?', 
                  ('processing', 0, request_id))
        conn.commit()
        conn.close()
        
        print(f"✅ Request #{request_id} set to processing")
        
        # Generate video in background thread
        thread = threading.Thread(target=generate_video_async, args=(request_text, request_id))
        thread.daemon = True
        thread.start()
        
        return jsonify({'status': 'processing', 'message': 'Video generation started'})
    except Exception as e:
        print(f"❌ Error approving request: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/requests/<int:request_id>/delete', methods=['POST'])
def delete_request(request_id):
    """Delete request and associated video file"""
    try:
        print(f"🗑️ Deleting request #{request_id}")
        
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('SELECT video_path FROM requests WHERE id = ?', (request_id,))
        row = c.fetchone()
        
        if row and row[0]:
            # Delete video file
            video_path = os.path.join('data/videos/pending', row[0])
            if os.path.exists(video_path):
                os.remove(video_path)
                print(f"  Deleted video: {video_path}")
        
        # Delete from database
        c.execute('DELETE FROM requests WHERE id = ?', (request_id,))
        conn.commit()
        conn.close()
        
        print(f"✅ Request #{request_id} deleted")
        return jsonify({'status': 'deleted', 'message': 'Request deleted successfully'})
    except Exception as e:
        print(f"❌ Error deleting request: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/videos/<path:filename>')
def serve_video(filename):
    """Serve video files"""
    try:
        return send_from_directory('../data/videos/pending', filename)
    except Exception as e:
        print(f"Error serving video: {e}")
        return jsonify({'error': 'Video not found'}), 404

def generate_video_async(request_text, request_id):
    """Generate video with progress updates"""
    try:
        print(f"\n{'='*60}")
        print(f"🎬 Starting video generation for request #{request_id}")
        print(f"{'='*60}")
        
        update_progress(request_id, 10, "Generating script with AI...")
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        os.makedirs('data/videos/pending', exist_ok=True)
        os.makedirs('data/audio/cache', exist_ok=True)
        
        audio_file = f"data/audio/cache/request_{request_id}_{timestamp}.wav"
        image_file = f"data/audio/cache/request_{request_id}_{timestamp}.png"
        video_file = f"data/videos/pending/request_{request_id}_{timestamp}.mp4"
        video_filename = f"request_{request_id}_{timestamp}.mp4"
        
        # Step 1: Generate script
        print("Step 1: Generating script...")
        script = generate_script(request_text)
        if not script:
            raise Exception("Failed to generate script")
        print(f"✅ Script: {script[:100]}...")
        
        # Save script to database
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('UPDATE requests SET script = ? WHERE id = ?', (script, request_id))
        conn.commit()
        conn.close()
        
        update_progress(request_id, 40, "Script generated! Converting to speech...")
        
        # Step 2: Convert to speech
        print("Step 2: Converting to speech...")
        if not text_to_speech(script, audio_file):
            raise Exception("Failed to create audio")
        print(f"✅ Audio: {audio_file}")
        
        update_progress(request_id, 60, "Audio created! Generating visual...")
        
        # Step 3: Create visual
        print("Step 3: Creating visual...")
        if not create_visual(script, request_text, image_file):
            raise Exception("Failed to create visual")
        print(f"✅ Visual: {image_file}")
        
        update_progress(request_id, 80, "Visual ready! Building final video...")
        
        # Step 4: Combine into video
        print("Step 4: Creating final video...")
        if not create_video(image_file, audio_file, video_file):
            raise Exception("Failed to create video")
        print(f"✅ Video: {video_file}")
        
        update_progress(request_id, 100, "Video complete!")
        
        # Update database
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('''
            UPDATE requests 
            SET status = ?, video_path = ?, processed_at = CURRENT_TIMESTAMP, progress = 100
            WHERE id = ?
        ''', ('approved', video_filename, request_id))
        conn.commit()
        conn.close()
        
        socketio.emit('video_complete', {'request_id': request_id, 'video_path': video_filename})
        
        print(f"{'='*60}")
        print(f"✅ Video generation complete for request #{request_id}")
        print(f"{'='*60}\n")
        
    except Exception as e:
        print(f"❌ Video generation failed: {e}")
        traceback.print_exc()
        update_progress(request_id, 0, f"Error: {str(e)}")
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('UPDATE requests SET status = ?, progress = 0 WHERE id = ?', ('failed', request_id))
        conn.commit()
        conn.close()

def generate_script(request_text):
    """Generate script using Ollama"""
    prompt = f"""Create a 20-30 second YouTube Short script for this request: "{request_text}"

Rules:
- Write ONLY the spoken narration (no stage directions, camera cues, or sound effects)
- Keep it under 60 words
- Make it engaging and informative
- End with a call to action for comments

Script:"""
    
    payload = {
        "model": "llama3.2:3b-instruct-q4_0",
        "prompt": prompt,
        "stream": False
    }
    
    try:
        response = requests.post(
            f"{config['ollama']['host']}/api/generate",
            json=payload,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            return result.get('response', '').strip()
        return None
    except Exception as e:
        print(f"Ollama error: {e}")
        return None

def text_to_speech(text, output_file):
    """Convert text to speech using explicitly configured local Piper files."""
    try:
        binary_path = config['piper'].get('binary_path', '')
        model_path = config['piper'].get('model_path', '')
        if not binary_path or not model_path:
            print('TTS unavailable: set PIPER_BIN and PIPER_MODEL for local generation')
            return False
        if not os.path.isfile(binary_path) or not os.path.isfile(model_path):
            print('TTS unavailable: configured Piper binary/model does not exist')
            return False
        process = subprocess.Popen(
            [binary_path, '--model', model_path, 
             '--output_file', output_file],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        process.communicate(input=text.encode())
        return process.returncode == 0 and os.path.exists(output_file)
    except Exception as e:
        print(f"TTS error: {e}")
        return False

def create_visual(script, request_text, output_file):
    """Create visual with gradient background and text"""
    try:
        from PIL import Image, ImageDraw, ImageFont
        
        width, height = 1080, 1920
        img = Image.new('RGB', (width, height))
        draw = ImageDraw.Draw(img)
        
        # Gradient background
        for y in range(height):
            r = int(102 + (118 - 102) * y / height)
            g = int(126 + (75 - 126) * y / height)
            b = int(234 + (162 - 234) * y / height)
            draw.rectangle([(0, y), (width, y + 1)], fill=(r, g, b))
        
        # Fonts
        try:
            title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 80)
            subtitle_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 50)
            request_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 40)
        except:
            title_font = subtitle_font = request_font = ImageFont.load_default()
        
        # Title
        title = "YouTube AI Lab"
        bbox = draw.textbbox((0, 0), title, font=title_font)
        title_width = bbox[2] - bbox[0]
        title_x = (width - title_width) // 2
        title_y = 200
        
        draw.text((title_x + 3, title_y + 3), title, fill=(0, 0, 0), font=title_font)
        draw.text((title_x, title_y), title, fill=(255, 255, 255), font=title_font)
        
        # Subtitle
        subtitle = "Testing the Limits of AI"
        bbox2 = draw.textbbox((0, 0), subtitle, font=subtitle_font)
        subtitle_width = bbox2[2] - bbox2[0]
        subtitle_x = (width - subtitle_width) // 2
        subtitle_y = title_y + 120
        
        draw.text((subtitle_x + 2, subtitle_y + 2), subtitle, fill=(0, 0, 0), font=subtitle_font)
        draw.text((subtitle_x, subtitle_y), subtitle, fill=(255, 255, 255), font=subtitle_font)
        
        # Request box
        box_top = height // 2 - 100
        box_height = 400
        draw.rectangle([(50, box_top), (width - 50, box_top + box_height)], 
                      fill=(0, 0, 0, 100), outline=(255, 255, 255))
        
        # Wrapped request text
        wrapped_request = textwrap.fill(f'"{request_text}"', width=25)
        y_offset = box_top + 50
        for line in wrapped_request.split('\n'):
            bbox3 = draw.textbbox((0, 0), line, font=request_font)
            line_width = bbox3[2] - bbox3[0]
            line_x = (width - line_width) // 2
            draw.text((line_x, y_offset), line, fill=(255, 255, 255), font=request_font)
            y_offset += 60
        
        # AI badge
        badge = "🤖 AI Generated"
        try:
            badge_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 35)
        except:
            badge_font = request_font
        
        bbox4 = draw.textbbox((0, 0), badge, font=badge_font)
        badge_width = bbox4[2] - bbox4[0]
        badge_x = (width - badge_width) // 2
        badge_y = height - 200
        
        draw.text((badge_x, badge_y), badge, fill=(255, 255, 255), font=badge_font)
        
        img.save(output_file, quality=95)
        return True
        
    except Exception as e:
        print(f"Visual creation error: {e}")
        traceback.print_exc()
        return False

def create_video(image_file, audio_file, output_file):
    """Combine image and audio into video"""
    try:
        # Get audio duration
        duration_cmd = [
            'ffprobe', '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            audio_file
        ]
        
        duration = float(subprocess.check_output(duration_cmd).decode().strip())
        
        # Create video
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
            '-vf', 'scale=1080:1920',
            '-shortest',
            output_file
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.returncode == 0 and os.path.exists(output_file)
        
    except Exception as e:
        print(f"Video creation error: {e}")
        traceback.print_exc()
        return False

if __name__ == '__main__':
    host = config['dashboard']['host']
    port = config['dashboard']['port']
    debug = bool(config['dashboard'].get('debug', False))
    allow_remote = _env_bool('YOUTUBE_AI_LAB_ALLOW_REMOTE', False)
    loopback_hosts = {'127.0.0.1', 'localhost', '::1'}
    if host not in loopback_hosts and not allow_remote:
        raise RuntimeError(
            'Refusing non-loopback dashboard bind. Set YOUTUBE_AI_LAB_ALLOW_REMOTE=1 only on a trusted network.'
        )
    
    print(f"\n{'='*60}")
    print(f"🚀 YouTube AI Lab Starting...")
    print(f"{'='*60}")
    print(f"📍 Dashboard: http://{host}:{port}")
    print(f"🤖 Ollama: {config['ollama']['host']}")
    print(f"🎤 Piper: {config['piper']['binary_path']}")
    print(f"📊 Database: {DB_PATH}")
    print(f"{'='*60}\n")
    
    socketio.run(app, host=host, port=port, debug=debug, allow_unsafe_werkzeug=True)
