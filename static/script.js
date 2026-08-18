// Active session transcript storage for TXT export
let activeSessionChat = [];
let currentLanguage = localStorage.getItem('dak_selected_lang') || 'English';

const PLACEHOLDERS = {
    'English': 'Ask Dak Sahayak or enter Consignment No. (e.g. EU123456789IN)...',
    'Hindi': 'डाक सहायक से पूछें या कंसाइनमेंट नंबर दर्ज करें (उदा. EU123456789IN)...',
    'Kannada': 'ಡಾಕ್ ಸಹಾಯಕ್ ಅವರನ್ನು ಕೇಳಿ ಅಥವಾ ಕಾನ್ಸೈನ್‌ಮೆಂಟ್ ಸಂಖ್ಯೆಯನ್ನು ನಮೂದಿಸಿ...',
    'Tamil': 'தபால் உதவியாளரிடம் கேளுங்கள் அல்லது பதிவு எண்ணை உள்ளிடவும்...',
    'Telugu': 'డాక్ సహాయక్‌ని అడగండి లేదా కన్సైన్‌మెంట్ నంబర్‌ను నమోదు చేయండి...',
    'Marathi': 'डाक सहाय्यकला विचारा किंवा कन्साइनमेंट नंबर प्रविष्ट करा...',
    'Bengali': 'ডাক সহায়ককে জিজ্ঞাসা করুন বা কনসাইনমেন্ট নম্বর লিখুন...'
};

document.addEventListener('DOMContentLoaded', () => {
    console.log("Dak Sahayak AI App Initialized.");
    const langSelect = document.getElementById('languageSelect');
    if (langSelect) {
        langSelect.value = currentLanguage;
    }
    onLanguageChange(false);

    const chatForm = document.getElementById('chatForm');
    if (chatForm) {
        chatForm.addEventListener('submit', (e) => {
            e.preventDefault();
            handleSend(e);
        });
    }
});

function onLanguageChange(userInitiated = true) {
    const langSelect = document.getElementById('languageSelect');
    if (langSelect) {
        currentLanguage = langSelect.value;
        localStorage.setItem('dak_selected_lang', currentLanguage);
    }
    
    const input = document.getElementById('userInput') || document.getElementById('userMsg');
    if (input) {
        input.placeholder = PLACEHOLDERS[currentLanguage] || PLACEHOLDERS['English'];
    }
}

// Modal Management
function openModal(id) {
    const modal = document.getElementById(id);
    if (modal) {
        modal.classList.add('show');
    }
}

function closeModal(id) {
    const modal = document.getElementById(id);
    if (modal) {
        modal.classList.remove('show');
    }
}

