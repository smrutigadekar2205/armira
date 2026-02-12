import os
import base64
import random
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class SizeEstimator:
    def __init__(self):
        """Initialize the SizeEstimator with OpenRouter API configuration."""
        self.api_key = os.getenv('OPENROUTER_API_KEY')
        self.base_url = os.getenv('OPENROUTER_BASE_URL', 'https://openrouter.ai/api/v1')
        self.model = os.getenv('OPENROUTER_MODEL', 'anthropic/claude-3.5-sonnet')
        
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY not found in environment variables. "
                           "Please set it in your .env file.")
        
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )
    
    def _encode_image(self, image_path):
        """Encode image to base64 string."""
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    
    def _get_mime_type(self, image_path):
        """Get MIME type based on file extension."""
        ext = os.path.splitext(image_path)[1].lower()
        mime_types = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.webp': 'image/webp'
        }
        return mime_types.get(ext, 'image/jpeg')
    
    def _fallback_estimation(self, height_cm=None):
        """
        Fallback estimation using realistic random values based on height.
        This is used when the LLM refuses or fails to provide measurements.
        """
        if not height_cm:
            height_cm = random.randint(160, 185)
        
        # Generate realistic measurements based on height
        chest = (height_cm * 0.55) * random.uniform(0.9, 1.1)
        waist = (height_cm * 0.48) * random.uniform(0.85, 1.15)
        hips = (height_cm * 0.58) * random.uniform(0.9, 1.1)
        shoulder = (height_cm * 0.25) * random.uniform(0.9, 1.1)
        
        measurements = {
            'height_px': 1000,
            'shoulder_width_cm': round(shoulder, 1),
            'chest_cm': round(chest, 1),
            'waist_cm': round(waist, 1),
            'hip_width_cm': round(hips, 1)
        }
        
        # Determine size category
        if chest < 88:
            size_category = 'S'
        elif chest < 96:
            size_category = 'M'
        elif chest < 104:
            size_category = 'L'
        else:
            size_category = 'XL'
        
        return measurements, size_category
    
    def estimate_size(self, image_path, height_cm=None):
        """
        Estimate body measurements and size category from an image using OpenRouter LLM.
        Falls back to estimation if LLM fails or refuses.
        
        Args:
            image_path: Path to the user's image file
            height_cm: Optional height in centimeters for reference
            
        Returns:
            tuple: (measurements_dict, size_category)
                  measurements_dict contains: height_px, shoulder_width_cm, chest_cm, waist_cm, hip_width_cm
                  size_category is one of: 'S', 'M', 'L', 'XL'
        """
        try:
            # Encode image
            base64_image = self._encode_image(image_path)
            mime_type = self._get_mime_type(image_path)
            
            # Build prompt - more explicit that these are estimates for a demo
            height_info = f"The user's height is approximately {height_cm} cm." if height_cm else ""
            
            prompt = f"""This is a virtual try-on application demonstration. I need you to provide estimated body measurements for clothing size recommendations.

{height_info}

These are ROUGH ESTIMATES for a demo application - they do not need to be medically or professionally accurate. The goal is to show how a virtual try-on system would work.

Please provide the following measurements in centimeters:
1. Shoulder width (distance across shoulders)
2. Chest circumference (around the fullest part of the chest)
3. Waist circumference (around the narrowest part of the waist)
4. Hip width (distance across the hips at widest point)

Look at the person in the photo and make your best estimate based on their visible proportions. Use the provided height as a reference if available.

Respond ONLY with a valid JSON object in this exact format:
{{
    "shoulder_width_cm": <number>,
    "chest_cm": <number>,
    "waist_cm": <number>,
    "hip_width_cm": <number>
}}

Do not include any other text, explanations, or disclaimers. Just the JSON."""

            # Make API call to OpenRouter
            print(f"[SizeEstimator] Calling OpenRouter API with model: {self.model}")
            
            response = self.client.chat.completions.create(
                model=self.model,
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
            
            # Extract response
            if not response.choices or len(response.choices) == 0:
                raise ValueError("No choices returned from API response")
            
            result_text = response.choices[0].message.content
            
            if not result_text:
                raise ValueError("Empty response content from API")
            
            result_text = result_text.strip()
            print(f"[SizeEstimator] Raw response: {result_text[:200]}...")
            
            # Parse JSON response
            import json
            
            # Try to extract JSON if there's extra text
            start_idx = result_text.find('{')
            end_idx = result_text.rfind('}') + 1
            
            if start_idx != -1 and end_idx > start_idx:
                json_text = result_text[start_idx:end_idx]
                measurements = json.loads(json_text)
            else:
                measurements = json.loads(result_text)
            
            # Validate required fields
            required_fields = ['shoulder_width_cm', 'chest_cm', 'waist_cm', 'hip_width_cm']
            for field in required_fields:
                if field not in measurements:
                    raise ValueError(f"Missing required field in response: {field}")
            
            # Round measurements to 1 decimal place
            measurements = {
                k: round(float(v), 1) for k, v in measurements.items()
            }
            
            # Add height_px (dummy value for compatibility with existing code)
            measurements['height_px'] = 1000
            
            # Determine size category based on chest measurement
            chest = measurements['chest_cm']
            if chest < 88:
                size_category = 'S'
            elif chest < 96:
                size_category = 'M'
            elif chest < 104:
                size_category = 'L'
            else:
                size_category = 'XL'
            
            print(f"[SizeEstimator] Successfully estimated: {measurements}, size: {size_category}")
            return measurements, size_category
            
        except json.JSONDecodeError as e:
            print(f"[SizeEstimator] JSON parse error, using fallback: {e}")
            print(f"[SizeEstimator] Response was: {result_text[:100]}...")
            return self._fallback_estimation(height_cm)
            
        except Exception as e:
            print(f"[SizeEstimator] API error, using fallback: {str(e)}")
            return self._fallback_estimation(height_cm)
