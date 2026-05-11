/**
 * Voice Module — Web Speech API for voice input
 * Supports English, Hindi, Punjabi
 */

const Voice = (() => {
    let recognition = null;
    let isListening = false;

    function init() {
        const voiceBtn = document.getElementById('voice-btn');
        const langSelect = document.getElementById('voice-lang');

        if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
            voiceBtn.style.display = 'none';
            langSelect.style.display = 'none';
            return;
        }

        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        recognition = new SpeechRecognition();
        recognition.continuous = false;
        recognition.interimResults = true;

        recognition.onresult = (event) => {
            let transcript = '';
            for (let i = event.resultIndex; i < event.results.length; i++) {
                transcript += event.results[i][0].transcript;
            }
            const input = document.getElementById('chat-input');
            input.value = transcript;
            input.dispatchEvent(new Event('input'));
        };

        recognition.onend = () => {
            isListening = false;
            voiceBtn.classList.remove('recording');
        };

        recognition.onerror = (event) => {
            isListening = false;
            voiceBtn.classList.remove('recording');
            if (event.error !== 'aborted') {
                showToast('Voice recognition error: ' + event.error);
            }
        };

        voiceBtn.addEventListener('click', toggleListening);
    }

    function toggleListening() {
        const voiceBtn = document.getElementById('voice-btn');
        const langSelect = document.getElementById('voice-lang');

        if (isListening) {
            recognition.stop();
            isListening = false;
            voiceBtn.classList.remove('recording');
        } else {
            recognition.lang = langSelect.value;
            recognition.start();
            isListening = true;
            voiceBtn.classList.add('recording');
        }
    }

    return { init };
})();