// Lightweight Markdown Parser Helper
function parseMarkdown(text) {
    if (!text) return '';
    
    let lines = text.split('\n');
    let htmlLines = [];
    let inList = false;
    let listType = null;

    lines.forEach(line => {
        let trimmed = line.trim();

        // Check for Headers (###)
        if (/^#{1,6}\s+/.test(trimmed)) {
            if (inList) { htmlLines.push(`</${listType}>`); inList = false; }
            let level = trimmed.match(/^#+/)[0].length;
            let headerText = trimmed.replace(/^#+\s+/, '');
            headerText = formatInlineMarkdown(headerText);
            htmlLines.push(`<h${Math.min(level + 2, 6)} style="color:var(--dark-red); margin: 10px 0 4px 0; font-weight: 600;">${headerText}</h${Math.min(level + 2, 6)}>`);
            return;
        }

        // Check for Unordered Bullet Points (*, -, •)
        if (/^[\*\-\•]\s+/.test(trimmed)) {
            if (!inList || listType !== 'ul') {
                if (inList) htmlLines.push(`</${listType}>`);
                htmlLines.push('<ul style="margin-left: 20px; margin-bottom: 8px;">');
                inList = true;
                listType = 'ul';
            }
            let itemText = trimmed.replace(/^[\*\-\•]\s+/, '');
            itemText = formatInlineMarkdown(itemText);
            htmlLines.push(`<li style="margin-bottom: 4px; line-height: 1.5;">${itemText}</li>`);
            return;
        }

        // Check for Ordered Bullet Points (1., 2.)
        if (/^\d+\.\s+/.test(trimmed)) {
            if (!inList || listType !== 'ol') {
                if (inList) htmlLines.push(`</${listType}>`);
                htmlLines.push('<ol style="margin-left: 20px; margin-bottom: 8px;">');
                inList = true;
                listType = 'ol';
            }
            let itemText = trimmed.replace(/^\d+\.\s+/, '');
            itemText = formatInlineMarkdown(itemText);
            htmlLines.push(`<li style="margin-bottom: 4px; line-height: 1.5;">${itemText}</li>`);
            return;
        }

        // Close list if paragraph line encountered
        if (inList) {
            htmlLines.push(`</${listType}>`);
            inList = false;
        }

        if (trimmed.length > 0) {
            let paragraphText = formatInlineMarkdown(trimmed);
            htmlLines.push(`<p style="margin-bottom: 8px; line-height: 1.5;">${paragraphText}</p>`);
        }
    });

    if (inList) {
        htmlLines.push(`</${listType}>`);
    }

    return htmlLines.join('');
}

function formatInlineMarkdown(text) {
    if (!text) return '';
    // Format bold (**text**)
    text = text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    // Format italic (*text*)
    text = text.replace(/\*(.*?)\*/g, '<em>$1</em>');
    // Clean up residual prefixes
    text = text.replace(/^(Overview|Detail|Summary):\s*/i, '');
    return text;
}

// Quick Prompt Pill Handler
function sendPrompt(text) {
    sendQuickPrompt(text);
}

function sendQuickPrompt(text) {
    const input = document.getElementById('userInput') || document.getElementById('userMsg');
    if (input) {
        input.value = text;
        handleSend();
    }
}

let conversationHistory = [];
let currentUserPincode = "";
let currentUserLocationDetails = "";

async function detectUserLocation() {
    const btn = document.getElementById('detectLocationBtn');
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> <span>Locating...</span>';
    }

    if (!navigator.geolocation) {
        alert("Geolocation is not supported by your browser.");
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = '<i class="fa-solid fa-location-crosshairs"></i> <span>📍 My PIN</span>';
        }
        return;
    }

    navigator.geolocation.getCurrentPosition(
        async (position) => {
            const lat = position.coords.latitude;
            const lon = position.coords.longitude;

            try {
                const res = await fetch(`https://nominatim.openstreetmap.org/reverse?format=json&lat=${lat}&lon=${lon}`);
                const data = await res.json();
                const address = data.address || {};
                
                const pincode = address.postcode || "Unknown PIN";
                const suburb = address.suburb || address.neighbourhood || address.residential || address.village || "";
                const city = address.city || address.town || address.county || address.state_district || "";
                const state = address.state || "";

                currentUserPincode = pincode;
                currentUserLocationDetails = `${suburb ? suburb + ', ' : ''}${city}, ${state} (PIN: ${pincode})`;

                // Hide welcome card if visible
                const welcomeCard = document.getElementById('welcomeCard');
                if (welcomeCard) welcomeCard.style.display = 'none';

                const cardHtml = `📍 **Location Detected Successfully!**
* **PIN Code:** **${pincode}**
* **Area / Suburb:** ${suburb || 'N/A'}
* **City / District:** ${city || 'N/A'}
* **State:** ${state || 'N/A'}
* *Your location PIN (${pincode}) is now attached for all post office searches.*`;

                appendMessage('bot', cardHtml, [], null);

            } catch (err) {
                console.error("Geocoding Error:", err);
                alert("Failed to fetch location address. Please try again.");
            } finally {
                if (btn) {
                    btn.disabled = false;
                    btn.innerHTML = '<i class="fa-solid fa-location-crosshairs"></i> <span>📍 My PIN</span>';
                }
            }
        },
        (error) => {
            console.error("Geolocation Position Error:", error);
            alert("Unable to retrieve your location. Please check browser location permissions.");
            if (btn) {
                btn.disabled = false;
                btn.innerHTML = '<i class="fa-solid fa-location-crosshairs"></i> <span>📍 My PIN</span>';
            }
        },
        { timeout: 10000 }
    );
}

