from flask import Flask, request, send_file, jsonify, send_from_directory
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_httpauth import HTTPTokenAuth
from flask_apispec import FlaskApiSpec, doc, use_kwargs, marshal_with
from flask_apispec.views import MethodResource
from marshmallow import Schema, fields
from apispec import APISpec
from apispec.ext.marshmallow import MarshmallowPlugin
from melo.api import TTS
import io
import threading
import tempfile
import os
import logging
import sys
import datetime
from functools import wraps

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# Get the directory containing server.py
current_dir = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__, static_folder=current_dir, static_url_path='')
CORS(app)

# Setup API documentation
app.config.update({
    'APISPEC_SPEC': APISpec(
        title='MeloTTS API',
        version='v1',
        plugins=[MarshmallowPlugin()],
        openapi_version='3.0.2',
        info=dict(description='API for text-to-speech synthesis')
    ),
    'APISPEC_SWAGGER_URL': '/api/swagger.json',
    'APISPEC_SWAGGER_UI_URL': '/docs'
})
docs = FlaskApiSpec(app)

# Setup rate limiter
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)

# Setup authentication
auth = HTTPTokenAuth(scheme='Bearer')

# For demo purposes - in production, use a secure database or environment variables
API_KEYS = {
    "test_key": "demo"  # In production, use secure keys
}

@auth.verify_token
def verify_token(token):
    if token in API_KEYS:
        return API_KEYS[token]
    return None

# Define available voices
AVAILABLE_VOICES = {
    'EN-US': {'name': 'English (American)', 'code': 'EN'},
    'EN-BR': {'name': 'English (British)', 'code': 'EN'},
    'EN-IN': {'name': 'English (Indian)', 'code': 'EN'},
    'EN-AU': {'name': 'English (Australian)', 'code': 'EN'},
    'EN': {'name': 'English (Default)', 'code': 'EN'},
    'ES': {'name': 'Spanish', 'code': 'ES'},
    'FR': {'name': 'French', 'code': 'FR'},
    'ZH': {'name': 'Chinese', 'code': 'ZH'},
    'JP': {'name': 'Japanese', 'code': 'JP'},
    'KR': {'name': 'Korean', 'code': 'KR'}
}

# Schemas for request/response validation and documentation
class VoiceSchema(Schema):
    id = fields.Str(required=True, description="Voice identifier")
    name = fields.Str(required=True, description="Voice display name")

class VoiceListResponseSchema(Schema):
    success = fields.Bool(required=True)
    timestamp = fields.DateTime(required=True)
    data = fields.Dict(keys=fields.Str(), values=fields.List(fields.Nested(VoiceSchema)))

class SynthesisRequestSchema(Schema):
    text = fields.Str(required=True, description="Text to synthesize")
    voice = fields.Str(required=False, default="EN", description="Voice ID to use")
    speed = fields.Float(required=False, default=1.0, description="Speech speed multiplier")

class ErrorResponseSchema(Schema):
    success = fields.Bool(required=True)
    timestamp = fields.DateTime(required=True)
    error = fields.Str(required=True)

# Current TTS instance
current_tts = None
current_voice = None

def get_tts(voice_id):
    """Get or create TTS instance for the specified voice"""
    global current_tts, current_voice
    
    if voice_id != current_voice:
        logger.info(f"Initializing new TTS model for voice: {voice_id}")
        os.environ["MECAB_SKIP"] = "1"  # Skip MeCab initialization
        
        voice_info = AVAILABLE_VOICES.get(voice_id)
        if not voice_info:
            raise ValueError(f"Invalid voice ID: {voice_id}")
            
        current_tts = TTS(language=voice_info['code'])
        current_voice = voice_id
        
    return current_tts

def api_response(success, data=None, error=None, status_code=200):
    """Helper function to structure API responses"""
    response = {
        'success': success,
        'timestamp': datetime.datetime.utcnow().isoformat(),
    }
    if data is not None:
        response['data'] = data
    if error is not None:
        response['error'] = error
    return jsonify(response), status_code

# Frontend routes
@app.route('/')
def root():
    """Serve the index.html file"""
    return app.send_static_file('index.html')

