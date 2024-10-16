import yt_dlp


def extract_audio_url(query: str):
    ydl_opts = {"format": "bestaudio/best", "quiet": True, "playlistend": 64}

    if not query.startswith("http"):
        query = f"ytsearch:{query}"

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(query, download=False)

    def format_info(info):
        return info["url"], info["webpage_url"], info["title"]

    if "entries" in info:
        if query.startswith("ytsearch"):
            info = info["entries"][0]
        else:
            return [format_info(entry) for entry in info["entries"]]
    return [format_info(info)]