// Handle User Input Submission
async function handleSend(e) {
    if (e && e.preventDefault) e.preventDefault();
    const input = document.getElementById('userInput') || document.getElementById('userMsg');
    if (!input) return;
    const message = input.value.trim();

    if (!message) return;

    // Hide welcome card on first message
    const welcomeCard = document.getElementById('welcomeCard');
    if (welcomeCard) welcomeCard.style.display = 'none';

    // Append User Message
    appendMessage('user', message);
    activeSessionChat.push({ sender: 'USER', message: message, time: new Date().toLocaleTimeString() });
    conversationHistory.push({ role: 'user', content: message });
    
    input.value = '';
    const sendBtn = document.getElementById('sendBtn');
    if (sendBtn) {
        sendBtn.disabled = true;
        sendBtn.innerHTML = '<span>Thinking...</span> <i class="fa-solid fa-spinner fa-spin"></i>';
    }

    // Create bot loading placeholder
    const loadingMsgId = appendLoadingMessage();

    try {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message: message,
                language: currentLanguage,
                pincode: currentUserPincode,
                user_location: currentUserLocationDetails,
                history: conversationHistory.slice(-6)
            })
        });
        const data = await response.json();
        
        // Remove loading placeholder
        removeMessage(loadingMsgId);

        if (response.ok) {
            const rawText = data.reply || data.response || data.message;
            const replyText = (rawText && rawText.trim()) ? rawText.trim() : "* India Post offers multiple Small Savings Schemes including PPF, SSA (Sukanya Samriddhi), NSC, and Post Office Savings Account.";
            appendMessage('bot', replyText, data.sources || [], data.log_id);
            activeSessionChat.push({ sender: 'DAK SAHAYAK', message: replyText, time: new Date().toLocaleTimeString() });
            conversationHistory.push({ role: 'assistant', content: replyText });
        } else {
            appendMessage('bot', `⚠️ Error: ${data.error || 'Failed to process request.'}`);
        }
    } catch (err) {
        removeMessage(loadingMsgId);
        appendMessage('bot', '⚠️ Connection error. Please check if backend Flask server is running.');
        console.error("Chat API Error:", err);
    } finally {
        sendBtn.disabled = false;
        sendBtn.innerHTML = '<span>Send</span> <i class="fa-solid fa-paper-plane"></i>';
    }
}

const LANG_CODES = {
    'English': 'en-IN',
    'Hindi': 'hi-IN',
    'Kannada': 'kn-IN',
    'Tamil': 'ta-IN',
    'Telugu': 'te-IN',
    'Marathi': 'mr-IN',
    'Bengali': 'bn-IN'
};

let mediaRecorder = null;
let audioChunks = [];
let mediaStream = null;
let isRecordingVoice = false;
let recordingTimeout = null;

