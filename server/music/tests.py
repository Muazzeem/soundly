import re


pattern = (
    r"^(https:\/\/)?open\.spotify\.com\/track\/[a-zA-Z0-9]+(\?si=[a-zA-Z0-9_\-]+)?$"
)

spotify_url = (
    "https://open.spotify.com/track/2RdEC8Ff83WkX7kDVCHseE?si=3ea50b2737a44d04"
)

c = re.match(pattern, spotify_url)

print(c)
