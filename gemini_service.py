"""Google Gemini API integration for TTS processing"""
import os
import hashlib
import trafilatura
from typing import Optional, Tuple


def format_content_for_tts(content: str, title: str) -> Optional[str]:
    """
    Use Gemma model to format content for TTS narration
    
    Args:
        content: Raw extracted content
        title: Article title
        
    Returns:
        Formatted transcript or None if failed
    """
    try:
        import google.generativeai as genai
        
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            raise Exception("GEMINI_API_KEY not set")
        
        genai.configure(api_key=api_key)
        
        formatting_model = genai.GenerativeModel('gemma-2-27b-it')
        
        formatting_prompt = f"""You are a transcript formatter for text-to-speech systems. Your task is to take the following article content and format it as a clean, natural-sounding transcript suitable for TTS.

Remove any: URLs, email addresses, navigation elements, advertisements, meta information, HTML artifacts, and redundant formatting.

Make it flow naturally for audio narration. Return ONLY the formatted transcript text with no explanations, no markdown, no headings, no preamble - just the clean transcript.

Title: {title}

Content:
{content}

Remember: Return ONLY the transcript text, nothing else."""

        formatting_response = formatting_model.generate_content(formatting_prompt)
        formatted_transcript = formatting_response.text.strip()
        
        return formatted_transcript if formatted_transcript else None
        
    except Exception as e:
        print(f"Error formatting content: {str(e)}")
        return None


def generate_audio_from_text(text: str) -> Optional[bytes]:
    """
    Generate audio from text using Gemini TTS
    
    Args:
        text: Formatted transcript text
        
    Returns:
        Audio data as bytes or None if failed
    """
    try:
        import google.generativeai as genai
        
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            raise Exception("GEMINI_API_KEY not set")
        
        genai.configure(api_key=api_key)
        
        tts_model = genai.GenerativeModel('gemini-2.0-flash-exp')
        
        tts_response = tts_model.generate_content(
            text,
            generation_config={
                'response_modalities': ['AUDIO']
            }
        )
        
        if hasattr(tts_response, 'audio') and tts_response.audio:
            return tts_response.audio
        
        return None
        
    except Exception as e:
        print(f"Error generating audio: {str(e)}")
        return None


def extract_content_from_url(url: str) -> Optional[str]:
    """
    Download and extract text content from URL using trafilatura
    
    Args:
        url: URL to extract content from
        
    Returns:
        Extracted text content or None if failed
    """
    try:
        downloaded = trafilatura.fetch_url(url)
        if not downloaded:
            return None
        
        content = trafilatura.extract(downloaded)
        if not content:
            return None
        
        # Truncate content if too long (Gemini has token limits)
        max_chars = 30000
        if len(content) > max_chars:
            content = content[:max_chars] + "..."
        
        return content
        
    except Exception as e:
        print(f"Error extracting content from URL: {str(e)}")
        return None


def process_url_to_audio(url: str, title: str, audio_dir: str) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Complete pipeline: Extract content, format for TTS, generate audio
    
    Args:
        url: URL to process
        title: Article title
        audio_dir: Directory to save audio file
        
    Returns:
        Tuple of (success, audio_path, error_message)
    """
    try:
        # Step 1: Extract content
        content = extract_content_from_url(url)
        if not content:
            return False, None, "Failed to extract content from URL"
        
        # Step 2: Format content for TTS
        formatted_transcript = format_content_for_tts(content, title)
        if not formatted_transcript:
            return False, None, "Failed to format content for TTS"
        
        # Step 3: Generate audio
        audio_data = generate_audio_from_text(formatted_transcript)
        if not audio_data:
            return False, None, "Failed to generate audio from text"
        
        # Step 4: Save audio file
        audio_filename = f"{hashlib.sha256(url.encode()).hexdigest()[:12]}.wav"
        audio_path = os.path.join(audio_dir, audio_filename)
        
        with open(audio_path, 'wb') as f:
            f.write(audio_data)
        
        return True, audio_path, None
        
    except Exception as e:
        error_msg = str(e)
        print(f"Error in TTS pipeline: {error_msg}")
        return False, None, error_msg
