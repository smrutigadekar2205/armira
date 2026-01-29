#!/usr/bin/env python3
"""
Debug script to test OpenRouter API directly and see the actual response.
"""
import os
import sys
import base64
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables
load_dotenv()

# Check for API key
api_key = os.getenv('OPENROUTER_API_KEY')
if not api_key or api_key == 'your_openrouter_api_key_here':
    print("❌ OPENROUTER_API_KEY not set in .env file")
    sys.exit(1)

print("✓ OPENROUTER_API_KEY is set")

base_url = os.getenv('OPENROUTER_BASE_URL', 'https://openrouter.ai/api/v1')
model = os.getenv('OPENROUTER_MODEL', 'anthropic/claude-3.5-sonnet')

print(f"✓ Base URL: {base_url}")
print(f"✓ Model: {model}")
print()

# Initialize client
client = OpenAI(api_key=api_key, base_url=base_url)

# Find a test image
test_image_path = None
search_paths = [
    '/mnt/b/local_projects/virtual-try-on/web/static/uploads/users',
    '/mnt/b/local_projects/virtual-try-on/web/static/uploads',
    '/mnt/b/local_projects/virtual-try-on/web/static'
]

for path in search_paths:
    if os.path.exists(path):
        for file in os.listdir(path):
            if file.lower().endswith(('.jpg', '.jpeg', '.png', '.webp')):
                test_image_path = os.path.join(path, file)
                break
    if test_image_path:
        break

if not test_image_path:
    print("❌ No test image found. Please upload a user photo first.")
    sys.exit(1)

print(f"✓ Using test image: {test_image_path}")
print()

# Encode image
with open(test_image_path, "rb") as image_file:
    base64_image = base64.b64encode(image_file.read()).decode('utf-8')

# Get MIME type
ext = os.path.splitext(test_image_path)[1].lower()
mime_type = {
    '.jpg': 'image/jpeg',
    '.jpeg': 'image/jpeg',
    '.png': 'image/png',
    '.webp': 'image/webp'
}.get(ext, 'image/jpeg')

# Test prompt
prompt = """Analyze this person's photo and estimate their body measurements for clothing size recommendation.

Please provide the following measurements in centimeters:
1. Shoulder width (distance across shoulders)
2. Chest circumference (around the fullest part of the chest)
3. Waist circumference (around the narrowest part of the waist)
4. Hip width (distance across the hips at widest point)

Respond ONLY with a valid JSON object in this exact format:
{
    "shoulder_width_cm": <number>,
    "chest_cm": <number>,
    "waist_cm": <number>,
    "hip_width_cm": <number>
}

Do not include any other text or explanation."""

print("Calling OpenRouter API...")
print("-" * 80)

try:
    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": prompt
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{mime_type};base64,{base64_image}"
                        }
                    }
                ]
            }
        ],
        max_tokens=500,
        temperature=0.3
    )
    
    print("-" * 80)
    print("\n✅ API call successful!")
    print(f"\nResponse ID: {response.id}")
    print(f"Model: {response.model}")
    print(f"Choices: {len(response.choices)}")
    
    if response.choices:
        content = response.choices[0].message.content
        print(f"\nRaw response content:")
        print("=" * 80)
        print(content)
        print("=" * 80)
        
        # Try to parse as JSON
        import json
        try:
            start_idx = content.find('{')
            end_idx = content.rfind('}') + 1
            
            if start_idx != -1 and end_idx > start_idx:
                json_text = content[start_idx:end_idx]
                measurements = json.loads(json_text)
            else:
                measurements = json.loads(content)
            
            print("\n✅ Successfully parsed JSON:")
            print(json.dumps(measurements, indent=2))
        except json.JSONDecodeError as e:
            print(f"\n❌ Failed to parse JSON: {e}")
    
except Exception as e:
    print("-" * 80)
    print(f"\n❌ API call failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
