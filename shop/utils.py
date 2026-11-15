# shop/utils.py
import re
from PIL import Image, ImageDraw, ImageFont
import os
from django.conf import settings
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
import uuid

def process_chat_message(message):
    """Rule-based NLP to extract customization parameters"""
    
    response = {
        'action': None,
        'parameters': {},
        'reply': ''
    }
    
    message = message.lower()
    
    # Detect customization intent
    if any(word in message for word in ['add', 'put', 'write', 'place', 'customize', 'print']):
        response['action'] = 'customize'
        
        # Extract text (content between quotes)
        text_match = re.search(r'"([^"]*)"', message)
        if text_match:
            response['parameters']['text'] = text_match.group(1)
            response['reply'] = f"I'll add text: '{response['parameters']['text']}'. "
        
        # Extract colors
        colors = {
            'red': '#FF0000', 'blue': '#0000FF', 'green': '#00FF00',
            'black': '#000000', 'white': '#FFFFFF', 'yellow': '#FFFF00',
            'purple': '#800080', 'orange': '#FFA500', 'pink': '#FFC0CB',
            'brown': '#A52A2A', 'gray': '#808080', 'navy': '#000080',
            'gold': '#FFD700', 'silver': '#C0C0C0'
        }
        
        for color_name, hex_code in colors.items():
            if color_name in message:
                if 'text' in response['parameters'] or 'text' in message:
                    response['parameters']['text_color'] = hex_code
                    response['reply'] += f"Text color: {color_name}. "
                else:
                    response['parameters']['icon_color'] = hex_code
                    response['reply'] += f"Icon color: {color_name}. "
                break
        
        # Extract icons/emojis
        icons = {
            'heart': '❤️', 'star': '⭐', 'smile': '😊', 'sun': '☀️',
            'flower': '🌸', 'tree': '🌲', 'bird': '🐦', 'cat': '🐱',
            'dog': '🐶', 'crown': '👑', 'diamond': '💎', 'car': '🚗',
            'ball': '⚽', 'book': '📚', 'coffee': '☕', 'music': '🎵'
        }
        
        for icon_name, icon_symbol in icons.items():
            if icon_name in message:
                response['parameters']['icon'] = icon_symbol
                response['reply'] += f"Adding {icon_name} icon. "
                break
        
        # Extract position
        positions = {
            'front': 'front', 'center': 'front', 'middle': 'front',
            'back': 'back', 'behind': 'back',
            'left chest': 'left_chest', 'left side': 'left_chest',
            'right chest': 'right_chest', 'right side': 'right_chest',
            'left sleeve': 'left_sleeve', 'right sleeve': 'right_sleeve'
        }
        
        for pos_key, pos_value in positions.items():
            if pos_key in message:
                response['parameters']['position'] = pos_value
                response['reply'] += f"Position: {pos_key}. "
                break
        
        if not response.get('reply'):
            response['reply'] = "I can help you customize! Tell me what text, color, or icon you'd like to add."
            
    elif any(word in message for word in ['help', 'what can you do', 'how to use']):
        response['action'] = 'help'
        response['reply'] = "I'm your customization assistant! Try saying:\n• 'Add text \"Hello\" in red on front'\n• 'Add heart icon in blue'\n• 'Put text on back in white'"
    
    elif any(word in message for word in ['hello', 'hi', 'hey']):
        response['action'] = 'greeting'
        response['reply'] = "Hello! How can I help you customize your clothing today?"
    
    else:
        response['action'] = 'unknown'
        response['reply'] = "I'm here to help with customization. Try asking me to add text or icons to your clothing!"
    
    return response

def generate_preview_image(product_image_path, customization_params):
    """Generate customized preview using PIL"""
    try:
        # Open the base product image
        if isinstance(product_image_path, str):
            img_path = product_image_path
        else:
            img_path = product_image_path.path
        
        product_image = Image.open(img_path).convert('RGBA')
        
        # Create a drawing layer
        overlay = Image.new('RGBA', product_image.size, (255, 255, 255, 0))
        draw = ImageDraw.Draw(overlay)
        
        # Get image dimensions
        width, height = product_image.size
        
        # Get parameters
        text = customization_params.get('custom_text', '')
        text_color = customization_params.get('text_color', '#000000')
        icon = customization_params.get('icon', '')
        text_size = int(customization_params.get('text_size', 30))
        
        # Get positions (convert from percentage or use absolute)
        text_x = int(customization_params.get('text_x', width // 2))
        text_y = int(customization_params.get('text_y', height // 2))
        icon_x = int(customization_params.get('icon_x', width // 2))
        icon_y = int(customization_params.get('icon_y', height // 2 + 50))
        
        print(f"=== GENERATING PREVIEW ===")
        print(f"Text: '{text}'")
        print(f"Icon: '{icon}'")
        print(f"Image size: {width} x {height}")
        print(f"Text position: ({text_x}, {text_y})")
        print(f"Icon position: ({icon_x}, {icon_y})")
        
        try:
            # Try to load a font that supports emoji
            font_path = os.path.join(settings.BASE_DIR, 'static/fonts/arial.ttf')
            if os.path.exists(font_path):
                font = ImageFont.truetype(font_path, text_size)
                icon_font = ImageFont.truetype(font_path, text_size + 10)
            else:
                # Use default font
                font = ImageFont.load_default()
                icon_font = ImageFont.load_default()
        except:
            font = ImageFont.load_default()
            icon_font = ImageFont.load_default()
        
        # Draw text if provided
        if text:
            # Calculate text bounding box to center properly
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            
            # Adjust position to center the text
            adjusted_x = text_x - text_width // 2
            adjusted_y = text_y - text_height // 2
            
            draw.text((adjusted_x, adjusted_y), text, fill=text_color, font=font)
            print(f"Drew text: '{text}' at ({adjusted_x}, {adjusted_y})")
        
        # Draw icon if provided
        if icon:
            # Calculate icon bounding box
            bbox = draw.textbbox((0, 0), icon, font=icon_font)
            icon_width = bbox[2] - bbox[0]
            icon_height = bbox[3] - bbox[1]
            
            # Adjust position to center the icon
            adjusted_icon_x = icon_x - icon_width // 2
            adjusted_icon_y = icon_y - icon_height // 2
            
            draw.text((adjusted_icon_x, adjusted_icon_y), icon, fill='#F28735', font=icon_font)
            print(f"Drew icon: '{icon}' at ({adjusted_icon_x}, {adjusted_icon_y})")
        
        # Composite the images
        final_image = Image.alpha_composite(product_image, overlay)
        
        # Generate unique filename
        import uuid
        filename = f"custom_{uuid.uuid4().hex}.png"
        preview_path = os.path.join('customizations', filename)
        full_path = os.path.join(settings.MEDIA_ROOT, preview_path)
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        
        # Save the preview
        final_image.save(full_path, 'PNG')
        print(f"Preview saved: {preview_path}")
        
        return preview_path
        
    except Exception as e:
        print(f"Error generating preview: {e}")
        import traceback
        traceback.print_exc()
        return None