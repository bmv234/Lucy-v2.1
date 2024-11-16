document.addEventListener('DOMContentLoaded', () => {
    const textInput = document.getElementById('textInput');
    const playButton = document.getElementById('playButton');
    const volumeControl = document.getElementById('volumeControl');
    const speedControl = document.getElementById('speedControl');
    const voiceSelect = document.getElementById('voiceSelect');
    const darkModeToggle = document.getElementById('darkModeToggle');
    const highlightedText = document.getElementById('highlightedText');
    let isPlaying = false;
    let currentAudio = null;

    // API Configuration
    const API_URL = 'http://localhost:5050/api/v1';
    const API_KEY = 'test_key';
    const headers = {
        'Authorization': `Bearer ${API_KEY}`,
        'Content-Type': 'application/json'
    };

    // Load available voices from API
    async function loadVoices() {
        try {
            const response = await fetch(`${API_URL}/voices`, {
                headers: headers
            });

            if (!response.ok) {
                if (response.status === 401) {
                    console.error('Authentication failed. Please check your API key.');
                    return;
                }
                throw new Error('Failed to load voices');
            }

            const data = await response.json();
            if (data.success && data.data.voices) {
                const voiceSelect = document.getElementById('voiceSelect');
                voiceSelect.innerHTML = ''; // Clear existing options
                
                data.data.voices.forEach(voice => {
                    const option = document.createElement('option');
                    option.value = voice.id;
                    option.textContent = voice.name;
                    voiceSelect.appendChild(option);
                });
            }
        } catch (error) {
            console.error('Error loading voices:', error);
        }
    }

    // Load voices when page loads
    loadVoices();

    // Initialize dark mode state
    let isDarkMode = true; // Start with dark mode enabled

    // Dark mode toggle
    darkModeToggle.addEventListener('click', () => {
        isDarkMode = !isDarkMode;
        document.body.classList.toggle('dark-mode');
        darkModeToggle.querySelector('.toggle-icon').textContent = isDarkMode ? '☀️' : '🌙';
    });

    // Function to create word spans for highlighting
    function createWordSpans(text) {
        highlightedText.innerHTML = text.split(' ').map(word => 
            `<span class="word">${word}</span>`
        ).join(' ');
    }

    // Update highlighted text when input changes
    textInput.addEventListener('input', () => {
        createWordSpans(textInput.value);
    });

    // Function to stop current playback
    function stopPlayback() {
        if (currentAudio) {
            currentAudio.pause();
            currentAudio = null;
        }
        isPlaying = false;
        playButton.querySelector('.btn-icon').textContent = '▶';
        
        // Remove all highlights
        const words = Array.from(highlightedText.getElementsByClassName('word'));
        words.forEach(word => word.classList.remove('highlighted'));
    }

    // Function to show error message
    function showError(message) {
        const errorDiv = document.createElement('div');
        errorDiv.className = 'error-message';
        errorDiv.textContent = message;
        document.querySelector('.container').insertBefore(errorDiv, highlightedText);
        setTimeout(() => errorDiv.remove(), 5000); // Remove after 5 seconds
    }

    // Play button click handler
    playButton.addEventListener('click', async () => {
        if (isPlaying) {
            stopPlayback();
            return;
        }

        const text = textInput.value.trim();
        if (!text) return;

        isPlaying = true;
        playButton.querySelector('.btn-icon').textContent = '⏹';
        
        try {
            const response = await fetch(`${API_URL}/synthesize`, {
                method: 'POST',
                headers: headers,
                body: JSON.stringify({
                    text: text,
                    speed: parseFloat(speedControl.value),
                    voice: voiceSelect.value
                })
            });

            if (!response.ok) {
                if (response.status === 401) {
                    showError('Authentication failed. Please check your API key.');
                } else if (response.status === 429) {
                    showError('Rate limit exceeded. Please try again later.');
                } else {
                    showError('TTS request failed. Please try again.');
                }
                stopPlayback();
                return;
            }

            const audioBlob = await response.blob();
            const audioUrl = URL.createObjectURL(audioBlob);
            
            currentAudio = new Audio(audioUrl);
            currentAudio.volume = parseFloat(volumeControl.value);
            
            // Create word spans if they don't exist
            createWordSpans(text);
            const words = Array.from(highlightedText.getElementsByClassName('word'));
            
            currentAudio.addEventListener('loadedmetadata', () => {
                const timePerWord = (currentAudio.duration * 1000) / words.length;
                
                currentAudio.play();

                // Word highlighting
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

                currentAudio.onended = () => {
                    stopPlayback();
                    clearInterval(highlightInterval);
                };
            });

        } catch (error) {
            console.error('Error:', error);
            showError('An error occurred while processing your request.');
            stopPlayback();
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
});
