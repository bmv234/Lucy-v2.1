import asyncio
import websockets
import numpy as np
import torch
from transformers import WhisperProcessor, WhisperForConditionalGeneration
import argostranslate.package
import argostranslate.translate
import logging
import json
import itertools
import socket
import os
import pathlib
import ssl

# Set up logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# Initialize device
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
logging.info(f"Using device: {device}")

# Initialize Whisper model
model_id = "openai/whisper-medium"
processor = WhisperProcessor.from_pretrained(model_id)
model = WhisperForConditionalGeneration.from_pretrained(model_id).to(device)
logging.info("Whisper model initialized")

# Define supported languages
SUPPORTED_LANGUAGES = {
    'en': 'english', 'es': 'spanish', 'fr': 'french', 'de': 'german',
    'it': 'italian', 'pt': 'portuguese', 'ru': 'russian', 'zh': 'chinese',
    'ja': 'japanese', 'ar': 'arabic', 'hi': 'hindi', 'nl': 'dutch',
    'pl': 'polish', 'tr': 'turkish'
}

def check_and_install_language_packages():
    argostranslate.package.update_package_index()
    available_packages = argostranslate.package.get_available_packages()
    installed_packages = argostranslate.package.get_installed_packages()

    # Get all possible language pairs
    language_pairs = list(itertools.permutations(SUPPORTED_LANGUAGES.keys(), 2))

    for from_code, to_code in language_pairs:
        # Check if the package is already installed
        if not any(pkg.from_code == from_code and pkg.to_code == to_code for pkg in installed_packages):
            # Find the package in available packages
            package = next((pkg for pkg in available_packages if pkg.from_code == from_code and pkg.to_code == to_code), None)
            if package:
                logging.info(f"Installing language package: {from_code} to {to_code}")
                argostranslate.package.install_from_path(package.download())
            else:
                logging.warning(f"Language package not available: {from_code} to {to_code}")

    logging.info("Finished checking and installing language packages")

# Run the check and install function
check_and_install_language_packages()

# Function to get available language pairs
def get_available_language_pairs():
    installed_packages = argostranslate.package.get_installed_packages()
    language_pairs = {}
    for lang in SUPPORTED_LANGUAGES.keys():
        language_pairs[lang] = [
            package.to_code 
            for package in installed_packages 
            if package.from_code == lang and package.to_code in SUPPORTED_LANGUAGES
        ]
    return language_pairs

# Get available language pairs
LANGUAGE_PAIRS = get_available_language_pairs()

# Audio settings
SAMPLE_RATE = 16000

def preprocess_audio(audio):
    logging.debug(f"Preprocessing audio of shape: {audio.shape}")
    # Implement noise reduction and other preprocessing steps here
    return audio

def transcribe(audio, from_language):
    logging.debug(f"Transcribing audio of shape: {audio.shape} in language: {from_language}")
    input_features = processor(audio, sampling_rate=SAMPLE_RATE, return_tensors="pt").input_features.to(device)
    
    forced_decoder_ids = processor.get_decoder_prompt_ids(language=SUPPORTED_LANGUAGES[from_language], task="transcribe")
    generated_ids = model.generate(input_features, forced_decoder_ids=forced_decoder_ids)
    
    transcription = processor.batch_decode(generated_ids, skip_special_tokens=True)[0]
    logging.debug(f"Transcription result: {transcription}")
    return transcription

def translate(text, from_code, to_code):
    if from_code == to_code:
        return text  # No translation needed
    logging.debug(f"Translating text from {from_code} to {to_code}: {text}")
    try:
        translated = argostranslate.translate.translate(text, from_code, to_code)
        if translated is None or translated == text:
            raise ValueError(f"Translation failed or returned None for {from_code} to {to_code}")
        logging.debug(f"Translation result: {translated}")
        return translated
    except Exception as e:
        error_msg = f"Translation error ({from_code} to {to_code}): {str(e)}"
        logging.error(error_msg)
        return f"[{error_msg}]"

async def handle_client(websocket, path):
    client_id = id(websocket)
    logging.info(f"New client connected: {client_id}")
    
    try:
        # Send available language pairs to the client
        await websocket.send(json.dumps({
            "type": "language_pairs", 
            "data": LANGUAGE_PAIRS
        }))
        logging.info(f"Sent language pairs to client: {client_id}")

        async for message in websocket:
            if isinstance(message, bytes):
                try:
                    metadata, audio_data = message.split(b'\n', 1)
                    metadata = json.loads(metadata.decode())
                    logging.debug(f"Received metadata from client {client_id}: {metadata}")

                    audio = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0
                    logging.debug(f"Received audio data from client {client_id}, shape: {audio.shape}")
                    
                    processed_audio = preprocess_audio(audio)
                    transcription = transcribe(processed_audio, metadata["from_code"])
                    translation = translate(transcription, metadata["from_code"], metadata["to_code"])
                    
                    response = {
                        "type": "result",
                        "transcription": transcription,
                        "translation": translation
                    }
                    logging.debug(f"Sending response to client {client_id}: {response}")
                    await websocket.send(json.dumps(response))
                except Exception as e:
                    error_msg = f"Error processing audio: {str(e)}"
                    logging.error(f"Error for client {client_id}: {error_msg}", exc_info=True)
                    await websocket.send(json.dumps({
                        "type": "error",
                        "message": error_msg
                    }))
            else:
                logging.warning(f"Received non-binary message from client {client_id}: {message}")
    except websockets.exceptions.ConnectionClosed:
        logging.info(f"Client {client_id} disconnected")
    except Exception as e:
        logging.error(f"Error handling client {client_id}: {str(e)}", exc_info=True)

def get_allowed_origins():
    # Get the machine's IP address
    ip = socket.gethostbyname(socket.gethostname())
    
    # Create a list of allowed origins
    origins = []
    
    # Add localhost and IP variations
    for host in ['localhost', '127.0.0.1', ip, '10.30.11.51']:
        for port in ['5000', '3000', '8000', '8443']:
            # Add both HTTP and HTTPS
            origins.extend([
                f"http://{host}:{port}",
                f"https://{host}:{port}"
            ])
    
    # Allow null origin for local file access
    origins.append("null")
    
    return origins

async def main():
    try:
        # Set up SSL context with more permissive settings for development
        ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ssl_context.load_cert_chain('cert.pem', 'key.pem')
        ssl_context.check_hostname = False  # Disable hostname checking for development
        ssl_context.verify_mode = ssl.CERT_NONE  # Don't verify client certificates
        
        # Get the machine's IP address
        ip = socket.gethostbyname(socket.gethostname())
        
        # Create WebSocket server with SSL and origins check
        async with websockets.serve(
            handle_client,
            "0.0.0.0",  # Listen on all interfaces
            8443,
            ssl=ssl_context,
            origins=get_allowed_origins(),
            ping_interval=20,
            ping_timeout=20,
            max_size=None,  # No message size limit
            compression=None  # Disable compression for better compatibility
        ) as server:
            logging.info(f"WebSocket server started on wss://{ip}:8443")
            logging.info(f"Also accessible via wss://localhost:8443")
            logging.info(f"And accessible via wss://10.30.11.51:8443")
            logging.info(f"Allowed origins: {get_allowed_origins()}")
            await asyncio.Future()  # run forever
    except Exception as e:
        logging.error(f"Failed to start server: {e}", exc_info=True)
        raise

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Server stopped by user")
    except Exception as e:
        logging.error(f"Server error: {e}", exc_info=True)
