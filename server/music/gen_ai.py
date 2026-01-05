import os
import json
import logging
import google.generativeai as genai
from decouple import config

logger = logging.getLogger(__name__)

# --- Configure your Gemini API key ---
# Load from .env file using python-decouple (same as Django settings)
GOOGLE_API_KEY = config("GOOGLE_API_KEY", default=None)
if not GOOGLE_API_KEY:
    logger.warning("GOOGLE_API_KEY not set in environment variables or .env file")
    logger.warning("Fun facts will not be generated. Please add GOOGLE_API_KEY to your .env file in the server directory.")
else:
    logger.info("GOOGLE_API_KEY loaded successfully")

# --- Song class for structured input ---
class GenFunFact:
    def __init__(self, title: str, artist: str, url: str):
        self.title = title
        self.artist = artist
        self.url = url

def parse_json_from_text(text):
    # Removing newline characters and backticks
    clean_text = text.replace('\n', '').replace('`', '')

    # Extracting JSON part
    json_start_index = clean_text.find('{')
    json_string = clean_text[json_start_index:]

    # Parsing JSON
    data = json.loads(json_string)
    return data


def build_interaction_prompt(title, artist, url):
    return f"""
        You are a musical fun fact generator bot.

        Your job is to return a single JSON object with a concise, surprising, and delightful fun fact (under 255 characters) about a specific song.

        The fact must be:
        - Accurate or plausible
        - Relevant to fans of the artist
        - Based on the song’s title, artist, and Spotify link

        Respond ONLY in this JSON format:
        {{"fact": "your fun fact here"}}

        Here is the song metadata:
        - Title: {title}
        - Artist: {artist}
        - Spotify URL: {url}

        Now generate the fun fact.
    """

# --- Main function to generate fun fact ---
def generate_fun_fact(song: GenFunFact):
    """
    Generate a fun fact about a song using Google's Gemini API.
    Returns a dict with 'fact' key, or raises an exception if generation fails.
    """
    if not GOOGLE_API_KEY:
        logger.warning("GOOGLE_API_KEY not set, cannot generate fun fact")
        raise ValueError("Google API key not configured")
    
    try:
        genai.configure(api_key=GOOGLE_API_KEY)
        prompt = build_interaction_prompt(song.title, song.artist, song.url)
        
        # Try the model name - if it fails, try alternative names
        model_name = "gemini-2.5-flash-lite"
        try:
            model = genai.GenerativeModel(model_name)
        except Exception as model_error:
            logger.warning(f"Model '{model_name}' failed, trying 'gemini-1.5-flash': {str(model_error)}")
            model_name = "gemini-1.5-flash"
            model = genai.GenerativeModel(model_name)
        
        logger.debug(f"Using model: {model_name} for song: {song.title}")
        response = model.generate_content(
            prompt,
            generation_config={
                "temperature": 0.7,
                "max_output_tokens": 200,  # Increased from 100 to allow longer facts
            },
        )
        
        if not response:
            raise ValueError("No response object from Gemini API")
        
        # Check for blocked content or errors
        if hasattr(response, 'prompt_feedback') and response.prompt_feedback:
            if hasattr(response.prompt_feedback, 'block_reason') and response.prompt_feedback.block_reason:
                raise ValueError(f"Content blocked by Gemini API: {response.prompt_feedback.block_reason}")
        
        # Get text from response - handle different response formats
        # The google-generativeai package is deprecated, so we need to handle various response formats
        response_text = None
        try:
            # Try the convenience property first (works in older versions)
            if hasattr(response, 'text') and response.text:
                response_text = response.text
        except (AttributeError, IndexError, KeyError) as e:
            logger.debug(f"response.text failed: {str(e)}, trying candidates access")
        
        # Fallback to direct candidate access
        if not response_text and hasattr(response, 'candidates') and response.candidates:
            try:
                if len(response.candidates) > 0:
                    candidate = response.candidates[0]
                    if hasattr(candidate, 'content') and candidate.content:
                        if hasattr(candidate.content, 'parts') and candidate.content.parts:
                            if len(candidate.content.parts) > 0:
                                part = candidate.content.parts[0]
                                if hasattr(part, 'text'):
                                    response_text = part.text
            except (AttributeError, IndexError, KeyError) as e:
                logger.debug(f"candidates access failed: {str(e)}")
        
        if not response_text:
            logger.error(f"Response structure: {type(response)}")
            logger.error(f"Response attributes: {[attr for attr in dir(response) if not attr.startswith('_')]}")
            if hasattr(response, 'candidates'):
                logger.error(f"Response candidates count: {len(response.candidates) if response.candidates else 0}")
            raise ValueError("Empty or invalid response from Gemini API - no text found")
        
        logger.debug(f"Raw Gemini response: {response_text[:200]}...")
        
        # Try to parse JSON
        try:
            parsed = json.loads(response_text.strip())
            if 'fact' in parsed:
                logger.info(f"Successfully parsed fun fact for '{song.title}'")
                return parsed
            else:
                logger.warning(f"JSON parsed but no 'fact' key found. Keys: {parsed.keys()}")
                # Try to extract fact from other possible keys
                for key in ['fact', 'fun_fact', 'text', 'content']:
                    if key in parsed:
                        return {'fact': str(parsed[key])}
        except json.JSONDecodeError as json_err:
            logger.warning(f"JSON parse error: {str(json_err)}, trying parse_json_from_text")
            try:
                parsed = parse_json_from_text(response_text.strip())
                if 'fact' in parsed:
                    return parsed
            except Exception as parse_err:
                logger.error(f"Failed to parse JSON from text: {str(parse_err)}")
                # Last resort: return the raw text as fact
                return {'fact': response_text.strip()[:255]}  # Limit to 255 chars
        
        raise ValueError("Could not extract 'fact' from Gemini API response")
        
    except ValueError as ve:
        # Re-raise ValueError (API key, blocked content, etc.)
        logger.error(f"ValueError in fun fact generation: {str(ve)}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error generating fun fact for '{song.title}': {str(e)}", exc_info=True)
        logger.error(f"Error type: {type(e).__name__}")
        raise

if __name__ == "__main__":
    song = GenFunFact(
        title="It Ain’t Me",
        artist="Kygo and Selena Gomez",
        url="https://open.spotify.com/track/3eR23VReFzcdmS7TYCrhCe?si=2f24d149fcaa477f"
    )

    fun_fact = generate_fun_fact(song)
    logger.info(f"Generated fun fact: {fun_fact}")
