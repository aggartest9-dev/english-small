import re

def convert_link(link):
    """
    Check if the URL is a YouTube or Google Drive link and return the appropriate formatted URL.
    Handles None or empty strings gracefully.
    """
    # If the link is None or empty, return it as-is
    if not link:
        return link
    
    # Check for YouTube URL
    youtube_regex = re.compile(r'https?://(?:www\.)?youtube\.com/watch\?v=([A-Za-z0-9_-]+)')
    youtube_match = youtube_regex.match(link)
    
    if youtube_match:
        # Convert to embed URL
        video_id = youtube_match.group(1)
        return f'https://www.youtube.com/embed/{video_id}'

    # Check for Google Drive URL
    drive_regex = re.compile(r'https?://drive\.google\.com/file/d/([A-Za-z0-9_-]+)/view\?usp=sharing')
    drive_match = drive_regex.match(link)
    
    if drive_match:
        # Convert to download URL
        file_id = drive_match.group(1)
        return f'https://drive.google.com/uc?export=download&id={file_id}'

    # If it's neither YouTube nor Google Drive, return the link as-is
    return link