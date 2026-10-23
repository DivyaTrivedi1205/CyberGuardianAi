#!/usr/bin/env python3
"""Generate extension icons using PIL"""
from PIL import Image, ImageDraw, ImageFont
import os

# Create icons directory if it doesn't exist
os.makedirs('icons', exist_ok=True)

def create_icon(size):
    """Create a simple blue icon with 'CG' text"""
    img = Image.new('RGB', (size, size), color=(59, 130, 246))  # #3b82f6
    draw = ImageDraw.Draw(img)

    # Try to use a nice font, fall back to default
    try:
        font = ImageFont.truetype("arial.ttf", int(size * 0.6))
    except:
        font = ImageFont.load_default()

    # Draw 'CG' text
    text = 'CG'
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    x = (size - text_width) // 2
    y = (size - text_height) // 2
    draw.text((x, y), text, fill='white', font=font)

    return img

# Generate icons
for size in [16, 48, 128]:
    img = create_icon(size)
    img.save(f'icons/icon-{size}.png')
    print(f'Created icons/icon-{size}.png')

print('All icons generated successfully')
