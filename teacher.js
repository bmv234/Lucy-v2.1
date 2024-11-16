// WebSocket connection
let socket;
const SERVER_URL = `wss://${window.location.hostname}:8443`;

// Audio context and processing nodes
let audioContext;
let microphone;

// Silero VAD
let myvad = null;
let vadInitialized = false;

// Language pairs
let languagePairs = {};

// UI elements
const startButton = document.getElementById('startButton');
const stopButton = document.getElementById('stopButton');
const clearButton = document.getElementById('clearButton');
const fromLanguage = document.getElementById('fromLanguage');
const toLanguage = document.getElementById('toLanguage');
const transcriptionText = document.getElementById('transcriptionText');
const translationText = document.getElementById('translationText');
const darkModeToggle = document.getElementById('darkModeToggle');

// Create status element
const statusDiv = document.createElement('div');
statusDiv.className = 'status-message';
document.querySelector('.recording-controls').appendChild(statusDiv);

// Language names
const languageNames = {
    'en': 'English',
    'es': 'Spanish',
    'fr': 'French',
    'de': 'German',
    'it': 'Italian',
    'pt': 'Portuguese',
    'ru': 'Russian',
    'zh': 'Chinese (Mandarin)',
    'ja': 'Japanese',
    'ar': 'Arabic',
    'hi': 'Hindi',
    'nl': 'Dutch',
    'pl': 'Polish',
    'tr': 'Turkish'
};

// Dark mode toggle
darkModeToggle.addEventListener('click', () => {
    document.body.classList.toggle('dark-mode');
    darkModeToggle.querySelector('.toggle-icon').textContent = 
        document.body.classList.contains('dark-mode') ? '☀️' : '🌙';
    localStorage.setItem('darkMode', document.body.classList.contains('dark-mode'));
});

// Initialize WebSocket connection
function initWebSocket() {
    console.log(`Attempting to connect to ${SERVER_URL}`);
    socket = new WebSocket(SERVER_URL);
    
    socket.onopen = () => {
        console.log('WebSocket connected successfully');
        showStatus('Connected to server', 'success');
        startButton.disabled = false;
    };

    socket.onclose = () => {
        console.log('WebSocket disconnected');
        showStatus('Disconnected from server. Reconnecting...', 'error');
        startButton.disabled = true;
        stopButton.disabled = true;
        setTimeout(initWebSocket, 5000);
    };

    socket.onerror = (error) => {
        console.error('WebSocket error:', error);
        showStatus('Error connecting to server', 'error');
    };

    socket.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            console.log('Received message:', data);
            if (data.type === 'language_pairs') {
                languagePairs = filterLanguagePairs(data.data);
                populateLanguageDropdowns();
            } else if (data.type === 'result') {
                displayResults(data);
                broadcastResults(data);
            } else if (data.type === 'error') {
                console.error('Server error:', data.message);
                showStatus(`Server error: ${data.message}`, 'error');
            }
        } catch (error) {
            console.error('Error processing message:', error);
            showStatus('Error processing server response', 'error');
        }
    };
}

// Initialize Silero VAD
async function initVAD() {
    if (vadInitialized) {
        console.log('VAD already initialized');
        return true;
    }

    try {
        console.log('Checking VAD dependencies...');
        if (typeof vad === 'undefined') {
            throw new Error('Silero VAD library not loaded');
        }

        // Create a temporary audio context to ensure worklet is loaded
        const tempContext = new (window.AudioContext || window.webkitAudioContext)();
        await tempContext.audioWorklet.addModule(window.WEBVAD_WORKER_PATH);
        tempContext.close();

        console.log('Creating VAD instance...');
        myvad = await vad.MicVAD.new({
            onSpeechStart: () => {
                console.log('VAD: Speech started');
                showStatus('Listening...', 'info');
            },
            onSpeechEnd: (audio) => {
                console.log('VAD: Speech ended');
                showStatus('Processing...', 'info');
                sendAudioToServer(audio);
            },
            onVADMisfire: () => {
                console.log('VAD: Misfire');
                showStatus('Ready', 'success');
            }
        });

        console.log('Silero VAD initialized successfully');
        vadInitialized = true;
        return true;
    } catch (error) {
        console.error('Error initializing VAD:', error);
        showStatus(`Error initializing voice detection: ${error.message}`, 'error');
        return false;
    }
}

