// chatbot.js

document.addEventListener("DOMContentLoaded", () => {
    const chatMessages = document.getElementById("chat-messages");
    const chatInput = document.getElementById("chat-input");
    const sendBtn = document.getElementById("send-btn");
    const suggestBtns = document.querySelectorAll(".suggest-btn");
    
    const languageSelect = document.getElementById("language-select");
    const locationBtn = document.getElementById("location-btn");
    
    const ctxLocation = document.getElementById("ctx-location");
    const ctxLanguage = document.getElementById("ctx-language");
    
    const uploadImgBtn = document.getElementById("upload-img-btn");
    const imageUpload = document.getElementById("image-upload");
    const imageContextBox = document.getElementById("image-context-box");
    const ctxImageResult = document.getElementById("ctx-image-result");
    const ctxImagePreview = document.getElementById("ctx-image-preview");

    const voiceBtn = document.getElementById("voice-btn");
    const speakerBtn = document.getElementById("speaker-btn");

    let currentLocation = null;
    let currentImageContext = null;
    let speechEnabled = false;

    // Speech Recognition Setup
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    let recognition = null;
    if (SpeechRecognition) {
        recognition = new SpeechRecognition();
        recognition.continuous = false;
        recognition.interimResults = false;
        
        recognition.onresult = (event) => {
            const transcript = event.results[0][0].transcript;
            chatInput.value = transcript;
            sendMessage(transcript);
        };
        
        recognition.onstart = () => {
            voiceBtn.classList.add("text-red-500", "bg-red-50", "animate-pulse");
        };
        
        recognition.onend = () => {
            voiceBtn.classList.remove("text-red-500", "bg-red-50", "animate-pulse");
        };
    } else {
        voiceBtn.style.display = 'none'; // Hide if not supported
    }

    // Text to Speech
    function speakText(text, langCode) {
        if (!speechEnabled || !window.speechSynthesis) return;
        
        // Strip HTML and asterisks for cleaner reading
        const cleanText = text.replace(/<[^>]*>?/gm, '').replace(/\*/g, '');
        const utterance = new SpeechSynthesisUtterance(cleanText);
        
        // Very basic language mapping
        if (langCode.includes("Hindi")) utterance.lang = 'hi-IN';
        else if (langCode.includes("Marathi")) utterance.lang = 'mr-IN';
        else utterance.lang = 'en-US';

        window.speechSynthesis.speak(utterance);
    }

    // --- Core Chat Functions ---

    function addMessage(text, sender) {
        const div = document.createElement("div");
        div.className = `chat-bubble ${sender === 'user' ? 'user-bubble' : 'bot-bubble'}`;
        div.innerHTML = formatMessage(text);
        chatMessages.appendChild(div);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    function formatMessage(text) {
        // Convert basic markdown-like syntax to HTML if needed
        let formatted = text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        formatted = formatted.replace(/\n/g, '<br>');
        return formatted;
    }

    function showTypingIndicator() {
        const div = document.createElement("div");
        div.className = "chat-bubble bot-bubble typing-indicator-container";
        div.id = "typing-indicator";
        div.innerHTML = `
            <div class="typing-indicator">
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
            </div>
        `;
        chatMessages.appendChild(div);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    function removeTypingIndicator() {
        const indicator = document.getElementById("typing-indicator");
        if (indicator) {
            indicator.remove();
        }
    }

    async function sendMessage(text) {
        if (!text.trim()) return;

        addMessage(text, 'user');
        chatInput.value = "";
        
        showTypingIndicator();
        sendBtn.disabled = true;

        try {
            const payload = {
                message: text,
                language: languageSelect.value,
                image_context: currentImageContext
            };

            if (currentLocation) {
                payload.latitude = currentLocation.lat;
                payload.longitude = currentLocation.lon;
                payload.location = currentLocation.city;
            }

            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            const data = await response.json();
            removeTypingIndicator();

            if (data.success) {
                addMessage(data.reply, 'bot');
                if (data.language && data.language !== "Auto Detect") {
                    ctxLanguage.textContent = data.language;
                    
                    // If the user is on Auto Detect, just update the Auto Detect option's text to show what was detected
                    // This ensures the next message is still Auto-Detected and can shift languages!
                    if (languageSelect.value === "Auto Detect") {
                        const autoOpt = Array.from(languageSelect.options).find(opt => opt.value === "Auto Detect");
                        if (autoOpt) {
                            autoOpt.text = `🌐 Auto Detect (${data.language})`;
                        }
                    }
                }
                speakText(data.reply, data.language);
            } else {
                addMessage("Sorry, I encountered an error. Please try again.", 'bot');
            }
        } catch (error) {
            console.error("Chat API Error:", error);
            removeTypingIndicator();
            addMessage("Network error. Please check your connection and try again.", 'bot');
        } finally {
            sendBtn.disabled = false;
            // Clear image context after sending so it's not repeatedly sent
            if (currentImageContext) {
                currentImageContext = null;
                imageContextBox.classList.add("hidden");
            }
        }
    }

    // --- Event Listeners ---

    sendBtn.addEventListener("click", () => sendMessage(chatInput.value));
    
    chatInput.addEventListener("keypress", (e) => {
        if (e.key === "Enter") sendMessage(chatInput.value);
    });

    suggestBtns.forEach(btn => {
        btn.addEventListener("click", () => sendMessage(btn.textContent));
    });

    languageSelect.addEventListener("change", () => {
        ctxLanguage.textContent = languageSelect.value;
    });

    // --- Location Handling ---
    
    locationBtn.addEventListener("click", () => {
        if (!navigator.geolocation) {
            alert("Geolocation is not supported by your browser.");
            return;
        }

        locationBtn.innerHTML = "⌛";
        locationBtn.disabled = true;

        navigator.geolocation.getCurrentPosition(
            async (position) => {
                const lat = position.coords.latitude;
                const lon = position.coords.longitude;
                
                // Reverse Geocoding using Open-Meteo
                try {
                    // Open-Meteo geocoding doesn't strictly reverse-geocode coords well natively without a workaround or another API.
                    // Instead, we will pass lat/lon to our python backend if needed, or we can use nominatim.
                    const response = await fetch(`https://nominatim.openstreetmap.org/reverse?format=json&lat=${lat}&lon=${lon}`);
                    const data = await response.json();
                    
                    const city = data.address.city || data.address.town || data.address.village || data.address.county || "Unknown Location";
                    
                    currentLocation = { lat, lon, city };
                    ctxLocation.textContent = city;
                    locationBtn.innerHTML = "📍";
                    locationBtn.disabled = false;
                } catch (e) {
                    currentLocation = { lat, lon, city: "Current Location" };
                    ctxLocation.textContent = `Lat: ${lat.toFixed(2)}, Lon: ${lon.toFixed(2)}`;
                    locationBtn.innerHTML = "📍";
                    locationBtn.disabled = false;
                }
            },
            (error) => {
                alert("Location access denied or unavailable. Please enter your city manually in the chat.");
                locationBtn.innerHTML = "📍";
                locationBtn.disabled = false;
            }
        );
    });

    // --- Image Upload Handling ---

    uploadImgBtn.addEventListener("click", () => {
        imageUpload.click();
    });

    imageUpload.addEventListener("change", async (e) => {
        const file = e.target.files[0];
        if (!file) return;

        // Show preview
        const reader = new FileReader();
        reader.onload = (e) => {
            ctxImagePreview.src = e.target.result;
            ctxImagePreview.classList.remove("hidden");
            imageContextBox.classList.remove("hidden");
            ctxImageResult.textContent = "Analyzing...";
        };
        reader.readAsDataURL(file);

        // Upload and Predict
        const formData = new FormData();
        formData.append("image", file);

        try {
            const response = await fetch('/api/predict', {
                method: 'POST',
                body: formData
            });
            const data = await response.json();

            if (data.error) {
                ctxImageResult.textContent = `Error: ${data.error}`;
                currentImageContext = null;
            } else {
                ctxImageResult.textContent = `${data.plant} - ${data.disease} (${data.confidence}%)`;
                currentImageContext = `Plant: ${data.plant}, Disease: ${data.disease}, Confidence: ${data.confidence}%`;
                
                // Automatically send a message
                sendMessage(`What should I do about ${data.plant} ${data.disease}?`);
            }
        } catch (error) {
            console.error(error);
            ctxImageResult.textContent = "Error communicating with detection server.";
        }
        
        imageUpload.value = ""; // Reset
    });

    // --- Voice Event Listeners ---
    voiceBtn.addEventListener("click", () => {
        if (recognition) {
            try {
                recognition.start();
            } catch (e) {
                recognition.stop();
            }
        }
    });

    speakerBtn.addEventListener("click", () => {
        speechEnabled = !speechEnabled;
        speakerBtn.dataset.active = speechEnabled;
        
        const svgOff = speakerBtn.querySelector(".speaker-off");
        const svgOn = speakerBtn.querySelector(".speaker-on");
        
        if (speechEnabled) {
            svgOff.classList.add("hidden");
            svgOn.classList.remove("hidden");
            speakerBtn.classList.add("text-emerald-600", "bg-emerald-50");
            speakerBtn.title = "Text-to-Speech (On)";
        } else {
            svgOff.classList.remove("hidden");
            svgOn.classList.add("hidden");
            speakerBtn.classList.remove("text-emerald-600", "bg-emerald-50");
            speakerBtn.title = "Text-to-Speech (Off)";
            window.speechSynthesis.cancel(); // Stop speaking if turned off
        }
    });

    // --- Auto Location Detection on Load ---
    async function autoDetectLocation() {
        if (navigator.geolocation) {
            navigator.geolocation.getCurrentPosition(
                async (position) => {
                    const lat = position.coords.latitude;
                    const lon = position.coords.longitude;
                    try {
                        const response = await fetch(`https://nominatim.openstreetmap.org/reverse?format=json&lat=${lat}&lon=${lon}`);
                        const data = await response.json();
                        const city = data.address.city || data.address.town || data.address.village || data.address.county || "Unknown Location";
                        currentLocation = { lat, lon, city };
                        ctxLocation.textContent = city;
                    } catch (e) {
                        fallbackIpLocation();
                    }
                },
                (error) => {
                    fallbackIpLocation();
                },
                { timeout: 5000 }
            );
        } else {
            fallbackIpLocation();
        }

        async function fallbackIpLocation() {
            try {
                const res = await fetch("https://ipapi.co/json/");
                if (res.ok) {
                    const data = await res.json();
                    if (data.city) {
                        currentLocation = { 
                            lat: data.latitude, 
                            lon: data.longitude, 
                            city: data.city,
                            state: data.region
                        };
                        ctxLocation.textContent = data.city;
                    }
                }
            } catch (err) {
                console.error("Auto-location failed:", err);
            }
        }
    }
    
    // Run auto-detect in the background when the chat loads
    autoDetectLocation();
});