async function toggleVoiceInput() {
    const micBtn = document.getElementById('micBtn');
    const input = document.getElementById('userInput') || document.getElementById('userMsg');

    // If currently recording, stop recorder
    if (isRecordingVoice && mediaRecorder && mediaRecorder.state !== 'inactive') {
        if (recordingTimeout) clearTimeout(recordingTimeout);
        mediaRecorder.stop();
        return;
    }

    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        showToast("⚠️ Microphone recording is not supported in your browser.");
        return;
    }

    try {
        mediaStream = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true } });
        audioChunks = [];

        let mimeType = 'audio/webm';
        if (MediaRecorder.isTypeSupported('audio/webm;codecs=opus')) {
            mimeType = 'audio/webm;codecs=opus';
        } else if (MediaRecorder.isTypeSupported('audio/mp4')) {
            mimeType = 'audio/mp4';
        } else if (MediaRecorder.isTypeSupported('audio/wav')) {
            mimeType = 'audio/wav';
        }

        mediaRecorder = new MediaRecorder(mediaStream, { mimeType: mimeType });

        mediaRecorder.ondataavailable = (e) => {
            if (e.data && e.data.size > 0) {
                audioChunks.push(e.data);
            }
        };

        mediaRecorder.onstart = () => {
            isRecordingVoice = true;
            if (micBtn) {
                micBtn.classList.add('recording');
                micBtn.innerHTML = '<i class="fa-solid fa-square fa-fade"></i>';
                micBtn.title = "Click mic to stop and submit";
            }
            if (input) {
                input.value = '';
                input.placeholder = "Recording your voice... Click mic again to submit 🎙️";
            }

            // Auto-stop recording after 10 seconds if user doesn't click stop manually
            if (recordingTimeout) clearTimeout(recordingTimeout);
            recordingTimeout = setTimeout(() => {
                if (isRecordingVoice && mediaRecorder && mediaRecorder.state !== 'inactive') {
                    mediaRecorder.stop();
                }
            }, 10000);
        };

        mediaRecorder.onstop = async () => {
            if (recordingTimeout) clearTimeout(recordingTimeout);
            isRecordingVoice = false;
            if (micBtn) {
                micBtn.classList.remove('recording');
                micBtn.innerHTML = '<i class="fa-solid fa-microphone"></i>';
                micBtn.title = "Speak your question (Voice Input)";
            }

            // Stop all media tracks to release microphone
            if (mediaStream) {
                mediaStream.getTracks().forEach(track => track.stop());
                mediaStream = null;
            }

            if (audioChunks.length === 0) {
                if (input) input.placeholder = PLACEHOLDERS[currentLanguage] || PLACEHOLDERS['English'];
                return;
            }

            const audioBlob = new Blob(audioChunks, { type: mediaRecorder.mimeType || 'audio/webm' });
            if (input) {
                input.placeholder = "Transcribing audio... ⚡";
            }

            // Convert audioBlob to Base64
            const reader = new FileReader();
            reader.readAsDataURL(audioBlob);
            reader.onloadend = async () => {
                const base64Audio = reader.result;

                try {
                    const response = await fetch('/api/transcribe', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            audio: base64Audio,
                            mime_type: audioBlob.type || 'audio/webm',
                            language: currentLanguage
                        })
                    });

                    const data = await response.json();

                    if (response.ok && (data.transcript || (data.success && data.transcript))) {
                        const transcribedText = data.transcript;
                        if (input) {
                            input.value = transcribedText;
                            input.placeholder = PLACEHOLDERS[currentLanguage] || PLACEHOLDERS['English'];
                        }
                        // Execute handleSend() immediately
                        handleSend();
                    } else {
                        if (input) input.placeholder = PLACEHOLDERS[currentLanguage] || PLACEHOLDERS['English'];
                        showToast(`⚠️ Transcription failed: ${data.error || 'Please speak again.'}`);
                    }
                } catch (err) {
                    console.error("Transcription API Error:", err);
                    if (input) input.placeholder = PLACEHOLDERS[currentLanguage] || PLACEHOLDERS['English'];
                    showToast("⚠️ Network error while sending voice data.");
                }
            };
        };

        mediaRecorder.start();

    } catch (err) {
        console.error("Microphone Access Error:", err);
        isRecordingVoice = false;
        if (micBtn) {
            micBtn.classList.remove('recording');
            micBtn.innerHTML = '<i class="fa-solid fa-microphone"></i>';
        }
        if (input) input.placeholder = PLACEHOLDERS[currentLanguage] || PLACEHOLDERS['English'];
        showToast("⚠️ Microphone access failed. Please check microphone permissions in your browser & Windows Settings.");
    }
}

// Toast Notification Helper
function showToast(message) {
    let toast = document.getElementById('dakToast');
    if (!toast) {
        toast = document.createElement('div');
        toast.id = 'dakToast';
        toast.style.cssText = `
            position: fixed;
            bottom: 85px;
            left: 50%;
            transform: translateX(-50%);
            background: #323232;
            color: #FFFFFF;
            padding: 10px 20px;
            border-radius: 20px;
            font-size: 0.88rem;
            z-index: 10000;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            transition: opacity 0.3s ease;
        `;
        document.body.appendChild(toast);
    }
    toast.innerText = message;
    toast.style.opacity = '1';
    toast.style.display = 'block';

    setTimeout(() => {
        toast.style.opacity = '0';
        setTimeout(() => { toast.style.display = 'none'; }, 300);
    }, 4000);
}

// Text-To-Speech (TTS)
let activeSpeakBtn = null;

