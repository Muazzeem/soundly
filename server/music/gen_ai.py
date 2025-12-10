import os
import json
import google.generativeai as genai

# --- Configure your Gemini API key ---
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", "AIzaSyAMaydye9zcwRtHey4RcraY_A4XBkdOoM4")

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
    genai.configure(api_key=GOOGLE_API_KEY)

    prompt = build_interaction_prompt(song.title, song.artist, song.url)

    model = genai.GenerativeModel("gemini-2.5-flash-lite")
    response = model.generate_content(
        prompt,
        generation_config={
            "temperature": 0.7,
            "max_output_tokens": 100,
        },
    )

    try:
        return json.loads(response.text.strip())
    except json.JSONDecodeError:
        return parse_json_from_text(response.text.strip())

if __name__ == "__main__":
    song = GenFunFact(
        title="It Ain’t Me",
        artist="Kygo and Selena Gomez",
        url="https://open.spotify.com/track/3eR23VReFzcdmS7TYCrhCe?si=2f24d149fcaa477f"
    )

    fun_fact = generate_fun_fact(song)
    print(fun_fact)
