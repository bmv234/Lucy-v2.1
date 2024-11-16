import os
os.environ["MECAB_SKIP"] = "1"  # Skip MeCab initialization

from melo.api import TTS

def test_tts():
    try:
        # Initialize TTS with English model
        tts = TTS(language='EN')  # Changed to uppercase
        # Test text to speech
        text = "Hello, this is a test of MeloTTS with modified dependencies."
        tts.tts_to_file(text, speaker_id=0, output_path="test_output.wav")
        print("Test successful - audio file generated as test_output.wav")
    except Exception as e:
        print(f"Test failed with error: {e}")

if __name__ == "__main__":
    test_tts()
