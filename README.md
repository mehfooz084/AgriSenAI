# 🌱 AgriSense AI

AgriSense AI is an intelligent, all-in-one agricultural platform designed to assist farmers with crop disease detection, localized weather forecasting, real-time market prices, and AI-driven agricultural advice. 

The platform combines a modern, responsive web interface (built with Tailwind CSS) with a robust Python Flask backend, integrating machine learning and external APIs to deliver actionable insights to users.

---

## 🌟 Key Features

### 1. 🍃 Plant Disease Detection
- **AI-Powered Diagnostics:** Upload a photo of a plant leaf to instantly identify potential diseases.
- **MobileNetV2 Model:** Uses a custom-trained MobileNetV2 deep learning model trained on the PlantVillage dataset (9 species, 29 classes) achieving over 97% testing accuracy.
- **Supported Crops:** Apple, Bell Pepper, Cherry, Corn (Maize), Grape, Peach, Potato, Strawberry, Tomato.
- **Confidence Scoring:** Displays the AI's confidence level in its prediction and seamlessly links to the recommended treatment.

### 2. 💊 Treatment Recommendations
- Provides detailed, actionable treatment plans, including recommended pesticides and cultural practices based on the specific disease detected.

### 3. 🌦️ Smart Weather & Farming Recommendations
- **Auto-Location Detection:** Seamlessly detects the user's exact location using highly precise HTML5 Geolocation (GPS) with a fallback to frictionless IP-based detection (`ipapi.co`).
- **16-Day Forecast:** Fetches current conditions and a 16-day extended forecast using the Open-Meteo API.
- **Smart Spraying Logic:** Analyzes wind speed, temperature, and rain probability to advise farmers on whether it is safe to spray pesticides or if they should delay.
- **Data Visualization:** Interactive temperature and rain probability charts powered by `Chart.js`.

### 4. 📈 Real-Time Mandi Prices
- Retrieves live agricultural commodity prices across different states and markets in India using the official `data.gov.in` API.
- Helps farmers make informed decisions on where and when to sell their produce for the best margins.

### 5. 🤖 Multilingual AI Assistant (Chatbot)
- **Powered by Gemini:** Uses Google's state-of-the-art `Gemini 3.5 Flash Lite` model for fast, intelligent agricultural advice.
- **Context-Aware:** Automatically attaches the user's local weather and location data to the chat, allowing the AI to answer questions like *"What crop should I plant right now?"* based on their real-world conditions.
- **Image Analysis:** Users can upload photos of their crops directly into the chat and ask the AI specific questions about the image.
- **Auto-Language Detection:** The AI automatically detects if the user is typing in English, Hindi, Marathi, or Hinglish, and dynamically updates its response language to match the user.
- **Hands-Free Mode:** Features built-in Speech-to-Text (microphone) for voice input and Text-to-Speech (speaker) so the AI can read its advice out loud to the farmer in the field.

## LIVE DEMO - https://agri-sen-ai-gdhy-omega.vercel.app/
---

## 🛠️ Technology Stack

- **Frontend:** HTML5, Vanilla JavaScript, Tailwind CSS (via CDN), Chart.js
- **Backend:** Python, Flask, Flask-CORS
- **Machine Learning:** TensorFlow / Keras (MobileNetV2)
- **APIs Used:** 
  - Google Gemini API (`google-genai` SDK)
  - Open-Meteo API & Nominatim (Weather & Geocoding)
  - IPAPI (IP-based Location Fallback)
  - Data.gov.in (Mandi Prices)

---

## 🚀 Setup & Installation

### Prerequisites
- Python 3.8+
- A Google Gemini API Key

### Installation

1. **Clone the repository:**
   ```bash
   git clone <repo-url>
   cd AgriSenAI
   ```

2. **Install the required dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Environment Variables:**
   Create a `.env` file in the root directory and add your API keys:
   ```env
   GEMINI_API_KEY=your_gemini_api_key_here
   ```

## 📊 Dataset

The plant disease detection model was trained using the PlantVillage dataset.

Due to the large size of the dataset, it is not included directly in this repository.

### Dataset Source

The dataset used for the project is available on Kaggle:

🔗 [Plant Disease Detection Dataset – Kaggle](https://www.kaggle.com/code/abdulrahmankhaled1/plant-disease-detection/input)
