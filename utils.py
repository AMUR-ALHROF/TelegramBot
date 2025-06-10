"""
Utility functions for the Treasure Hunter Bot
"""

import base64
import io
import time
from collections import defaultdict
from typing import Optional
from PIL import Image
import logging

logger = logging.getLogger(__name__)

class RateLimiter:
    """Simple rate limiter to prevent API abuse"""
    
    def __init__(self, max_requests_per_minute: int = 10):
        self.max_requests = max_requests_per_minute
        self.requests = defaultdict(list)
    
    def is_allowed(self, user_id: int) -> bool:
        """Check if user is allowed to make a request"""
        current_time = time.time()
        user_requests = self.requests[user_id]
        
        # Remove requests older than 1 minute
        self.requests[user_id] = [req_time for req_time in user_requests 
                                 if current_time - req_time < 60]
        
        # Check if under limit
        if len(self.requests[user_id]) < self.max_requests:
            self.requests[user_id].append(current_time)
            return True
        
        return False
    
    def get_wait_time(self, user_id: int) -> int:
        """Get wait time in seconds before next request"""
        if not self.requests[user_id]:
            return 0
        
        oldest_request = min(self.requests[user_id])
        wait_time = 60 - (time.time() - oldest_request)
        return max(0, int(wait_time))

def image_to_base64(image_data: bytes, max_size_mb: int = 10) -> Optional[str]:
    """Convert image data to base64 string with size validation"""
    try:
        # Check file size
        if len(image_data) > max_size_mb * 1024 * 1024:
            logger.warning(f"Image too large: {len(image_data)} bytes")
            return None
        
        # Open and validate image
        image = Image.open(io.BytesIO(image_data))
        
        # Convert to RGB if necessary
        if image.mode not in ['RGB', 'RGBA']:
            image = image.convert('RGB')
        
        # Resize if too large (max 1024x1024 for better processing)
        max_dimension = 1024
        if image.width > max_dimension or image.height > max_dimension:
            image.thumbnail((max_dimension, max_dimension), Image.Resampling.LANCZOS)
        
        # Convert to base64
        buffer = io.BytesIO()
        image.save(buffer, format='JPEG', quality=85)
        image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        
        return image_base64
        
    except Exception as e:
        logger.error(f"Error converting image to base64: {e}")
        return None

def format_response(text: str, max_length: int = 4000) -> list:
    """Format response text for Telegram (max 4096 chars per message)"""
    if len(text) <= max_length:
        return [text]
    
    # Split into chunks at natural break points
    chunks = []
    current_chunk = ""
    
    paragraphs = text.split('\n\n')
    
    for paragraph in paragraphs:
        if len(current_chunk) + len(paragraph) + 2 <= max_length:
            if current_chunk:
                current_chunk += '\n\n'
            current_chunk += paragraph
        else:
            if current_chunk:
                chunks.append(current_chunk)
            
            # If single paragraph is too long, split by sentences
            if len(paragraph) > max_length:
                sentences = paragraph.split('. ')
                temp_chunk = ""
                
                for sentence in sentences:
                    if len(temp_chunk) + len(sentence) + 2 <= max_length:
                        if temp_chunk:
                            temp_chunk += '. '
                        temp_chunk += sentence
                    else:
                        if temp_chunk:
                            chunks.append(temp_chunk + '.')
                        temp_chunk = sentence
                
                current_chunk = temp_chunk
            else:
                current_chunk = paragraph
    
    if current_chunk:
        chunks.append(current_chunk)
    
    return chunks

def escape_markdown(text: str) -> str:
    """Escape markdown special characters for Telegram"""
    special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for char in special_chars:
        text = text.replace(char, f'\\{char}')
    return text