# API v1 routes
@app.route('/api/v1/voices', methods=['GET'])
@auth.login_required
@limiter.limit("30/minute")
@doc(description='Get list of available voices', tags=['voices'])
@marshal_with(VoiceListResponseSchema)
def api_list_voices():
    """API endpoint to list available voices"""
    try:
        voices = [
            {'id': k, 'name': v['name']} 
            for k, v in AVAILABLE_VOICES.items()
        ]
        return api_response(True, {'voices': voices})
    except Exception as e:
        logger.error(f"Error in list_voices: {str(e)}", exc_info=True)
        return api_response(False, error=str(e), status_code=500)

@app.route('/api/v1/synthesize', methods=['POST'])
@auth.login_required
@limiter.limit("20/minute")
@doc(description='Convert text to speech', tags=['synthesis'])
@use_kwargs(SynthesisRequestSchema)
def api_synthesize(**kwargs):
    """API endpoint for text-to-speech synthesis"""
    try:
        text = kwargs.get('text')
        speed = float(kwargs.get('speed', 1.0))
        voice_id = kwargs.get('voice', 'EN')

        logger.info(f"API synthesis request - Text: {text}, Speed: {speed}, Voice: {voice_id}")

        temp_file = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
        temp_path = temp_file.name
        temp_file.close()

        try:
            tts = get_tts(voice_id)
            tts.tts_to_file(
                text=text,
                speaker_id=0,
                output_path=temp_path,
                speed=speed
            )
            
            if not os.path.exists(temp_path) or os.path.getsize(temp_path) == 0:
                raise Exception("Failed to generate audio file")
                
            response = send_file(
                temp_path,
                mimetype='audio/wav',
                as_attachment=True,
                download_name='speech.wav'
            )
            response.headers['Content-Length'] = os.path.getsize(temp_path)
            return response

        finally:
            if os.path.exists(temp_path):
                try:
                    os.unlink(temp_path)
                except Exception as e:
                    logger.error(f"Error cleaning up temp file: {str(e)}", exc_info=True)

    except Exception as e:
        logger.error(f"Error in synthesis: {str(e)}", exc_info=True)
        return api_response(False, error=str(e), status_code=500)

# Legacy routes for frontend compatibility
@app.route('/voices', methods=['GET'])
def list_voices():
    """Legacy endpoint for frontend"""
    try:
        voices = [
            {'id': k, 'name': v['name']} 
            for k, v in AVAILABLE_VOICES.items()
        ]
        return jsonify({'voices': voices})
    except Exception as e:
        logger.error(f"Error in list_voices: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@app.route('/synthesize', methods=['POST'])
def synthesize():
    """Legacy endpoint for frontend"""
    try:
        data = request.json
        if not data or 'text' not in data:
            return jsonify({'error': 'No text provided'}), 400

        text = data['text']
        speed = float(data.get('speed', 1.0))
        voice_id = data.get('voice', 'EN')
        
        logger.info(f"Frontend synthesis request - Text: {text}, Speed: {speed}, Voice: {voice_id}")

        temp_file = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
        temp_path = temp_file.name
        temp_file.close()

        try:
            tts = get_tts(voice_id)
            tts.tts_to_file(
                text=text,
                speaker_id=0,
                output_path=temp_path,
                speed=speed
            )
            
            if not os.path.exists(temp_path) or os.path.getsize(temp_path) == 0:
                raise Exception("Failed to generate audio file")
                
            response = send_file(
                temp_path,
                mimetype='audio/wav',
                as_attachment=True,
                download_name='speech.wav'
            )
            response.headers['Content-Length'] = os.path.getsize(temp_path)
            return response

        finally:
            if os.path.exists(temp_path):
                try:
                    os.unlink(temp_path)
                except Exception as e:
                    logger.error(f"Error cleaning up temp file: {str(e)}", exc_info=True)

    except Exception as e:
        logger.error(f"Error in synthesis: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500

# Register API documentation
docs.register(api_list_voices)
docs.register(api_synthesize)

if __name__ == '__main__':
    logger.info("Starting MeloTTS API server...")
    try:
        app.run(host='0.0.0.0', port=5050, debug=True)
    except Exception as e:
        logger.error(f"Error starting server: {str(e)}", exc_info=True)
        sys.exit(1)
