"""
YouTube AI Lab - Main Application
Testing the Limits of AI
"""

from flask import Flask, render_template, jsonify
from flask_cors import CORS
import os
import json
from datetime import datetime

# Initialize Flask app
app = Flask(__name__, 
            template_folder='../dashboard/templates',
            static_folder='../dashboard/static')
CORS(app)

# Load configuration
with open('config/config.json', 'r') as f:
    config = json.load(f)

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
        'version': '0.1.0',
        'ollama_configured': True,
        'piper_configured': True
    })

@app.route('/api/config')
def get_config():
    """Get current configuration"""
    return jsonify(config)

if __name__ == '__main__':
    # Create logs directory if it doesn't exist
    os.makedirs('data/logs', exist_ok=True)
    
    # Run Flask app
    host = config['dashboard']['host']
    port = config['dashboard']['port']
    debug = config['dashboard']['debug']
    
    print(f"\n{'='*60}")
    print(f"🚀 YouTube AI Lab Starting...")
    print(f"{'='*60}")
    print(f"📍 Dashboard: http://192.168.50.50:{port}")
    print(f"🤖 Ollama: {config['ollama']['host']}")
    print(f"🎤 Piper: {config['piper']['model_path']}")
    print(f"{'='*60}\n")
    
    app.run(host=host, port=port, debug=debug)
