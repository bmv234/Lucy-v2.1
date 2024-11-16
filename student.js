document.addEventListener('DOMContentLoaded', () => {
    // UI Elements
    const incomingText = document.getElementById('incomingText');
    const playButton = document.getElementById('playButton');
    const volumeControl = document.getElementById('volumeControl');
    const speedControl = document.getElementById('speedControl');
    const voiceSelect = document.getElementById('voiceSelect');
    const darkModeToggle = document.getElementById('darkModeToggle');
    const highlightedText = document.getElementById('highlightedText');

    // Audio state
    let isPlaying = false;
    let currentAudio = null;

    // MeloTTS API configuration
    const API_URL = 'http://localhost:5050/api/v1/synthesize';
    const API_KEY = 'test_key';

    // BroadcastChannel for receiving translations
    const broadcastChannel = new BroadcastChannel('lucy-v4-channel');
    broadcastChannel.onmessage = (event) => {
        if (event.data.type === 'translation') {
            const newText = event.data.text;
            incomingText.innerHTML += newText + '<br><br>';
            createWordSpans(event.data.text);
            incomingText.scrollTop = incomingText.scrollHeight;
        }
    };

    // Dark mode toggle
    darkModeToggle.addEventListener('click', () => {
        document.body.classList.toggle('dark-mode');
        darkModeToggle.querySelector('.toggle-icon').textContent = 
            document.body.classList.contains('dark-mode') ? '☀️' : '🌙';
        localStorage.setItem('darkMode', document.body.classList.contains('dark-mode'));
    });

    // Function to create word spans for highlighting
    function createWordSpans(text) {
        highlightedText.innerHTML = text.split(' ').map(word => 
            `<span class="word">${word}</span>`
        ).join(' ');
    }

    // Function to stop current playback
    function stopPlayback() {
        if (currentAudio) {
            currentAudio.pause();
            URL.revokeObjectURL(currentAudio.src); // Clean up the blob URL
            currentAudio = null;
        }
        isPlaying = false;
        playButton.querySelector('.btn-icon').textContent = '▶';
        
        // Remove all highlights
        const words = Array.from(highlightedText.getElementsByClassName('word'));
        words.forEach(word => word.classList.remove('highlighted'));
    }

    // Play button click handler
    playButton.addEventListener('click', async () => {
        if (isPlaying) {
            stopPlayback();
            return;
        }

        const text = highlightedText.textContent.trim();
        if (!text) {
            console.log('No text to speak');
            return;
        }

        isPlaying = true;
        playButton.querySelector('.btn-icon').textContent = '⏹';
        
        try {
            console.log('Making TTS request for text:', text);
            const response = await fetch(API_URL, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${API_KEY}`,
                    'Content-Type': 'application/json',
                    'Accept': 'audio/wav'
                },
                body: JSON.stringify({
                    text: text,
                    voice: voiceSelect.value,
                    speed: parseFloat(speedControl.value)
                })
            });

            console.log('Response status:', response.status);
            console.log('Response headers:', Object.fromEntries(response.headers.entries()));

            if (!response.ok) {
                let errorMessage;
                try {
                    const errorData = await response.json();
                    errorMessage = errorData.error;
                } catch {
                    errorMessage = `Server returned ${response.status}`;
                }
                throw new Error(errorMessage);
            }

            const audioBlob = await response.blob();
            console.log('Received audio blob:', audioBlob);

            if (audioBlob.size === 0) {
                throw new Error('Received empty audio data');
            }

            // Create a new audio element
            currentAudio = new Audio();
            
            // Set up event listeners before setting the source
            currentAudio.addEventListener('error', (e) => {
                console.error('Audio error:', e);
                stopPlayback();
                alert('Error playing audio');
            });

            currentAudio.addEventListener('ended', () => {
                console.log('Audio playback ended');
                stopPlayback();
            });

            // Create blob URL and set as audio source
            const audioUrl = URL.createObjectURL(audioBlob);
            currentAudio.src = audioUrl;
            
            // Set volume and start playback
            currentAudio.volume = parseFloat(volumeControl.value);
            await currentAudio.play();
            
            // Word highlighting
            const words = Array.from(highlightedText.getElementsByClassName('word'));
            if (words.length > 0) {
                const timePerWord = (currentAudio.duration * 1000) / words.length;
                let currentWordIndex = 0;
                
                const highlightInterval = setInterval(() => {
                    if (!isPlaying || currentWordIndex >= words.length) {
                        clearInterval(highlightInterval);
                        return;
                    }

                    // Remove previous highlight
                    if (currentWordIndex > 0) {
                        words[currentWordIndex - 1].classList.remove('highlighted');
                    }
                    
                    // Add new highlight
                    words[currentWordIndex].classList.add('highlighted');
                    currentWordIndex++;
                }, timePerWord);

                currentAudio.addEventListener('ended', () => {
                    clearInterval(highlightInterval);
                });
            }

        } catch (error) {
            console.error('Error:', error);
            stopPlayback();
            alert(`Error synthesizing speech: ${error.message}`);
        }
    });

    // Volume control
    volumeControl.addEventListener('input', (e) => {
        const volume = parseFloat(e.target.value);
        if (currentAudio) {
            currentAudio.volume = volume;
        }
    });

    // Speed control
    speedControl.addEventListener('input', (e) => {
        const speed = parseFloat(e.target.value);
        if (currentAudio) {
            currentAudio.playbackRate = speed;
        }
    });

    // Auto-scroll when new content is added
    const observer = new MutationObserver((mutations) => {
        mutations.forEach((mutation) => {
            if (mutation.type === 'childList') {
                incomingText.scrollTop = incomingText.scrollHeight;
            }
        });
    });

    observer.observe(incomingText, {
        childList: true,
        subtree: true
    });
});
