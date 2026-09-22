import os
import requests
import json
import re

from backend import weather


def detect_intent_and_context(message, location_data):
    msg_lower = message.lower()
    context_str = ""

    # ---------------------------------------------------------
    # LOCATION CONTEXT
    # ---------------------------------------------------------
    if location_data:
        city = location_data.get("city") or location_data.get("location")
        state = location_data.get("state")

        if city or state:
            loc_str = ", ".join(filter(None, [city, state]))
            context_str += f"User's current location: {loc_str}\n"

    # ---------------------------------------------------------
    # WEATHER KEYWORDS
    # ---------------------------------------------------------
    weather_keywords = [
        "weather",
        "rain",
        "temperature",
        "humidity",
        "baarish",
        "mausam",
        "paus",
        "havaamaan",
        "irrigate",
        "irrigation",
        "water",
        "wind",
        "rainfall",
        "paani"
    ]

    needs_weather = any(
        keyword in msg_lower
        for keyword in weather_keywords
    )

    # ---------------------------------------------------------
    # FETCH LIVE WEATHER
    # ---------------------------------------------------------
    if needs_weather and location_data and "city" in location_data:

        city = location_data["city"]

        try:
            loc, cur, df_daily, rec, err = (
                weather.fetch_weather_and_recommendations(city)
            )

            if not err and loc and cur:

                context_str += (
                    f"Live Weather Data for {loc.get('city')}:\n"
                )

                context_str += (
                    f"Temperature: {cur.get('temp')}°C, "
                    f"Humidity: {cur.get('hum')}%, "
                    f"Wind: {cur.get('wind')} km/h\n"
                )

                if rec:
                    context_str += (
                        f"Recommendation: "
                        f"{rec.get('title')} - "
                        f"{rec.get('msg')}\n"
                    )

                if df_daily is not None and not df_daily.empty:
                    rain_prob = df_daily.iloc[0][
                        "Rain Probability (%)"
                    ]

                    context_str += (
                        f"Today's Rain Probability: "
                        f"{rain_prob}%\n"
                    )

            else:
                print(
                    f"Weather API returned error: {err}",
                    flush=True
                )

        except Exception as e:
            print(
                "=" * 70,
                flush=True
            )
            print(
                "WEATHER ERROR INSIDE CHATBOT",
                flush=True
            )
            print(
                "ERROR TYPE:",
                type(e).__name__,
                flush=True
            )
            print(
                "ERROR:",
                str(e),
                flush=True
            )
            print(
                "=" * 70,
                flush=True
            )

    return context_str


# =============================================================
# MAIN CHATBOT FUNCTION
# =============================================================

