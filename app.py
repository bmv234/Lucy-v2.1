from flask import Flask, send_from_directory, request, send_file, jsonify
from flask_cors import CORS
import os
import subprocess
import tempfile
import ssl
import socket
import requests
import logging
from urllib3.exceptions import InsecureRequestWarning

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Disable insecure request warnings for local development
requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)

app = Flask(__name__, static_folder='.')
CORS(app)

@app.route('/')
def serve_teacher():
    """Serve the teacher's page"""
    return send_from_directory('.', 'index.html')

@app.route('/student')
def serve_student():
    """Serve the student's page"""
    return send_from_directory('.', 'student.html')

@app.route('/synthesize', methods=['POST'])
def synthesize():
    """Handle TTS synthesis requests"""
    try:
        if not request.is_json:
            logger.error("Request does not contain JSON data")
            return jsonify({"error": "Request must be JSON"}), 400

        request_data = request.get_json()
        logger.info(f"Received TTS request: {request_data}")

        # Forward the request to the TTS server
        session = requests.Session()
        session.verify = False  # Disable SSL verification for local development
        
        logger.info("Forwarding request to TTS server...")
        tts_response = session.post(
            'https://localhost:5050/synthesize',
            json=request_data,
            timeout=30  # Add timeout
        )
        
        if tts_response.status_code != 200:
            error_msg = f"TTS server error: {tts_response.text}"
            logger.error(error_msg)
            return jsonify({"error": error_msg}), 500
            
        # Create a temporary file to store the audio
        temp_file = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
        temp_path = temp_file.name
        temp_file.close()
        
        logger.info(f"Writing audio data to temporary file: {temp_path}")
        
        # Write the audio data to the temporary file
        with open(temp_path, 'wb') as f:
            f.write(tts_response.content)
        
        # Verify the file was created and has content
        if not os.path.exists(temp_path):
            raise Exception("Failed to create temporary audio file")
        
        file_size = os.path.getsize(temp_path)
        if file_size == 0:
            raise Exception("Generated audio file is empty")
        
        logger.info(f"Successfully created audio file of size: {file_size} bytes")
        
        try:
            # Send the file
            return send_file(
                temp_path,
                mimetype='audio/wav',
                as_attachment=True,
                download_name='speech.wav'
            )
        finally:
            # Clean up the temporary file
            try:
                os.unlink(temp_path)
                logger.info("Temporary file cleaned up")
            except Exception as e:
                logger.error(f"Error cleaning up temporary file: {str(e)}")
                
    except requests.exceptions.RequestException as e:
        error_msg = f"Error communicating with TTS server: {str(e)}"
        logger.error(error_msg)
        return jsonify({"error": error_msg}), 500
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return jsonify({"error": error_msg}), 500

@app.route('/<path:path>')
def serve_files(path):
    """Serve any other files (js, css)"""
    return send_from_directory('.', path)

if __name__ == '__main__':
    # Get the local IP address for network access
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)
    
    # SSL context
    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ssl_context.load_cert_chain('cert.pem', 'key.pem')
    
    print(f"\nLucy v4 Server Running!")
    print(f"======================")
    print(f"Local Access:")
    print(f"Teacher's page: https://localhost:5000")
    print(f"Student's page: https://localhost:5000/student")
    print(f"\nNetwork Access:")
    print(f"Teacher's page: https://{local_ip}:5000")
    print(f"Student's page: https://{local_ip}:5000/student")
    print(f"======================\n")
    
    # Run the Flask server with SSL
    app.run(
        host='0.0.0.0',
        port=5000,
        ssl_context=ssl_context,
        debug=True
    )