function toggleSpeakText(btnEl, msgId) {
    const msgElement = document.getElementById(msgId);
    if (!msgElement) return;

    if (!('speechSynthesis' in window)) {
        alert("Text-to-speech is not supported in your browser.");
        return;
    }

    // If currently speaking this button, stop it
    if (window.speechSynthesis.speaking && activeSpeakBtn === btnEl) {
        window.speechSynthesis.cancel();
        btnEl.classList.remove('speaking');
        btnEl.innerHTML = '<i class="fa-solid fa-volume-high"></i> <span>Read Aloud</span>';
        activeSpeakBtn = null;
        return;
    }

    // Stop any ongoing speech
    window.speechSynthesis.cancel();
    if (activeSpeakBtn) {
        activeSpeakBtn.classList.remove('speaking');
        activeSpeakBtn.innerHTML = '<i class="fa-solid fa-volume-high"></i> <span>Read Aloud</span>';
    }

    // Extract raw text content without HTML tags
    const textContent = msgElement.innerText || msgElement.textContent;
    const cleanText = textContent.replace(/Was this helpful\?.*$/i, '').replace(/Read Aloud.*$/i, '').trim();

    if (!cleanText) return;

    const utterance = new SpeechSynthesisUtterance(cleanText);
    utterance.lang = LANG_CODES[currentLanguage] || 'en-IN';
    utterance.rate = 1.0;

    utterance.onstart = () => {
        btnEl.classList.add('speaking');
        btnEl.innerHTML = '<i class="fa-solid fa-volume-xmark"></i> <span>Stop</span>';
        activeSpeakBtn = btnEl;
    };

    utterance.onend = () => {
        btnEl.classList.remove('speaking');
        btnEl.innerHTML = '<i class="fa-solid fa-volume-high"></i> <span>Read Aloud</span>';
        activeSpeakBtn = null;
    };

    utterance.onerror = () => {
        btnEl.classList.remove('speaking');
        btnEl.innerHTML = '<i class="fa-solid fa-volume-high"></i> <span>Read Aloud</span>';
        activeSpeakBtn = null;
    };

    window.speechSynthesis.speak(utterance);
}

// Append Chat Message to UI
function appendMessage(sender, text, sources = [], logId = null) {
    const chatThread = document.getElementById('chatThread');
    const msgWrapper = document.createElement('div');
    const msgId = 'msg-' + Date.now() + '-' + Math.floor(Math.random() * 10000);
    msgWrapper.id = msgId;
    msgWrapper.className = `message-wrapper ${sender}`;

    const avatar = document.createElement('div');
    avatar.className = 'avatar';
    avatar.innerHTML = sender === 'user' ? '<i class="fa-solid fa-user"></i>' : '<i class="fa-solid fa-robot"></i>';

    const bubble = document.createElement('div');
    bubble.className = 'message-bubble';

    // Text content container
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-text-content';
    contentDiv.innerHTML = parseMarkdown(text || "No response received");
    bubble.appendChild(contentDiv);

    // Append feedback and TTS actions for Bot responses
    if (sender === 'bot') {
        const actionsDiv = document.createElement('div');
        actionsDiv.className = 'feedback-actions';
        
        let actionsHtml = `
            <button class="speak-btn" onclick="toggleSpeakText(this, '${msgId}')" title="Read aloud" aria-label="Read answer aloud">
                <i class="fa-solid fa-volume-high"></i> <span>Read Aloud</span>
            </button>
        `;

        if (logId) {
            actionsHtml += `
                <span>|</span>
                <span>Was this helpful?</span>
                <button class="feedback-btn" id="pos-${logId}" onclick="submitFeedback(${logId}, 'positive')">
                    <i class="fa-solid fa-thumbs-up"></i> Yes
                </button>
                <button class="feedback-btn" id="neg-${logId}" onclick="submitFeedback(${logId}, 'negative')">
                    <i class="fa-solid fa-thumbs-down"></i> No
                </button>
            `;
        }

        actionsDiv.innerHTML = actionsHtml;
        bubble.appendChild(actionsDiv);
    }

    msgWrapper.appendChild(avatar);
    msgWrapper.appendChild(bubble);
    chatThread.appendChild(msgWrapper);

    // Scroll to bottom
    chatThread.scrollTop = chatThread.scrollHeight;
}