// Send audio to server
function sendAudioToServer(audio) {
    if (!socket || socket.readyState !== WebSocket.OPEN) {
        console.error('WebSocket not connected');
        showStatus('Connection lost. Running in demo mode.', 'warning');
        return;
    }

    console.log('Converting audio data...');
    const audioData = new Int16Array(audio.map(x => Math.max(-32768, Math.min(32767, Math.round(x * 32767)))));
    console.log('Audio data converted, samples:', audioData.length);
    
    const metadata = {
        type: 'audio',
        from_code: fromLanguage.value,
        to_code: toLanguage.value
    };
    console.log('Sending metadata:', metadata);

    const blob = new Blob([
        JSON.stringify(metadata),
        '\n',
        audioData.buffer
    ]);

    try {
        socket.send(blob);
        console.log(`Sent ${audioData.length} samples to server`);
    } catch (error) {
        console.error('Error sending audio data:', error);
        showStatus('Error sending audio data', 'error');
    }
}

// Broadcast results to student page
const broadcastChannel = new BroadcastChannel('lucy-v4-channel');
function broadcastResults(data) {
    broadcastChannel.postMessage({
        type: 'translation',
        text: data.translation || data.transcription,
        fromLang: fromLanguage.value,
        toLang: toLanguage.value
    });
}

// Filter language pairs
function filterLanguagePairs(pairs) {
    const filteredPairs = {};
    for (const [fromLang, toLangs] of Object.entries(pairs)) {
        if (languageNames[fromLang]) {
            filteredPairs[fromLang] = toLangs.filter(lang => languageNames[lang]);
        }
    }
    return filteredPairs;
}

// Populate language dropdowns
function populateLanguageDropdowns() {
    fromLanguage.innerHTML = Object.keys(languagePairs)
        .filter(lang => languagePairs[lang].length > 0)
        .map(lang => `<option value="${lang}">${languageNames[lang]}</option>`)
        .join('');

    fromLanguage.value = languagePairs['en'] ? 'en' : fromLanguage.options[0].value;
    updateToLanguages();
    fromLanguage.addEventListener('change', updateToLanguages);
}

// Update 'To' languages based on selected 'From' language
function updateToLanguages() {
    const fromLang = fromLanguage.value;
    const toLanguages = languagePairs[fromLang] || [];

    toLanguage.innerHTML = toLanguages
        .map(lang => `<option value="${lang}">${languageNames[lang]}</option>`)
        .join('');

    if (toLanguages.length > 0) {
        // Set Spanish as default if available, otherwise use first available language
        if (toLanguages.includes('es')) {
            toLanguage.value = 'es';
        } else {
            toLanguage.value = toLanguages[0];
        }
    }
}

// Display results
function displayResults(data) {
    console.log('Displaying results:', data);
    if (data.transcription) {
        transcriptionText.value += `${data.transcription}\n\n`;
        transcriptionText.scrollTop = transcriptionText.scrollHeight;
    }
    if (data.translation) {
        translationText.value += `${data.translation}\n\n`;
        translationText.scrollTop = translationText.scrollHeight;
    }
    showStatus('Ready', 'success');
}

// Start listening
async function startListening() {
    console.log('Starting listening process...');
    
    try {
        // Initialize audio context if needed
        if (!audioContext) {
            audioContext = new (window.AudioContext || window.webkitAudioContext)();
            await audioContext.resume();
            console.log('Audio context initialized');
        }

        // Request microphone permission
        const stream = await navigator.mediaDevices.getUserMedia({ 
            audio: {
                echoCancellation: true,
                noiseSuppression: true,
                autoGainControl: true
            }
        });

        // Initialize VAD if needed
        if (!vadInitialized) {
            console.log('Initializing VAD...');
            const success = await initVAD();
            if (!success) {
                showStatus('Error initializing voice detection', 'error');
                return;
            }
        }

        // Start VAD
        console.log('Starting VAD...');
        await myvad.start();
        console.log('Started listening');
        startButton.disabled = true;
        stopButton.disabled = false;
        showStatus('Ready', 'success');
    } catch (error) {
        console.error('Error starting audio:', error);
        showStatus(`Error starting voice detection: ${error.message}`, 'error');
    }
}

// Stop listening
function stopListening() {
    if (myvad) {
        myvad.pause();
        console.log('Stopped listening');
        startButton.disabled = false;
        stopButton.disabled = true;
        showStatus('Stopped', 'info');
    }
}

// Clear results
function clearResults() {
    transcriptionText.value = '';
    translationText.value = '';
}

// Show status message
function showStatus(message, type = 'info') {
    console.log('Status:', message, '(', type, ')');
    statusDiv.textContent = message;
    statusDiv.className = `status-message ${type}`;
}

// Event listeners
startButton.addEventListener('click', startListening);
stopButton.addEventListener('click', stopListening);
clearButton.addEventListener('click', clearResults);

// Initialize
stopButton.disabled = true;
startButton.disabled = true;

// Initialize WebSocket and VAD
initWebSocket();

// Initialize VAD when the page loads
window.addEventListener('load', async () => {
    try {
        console.log('Initializing VAD on page load...');
        await initVAD();
    } catch (error) {
        console.error('Failed to initialize VAD:', error);
    }
});