def get_chatbot_response(
    message,
    language,
    location_data=None,
    image_context=None
):

    # ---------------------------------------------------------
    # REAL-TIME CONTEXT
    # ---------------------------------------------------------

    realtime_context = ""

    if location_data and isinstance(location_data, dict):
        realtime_context = detect_intent_and_context(
            message,
            location_data
        )
    else:
        realtime_context = detect_intent_and_context(
            message,
            {}
        )

    # ---------------------------------------------------------
    # IMAGE CONTEXT
    # ---------------------------------------------------------

    if image_context:
        realtime_context += (
            "\nUser uploaded an image. "
            f"Disease detection result: {image_context}\n"
        )

    # ---------------------------------------------------------
    # SYSTEM PROMPT
    # ---------------------------------------------------------

    system_prompt = (
        "You are AgriSense AI, an agricultural assistant. "
        "Provide practical, clear, and responsible farming guidance.\n"

        "Use available real-time weather and market data when relevant. "
        "Do not invent live weather, market prices, disease predictions, "
        "or API data.\n"

        f"The user wants you to respond in this language: "
        f"'{language}'. "

        "If the user's message is in a different language, "
        "respond in the language they used.\n"

        "CRITICAL: You MUST start your response with the exact "
        "language name you are responding in, enclosed in brackets "
        "on the very first line.\n"

        "Examples:\n"
        "[English]\n"
        "Your response here...\n\n"

        "[Hindi]\n"
        "Your response here...\n\n"

        "Choose ONLY from:\n"
        "English, Hindi, Marathi, Bengali, Telugu, Tamil, "
        "Gujarati, Kannada, Malayalam, Punjabi, Odia.\n"

        "If the user types in Romanized Hindi/Hinglish, "
        "output [Hindi].\n"

        "NEVER forget the bracketed language tag."
    )

    # ---------------------------------------------------------
    # ADD REAL-TIME CONTEXT
    # ---------------------------------------------------------

    if realtime_context:

        system_prompt += (
            "\n\nREAL-TIME CONTEXT:\n"
            "Use this information to answer the user.\n"
            "Do NOT invent data outside this context if the user "
            "asks for live information.\n\n"
            f"{realtime_context}\n"
        )

    # ---------------------------------------------------------
    # API KEY
    # ---------------------------------------------------------

    api_key = os.environ.get("GEMINI_API_KEY")

    if not api_key:

        print(
            "=" * 70,
            flush=True
        )

        print(
            "GEMINI API KEY ERROR",
            flush=True
        )

        print(
            "GEMINI_API_KEY is NOT configured.",
            flush=True
        )

        print(
            "=" * 70,
            flush=True
        )

        return (
            "System error: Gemini API key is missing.",
            language
        )

    # ---------------------------------------------------------
    # GEMINI API
    # ---------------------------------------------------------

    try:

        from google import genai

        print(
            "=" * 70,
            flush=True
        )

        print(
            "INITIALIZING GEMINI CLIENT...",
            flush=True
        )

        client = genai.Client(
            api_key=api_key
        )

        print(
            "GEMINI CLIENT INITIALIZED",
            flush=True
        )

        print(
            "MODEL: gemini-3.5-flash-lite",
            flush=True
        )

        print(
            "USER MESSAGE:",
            message,
            flush=True
        )

        # -----------------------------------------------------
        # GENERATE RESPONSE
        # -----------------------------------------------------

        response = client.models.generate_content(

            model="gemini-3.5-flash-lite",

            contents=message,

            config=genai.types.GenerateContentConfig(

                system_instruction=system_prompt,

                temperature=0.3,

                max_output_tokens=1500
            )
        )

        print(
            "GEMINI RESPONSE RECEIVED",
            flush=True
        )

        # -----------------------------------------------------
        # CHECK RESPONSE
        # -----------------------------------------------------

        if not response:

            print(
                "Gemini returned None response.",
                flush=True
            )

            return (
                "I'm sorry, I couldn't generate a response "
                "for that.",
                language
            )

        if not response.candidates:

            print(
                "Gemini returned no candidates.",
                flush=True
            )

            return (
                "I'm sorry, I couldn't generate a response "
                "for that.",
                language
            )

        candidate = response.candidates[0]

        print(
            "FINISH REASON:",
            getattr(
                candidate,
                "finish_reason",
                "Unknown"
            ),
            flush=True
        )

        # -----------------------------------------------------
        # CHECK CONTENT
        # -----------------------------------------------------

        if not candidate.content:

            print(
                "Gemini candidate has no content.",
                flush=True
            )

            return (
                "I'm sorry, I couldn't generate a response "
                "for that.",
                language
            )

        if not candidate.content.parts:

            print(
                "Gemini candidate has no parts.",
                flush=True
            )

            return (
                "I'm sorry, I couldn't generate a response "
                "for that.",
                language
            )

        # -----------------------------------------------------
        # GET RESPONSE TEXT
        # -----------------------------------------------------

        response_text = response.text

        if not response_text:

            print(
                "Gemini response.text is empty.",
                flush=True
            )

            return (
                "I'm sorry, I couldn't generate a response "
                "for that.",
                language
            )

        response_text = response_text.strip()

        print(
            "RAW GEMINI RESPONSE:",
            response_text,
            flush=True
        )

        # -----------------------------------------------------
        # EXTRACT LANGUAGE TAG
        # -----------------------------------------------------

        match = re.search(
            r"\[([A-Za-z]+)\]\s*(.*)",
            response_text,
            re.DOTALL
        )

        if match:

            detected_lang = match.group(1)
            reply = match.group(2).strip()

        else:

            print(
                "WARNING: Gemini did not return language tag.",
                flush=True
            )

            detected_lang = language
            reply = response_text

        # -----------------------------------------------------
        # FINAL RESPONSE
        # -----------------------------------------------------

        print(
            "DETECTED LANGUAGE:",
            detected_lang,
            flush=True
        )

        print(
            "FINAL REPLY:",
            reply,
            flush=True
        )

        print(
            "=" * 70,
            flush=True
        )

        return reply, detected_lang

    # =========================================================
    # GEMINI ERROR HANDLING
    # =========================================================

    except Exception as e:

        error_msg = str(e)

        print(
            "=" * 70,
            flush=True
        )

        print(
            "GEMINI API ERROR",
            flush=True
        )

        print(
            "ERROR TYPE:",
            type(e).__name__,
            flush=True
        )

        print(
            "ERROR:",
            error_msg,
            flush=True
        )

        print(
            "=" * 70,
            flush=True
        )

        # -----------------------------------------------------
        # RATE LIMIT / QUOTA
        # -----------------------------------------------------

        if (
            "429" in error_msg
            or "Quota" in error_msg
            or "RESOURCE_EXHAUSTED" in error_msg
        ):

            return (
                "The AI service is temporarily rate-limited. "
                "Please wait a few seconds and try again.",
                language
            )

        # -----------------------------------------------------
        # API KEY ERROR
        # -----------------------------------------------------

        if (
            "API_KEY_INVALID" in error_msg
            or "API key not valid" in error_msg
            or "401" in error_msg
            or "403" in error_msg
        ):

            return (
                "The Gemini API key is invalid or not authorized. "
                "Please check the API key configuration.",
                language
            )

        # -----------------------------------------------------
        # MODEL ERROR
        # -----------------------------------------------------

        if (
            "NOT_FOUND" in error_msg
            or "not found" in error_msg
            or "404" in error_msg
        ):

            return (
                "The configured Gemini model is unavailable. "
                "Please check the model configuration.",
                language
            )

       
        return (
            f"Gemini Error: {error_msg}",
            language
        )