function appendLoadingMessage() {
    const id = 'msg-loading-' + Date.now();
    const chatThread = document.getElementById('chatThread');
    const msgWrapper = document.createElement('div');
    msgWrapper.className = 'message-wrapper bot';
    msgWrapper.id = id;

    const avatar = document.createElement('div');
    avatar.className = 'avatar';
    avatar.innerHTML = '<i class="fa-solid fa-robot"></i>';

    const bubble = document.createElement('div');
    bubble.className = 'message-bubble';
    bubble.innerHTML = `
        <div style="display: flex; align-items: center; gap: 8px; color: var(--text-muted); font-size: 0.9rem;">
            <span>Dak Sahayak is thinking</span>
            <div class="typing-indicator">
                <span class="typing-dot"></span>
                <span class="typing-dot"></span>
                <span class="typing-dot"></span>
            </div>
        </div>
    `;

    msgWrapper.appendChild(avatar);
    msgWrapper.appendChild(bubble);
    chatThread.appendChild(msgWrapper);
    chatThread.scrollTop = chatThread.scrollHeight;
    return id;
}

function removeMessage(id) {
    const el = document.getElementById(id);
    if (el) el.remove();
}

function clearChat() {
    conversationHistory = [];
    activeSessionChat = [];
    const chatThread = document.getElementById('chatThread');
    chatThread.innerHTML = `
        <div class="welcome-card" id="welcomeCard">
            <div class="welcome-icon">
                <i class="fa-solid fa-paper-plane"></i>
            </div>
            <h2>Namaste! Welcome to Dak Sahayak</h2>
            <p>Ask anything about India Post services, Speed Post tariffs, Post Office Savings Schemes (PPF, SSA, SCSS, KVP), or track consignments live.</p>
            <div class="prompt-pills">
                <button class="pill" onclick="sendPrompt('What are domestic Speed Post rates and delivery timelines?')">🚀 Speed Post Rates & Timelines</button>
                <button class="pill" onclick="sendPrompt('Track consignment EU123456789IN')">📦 Track Consignment EU123456789IN</button>
                <button class="pill" onclick="sendPrompt('Tell me about Sukanya Samriddhi Account (SSA) details and interest rate.')">👧 Sukanya Samriddhi Scheme</button>
                <button class="pill" onclick="sendPrompt('What are the features and tax benefits of Public Provident Fund (PPF)?')">💰 Public Provident Fund (PPF)</button>
            </div>
        </div>
    `;
}

// Feedback submission
async function submitFeedback(logId, type) {
    try {
        const resp = await fetch('/api/feedback', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ log_id: logId, feedback: type })
        });
        if (resp.ok) {
            const posBtn = document.getElementById(`pos-${logId}`);
            const negBtn = document.getElementById(`neg-${logId}`);
            if (posBtn) posBtn.classList.remove('active-pos');
            if (negBtn) negBtn.classList.remove('active-neg');

            if (type === 'positive' && posBtn) {
                posBtn.classList.add('active-pos');
            } else if (type === 'negative' && negBtn) {
                negBtn.classList.add('active-neg');
            }
        }
    } catch (e) {
        console.error("Feedback submission failed:", e);
    }
}

