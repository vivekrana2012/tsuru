"""Background worker for TTS queue processing"""
import asyncio
import os
from database import (
    get_pending_tts_queue_items,
    update_tts_queue_status,
    store_feed_with_audio
)
from gemini_service import process_url_to_audio

# Audio directory
DATA_DIR = os.getenv('DATA_DIR', '.')
AUDIO_DIR = os.path.join(DATA_DIR, 'audio')


async def process_tts_queue():
    """Process pending TTS queue entries (1 per run due to rate limits)"""
    try:
        # Check if Gemini API key is set
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            print("Warning: GEMINI_API_KEY not set. TTS processing disabled.")
            return
        
        # Get pending queue items (limit to 1 due to Gemini rate limits)
        queue_items = get_pending_tts_queue_items(limit=1)
        
        for item in queue_items:
            try:
                print(f"Processing TTS for: {item['title']}")
                
                # Update status to processing
                update_tts_queue_status(item['id'], 'processing')
                
                # Process URL to audio (extract, format, generate)
                success, audio_path, error_msg = process_url_to_audio(
                    item['url'],
                    item['title'],
                    AUDIO_DIR
                )
                
                if success and audio_path:
                    # Store in feed table with audio path
                    store_feed_with_audio(
                        item['url'],
                        item['title'],
                        item['description'],
                        item['added_by'],
                        audio_path
                    )
                    
                    # Update queue status to completed
                    update_tts_queue_status(item['id'], 'completed')
                    
                    print(f"Successfully processed TTS for: {item['title']}")
                else:
                    # Update queue status to failed
                    update_tts_queue_status(
                        item['id'],
                        'failed',
                        error_msg or "Unknown error"
                    )
                    print(f"Failed to process TTS: {error_msg}")
                
            except Exception as e:
                error_msg = str(e)
                print(f"Error processing TTS queue item {item['id']}: {error_msg}")
                
                # Update queue status to failed
                update_tts_queue_status(item['id'], 'failed', error_msg)
    
    except Exception as e:
        print(f"Error in TTS queue processing: {str(e)}")


async def tts_worker():
    """Background worker that processes TTS queue every minute"""
    while True:
        try:
            await process_tts_queue()
        except Exception as e:
            print(f"TTS worker error: {str(e)}")
        
        # Wait 60 seconds before next poll
        await asyncio.sleep(60)


if __name__ == "__main__":
    """Run worker standalone for testing"""
    asyncio.run(tts_worker())
