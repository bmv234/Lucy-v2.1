import multiprocessing
import subprocess
import sys
import os
import socket
import pathlib
import time
import requests
import logging
from urllib3.exceptions import InsecureRequestWarning

# Disable insecure request warnings for local development
requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def get_local_ip():
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)
    return local_ip

def run_flask_server():
    subprocess.run([sys.executable, 'app.py'])

def run_websocket_server():
    subprocess.run([sys.executable, 'server.py'])

def wait_for_server(url, server_name, timeout=30):
    """Wait for a server to be ready"""
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            response = requests.get(url, verify=False, timeout=1)
            if response.status_code == 200:
                logger.info(f"{server_name} is ready!")
                return True
        except requests.exceptions.RequestException:
            pass
        time.sleep(1)
        logger.info(f"Waiting for {server_name}...")
    return False

def check_ssl_certificates():
    current_dir = pathlib.Path(__file__).parent.absolute()
    cert_path = current_dir / 'cert.pem'
    key_path = current_dir / 'key.pem'
    
    if not (cert_path.exists() and key_path.exists()):
        print("\nGenerating SSL certificates...")
        os.system(f'openssl req -x509 -newkey rsa:2048 -keyout {key_path} -out {cert_path} -days 365 -nodes -subj "/CN=localhost"')
        print("SSL certificates generated successfully")

def main():
    # Check and generate SSL certificates if needed
    check_ssl_certificates()
    
    # Get the local IP
    local_ip = get_local_ip()
    
    # Print startup message
    print("\nLucy v4 - Starting Secure Services")
    print("================================")
    print("Secure Web Application:")
    print(f"Teacher's page: https://{local_ip}:5000")
    print(f"Student's page: https://{local_ip}:5000/student")
    print("\nSecure WebSocket Server:")
    print(f"wss://{local_ip}:8443")
    print("\nMeloTTS Server (External):")
    print("http://localhost:5050")
    print("\nLocal Access (Alternative):")
    print(f"Teacher's page: https://localhost:5000")
    print(f"Student's page: https://localhost:5000/student")
    print(f"WebSocket: wss://localhost:8443")
    print("\nImportant Notes:")
    print("1. All servers use self-signed certificates for secure connections")
    print("2. When first accessing the services, you'll need to:")
    print("   a. Accept the security warning for https://{local_ip}:5000")
    print("   b. Accept the security warning for wss://{local_ip}:8443")
    print("3. Firefox users may need to:")
    print("   a. Visit each HTTPS endpoint directly")
    print("   b. Add security exceptions")
    print("   c. Then return to the teacher's page")
    print("4. The system uses two servers:")
    print("   - Main web application (port 5000)")
    print("   - WebSocket server for real-time communication (port 8443)")
    print("5. Text-to-Speech is provided by external MeloTTS server on port 5050")
    print("================================\n")

    # Start servers
    flask_process = multiprocessing.Process(target=run_flask_server)
    websocket_process = multiprocessing.Process(target=run_websocket_server)

    try:
        # Start servers
        logger.info("Starting main application server...")
        flask_process.start()
        logger.info("Starting WebSocket server...")
        websocket_process.start()

        # Wait for main application to be ready
        if not wait_for_server('https://localhost:5000', 'Main application'):
            logger.error("Main application failed to start!")
            raise Exception("Main application failed to start")

        logger.info("All servers are running!")

        # Wait for all processes
        flask_process.join()
        websocket_process.join()

    except KeyboardInterrupt:
        print("\nShutting down servers...")
    except Exception as e:
        print(f"\nError: {str(e)}")
    finally:
        # Clean up processes
        for p in [flask_process, websocket_process]:
            if p.is_alive():
                p.terminate()
                p.join()
        print("Servers stopped")

if __name__ == '__main__':
    main()