// Export Chat Transcript to .txt file
function exportTranscript() {
    if (activeSessionChat.length === 0) {
        alert("No active chat messages to export.");
        return;
    }

    let fileContent = "========================================================\n";
    fileContent += "DAK SAHAYAK (डाक सहायक) - INDIA POST CHAT TRANSCRIPT\n";
    fileContent += `Date: ${new Date().toLocaleString()}\n`;
    fileContent += "========================================================\n\n";

    activeSessionChat.forEach((item, index) => {
        fileContent += `[${item.time}] ${item.sender}:\n${item.message}\n\n`;
        fileContent += "--------------------------------------------------------\n";
    });

    const blob = new Blob([fileContent], { type: 'text/plain;charset=utf-8' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `Dak_Sahayak_Transcript_${Date.now()}.txt`;
    link.click();
}

// Tariff Calculator Functions
function syncWeight(val) {
    document.getElementById('calcWeightRange').value = val;
    document.getElementById('calcWeightNumber').value = val;
    document.getElementById('weightValDisplay').textContent = `${val} g`;
}

async function calculateTariff(e) {
    e.preventDefault();
    const weight = document.getElementById('calcWeightNumber').value;
    const distance = document.getElementById('calcDistance').value;

    try {
        const resp = await fetch('/api/calculator', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ weight: weight, distance: distance })
        });
        const data = await resp.json();

        if (resp.ok) {
            document.getElementById('resWeightSlab').textContent = data.weight_slab;
            document.getElementById('resDistSlab').textContent = data.distance_label;
            document.getElementById('resBaseRate').textContent = `₹${data.base_tariff.toFixed(2)}`;
            document.getElementById('resGst').textContent = `₹${data.gst_amount.toFixed(2)}`;
            document.getElementById('resTotal').textContent = `₹${data.total_payable.toFixed(2)}`;

            document.getElementById('calcResultBox').style.display = 'block';
        }
    } catch (err) {
        alert("Error calculating tariff. Check server logs.");
    }
}

// PIN Code Search
async function searchPincode(e) {
    e.preventDefault();
    const query = document.getElementById('pinInput').value.trim();
    if (!query) return;

    const container = document.getElementById('pinResultsContainer');
    container.innerHTML = '<p class="placeholder-text"><i class="fa-solid fa-spinner fa-spin text-red"></i> Searching India Post PIN Directory...</p>';

    try {
        const resp = await fetch(`/api/pincode/${encodeURIComponent(query)}`);
        const data = await resp.json();

        if (resp.ok && data.results && data.results.length > 0) {
            let gridHTML = '<div class="pin-card-grid">';
            data.results.forEach(office => {
                gridHTML += `
                    <div class="pin-card">
                        <h4><i class="fa-solid fa-building-columns"></i> ${office.Name}</h4>
                        <span class="pin-badge">PIN: ${office.Pincode}</span>
                        <div class="pin-detail"><strong>Type:</strong> ${office.BranchType}</div>
                        <div class="pin-detail"><strong>Delivery:</strong> ${office.DeliveryStatus}</div>
                        <div class="pin-detail"><strong>District:</strong> ${office.District}</div>
                        <div class="pin-detail"><strong>State:</strong> ${office.State}</div>
                    </div>
                `;
            });
            gridHTML += '</div>';
            container.innerHTML = gridHTML;
        } else {
            container.innerHTML = `<p class="placeholder-text">No post office results found for '${query}'.</p>`;
        }
    } catch (err) {
        container.innerHTML = '<p class="placeholder-text">Error fetching PIN details. Please try again.</p>';
    }
}

// Chat History Modal Loader
async function loadHistoryModal() {
    openModal('historyModal');
    const container = document.getElementById('historyListContainer');
    container.innerHTML = '<p class="placeholder-text"><i class="fa-solid fa-spinner fa-spin text-red"></i> Fetching log history...</p>';

    try {
        const resp = await fetch('/api/history');
        const data = await resp.json();

        if (resp.ok && data.history && data.history.length > 0) {
            let listHTML = '';
            data.history.forEach(item => {
                const feedbackBadge = item.feedback 
                    ? `<span class="source-tag"><i class="fa-solid fa-thumbs-${item.feedback === 'positive' ? 'up' : 'down'}"></i> ${item.feedback}</span>`
                    : '';
                listHTML += `
                    <div class="history-item">
                        <div class="hist-header">
                            <span><i class="fa-solid fa-tag"></i> ${item.matched_category || 'General'}</span>
                            <span>${item.timestamp} ${feedbackBadge}</span>
                        </div>
                        <div class="hist-query">Q: ${item.user_message}</div>
                        <div class="hist-response">${parseMarkdown(item.bot_response)}</div>
                    </div>
                `;
            });
            container.innerHTML = listHTML;
        } else {
            container.innerHTML = '<p class="placeholder-text">No query history logged yet.</p>';
        }
    } catch (err) {
        container.innerHTML = '<p class="placeholder-text">Failed to load history logs.</p>';
    }
}
