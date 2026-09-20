import os
import requests
import json

import weather

def detect_intent_and_context(message, location_data):
    msg_lower = message.lower()
    context_str = ""
    
    if location_data:
        city = location_data.get("city") or location_data.get("location")
        state = location_data.get("state")
        if city or state:
            loc_str = ", ".join(filter(None, [city, state]))
            context_str += f"User's current location: {loc_str}\n"
    
    weather_keywords = ["weather", "rain", "temperature", "humidity", "baarish", "mausam", "paus", "havaamaan", "irrigate", "water"]
    
    needs_weather = any(kw in msg_lower for kw in weather_keywords)
    
    # Check Weather
    if needs_weather and location_data and "city" in location_data:
        city = location_data["city"]
        try:
            loc, cur, df_daily, rec, err = weather.fetch_weather_and_recommendations(city)
            if not err:
                context_str += f"Live Weather Data for {loc.get('city')}:\n"
                context_str += f"Temperature: {cur.get('temp')}°C, Humidity: {cur.get('hum')}%, Wind: {cur.get('wind')} km/h\n"
                context_str += f"Recommendation: {rec.get('title')} - {rec.get('msg')}\n"
                if df_daily is not None and not df_daily.empty:
                    rain_prob = df_daily.iloc[0]["Rain Probability (%)"]
                    context_str += f"Today's Rain Probability: {rain_prob}%\n"
        except Exception as e:
            print(f"Weather fetch error in chatbot: {e}")
            
    return context_str

def get_chatbot_response(message, language, location_data=None, image_context=None):
    realtime_context = ""
    if location_data and isinstance(location_data, dict):
        realtime_context = detect_intent_and_context(message, location_data)
    else:
        realtime_context = detect_intent_and_context(message, {})
            
    if image_context:
        realtime_context += f"\nUser uploaded an image. Disease detection result: {image_context}\n"

    system_prompt = (
        "You are AgriSense AI, an agricultural assistant. Provide practical, clear, and responsible farming guidance.\n"
        "Use available real-time weather and market data when relevant. Do not invent live weather, market prices, disease predictions, or API data.\n"
        f"The user wants you to respond in this language: '{language}'. If the user's message is in a different language, respond in the language they used.\n"
        "CRITICAL: You MUST start your response with the exact language name you are responding in, enclosed in brackets on the very first line. "
        "For example: [English]\nYour response here... OR [Hindi]\nYour response here...\n"
        "Choose ONLY from: English, Hindi, Marathi, Bengali, Telugu, Tamil, Gujarati, Kannada, Malayalam, Punjabi, Odia. "
        "If the user types in Romanized Hindi/Hinglish, output [Hindi]. NEVER forget the bracketed language tag!"
    )
    
    if realtime_context:
        system_prompt += f"\nREAL-TIME CONTEXT (Use this to answer the user. Do NOT invent data outside of this if they ask for live info):\n{realtime_context}\n"

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY is not set.")
        return "System error: API key is missing. Please check your .env file and add GEMINI_API_KEY.", language

    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model='gemini-3.5-flash-lite',
            contents=message,
            config=genai.types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=0.3,
                max_output_tokens=1500
            )
        )
        
        if not response.candidates or not response.candidates[0].content.parts:
            print(f"Gemini API Error: Empty or blocked response. Finish reason: {response.candidates[0].finish_reason if response.candidates else 'Unknown'}", flush=True)
            return "I'm sorry, I couldn't generate a response for that. Please try rephrasing your question.", language
            
        response_text = response.text.strip()
        import re
        match = re.search(r'\[([A-Za-z]+)\]\s*(.*)', response_text, re.DOTALL)
        if match:
            detected_lang = match.group(1)
            reply = match.group(2).strip()
        else:
            detected_lang = language
            reply = response_text
            
        return reply, detected_lang
    except Exception as e:
        error_msg = str(e)
        print(f"Gemini API Error: {error_msg}", flush=True)
        if "429" in error_msg or "Quota" in error_msg:
            return "You are sending messages too quickly (API rate limit). Please wait a few seconds and try again.", language
        return "I am currently unable to process your request due to a server error. Please try again later.", language
