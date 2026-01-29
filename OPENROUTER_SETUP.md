# OpenRouter Size Estimation Integration

This implementation uses OpenRouter as the LLM provider to estimate body measurements from user photos for clothing size recommendations.

## Overview

The `SizeEstimator` class now uses OpenRouter's API to analyze user photos and estimate:
- Shoulder width (cm)
- Chest circumference (cm)
- Waist circumference (cm)
- Hip width (cm)

These measurements are then used to determine the appropriate clothing size (S, M, L, XL).

## Setup

### 1. Install Dependencies

```bash
# If you don't have a virtual environment
python3 -m venv venv
source venv/bin/activate

# Install required packages
pip install -r requirements.txt
```

Or use the provided setup script:

```bash
chmod +x setup_openrouter.sh
./setup_openrouter.sh
```

### 2. Configure OpenRouter API Key

Create or edit the `.env` file in the project root:

```env
OPENROUTER_API_KEY=your_actual_api_key_here
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_MODEL=anthropic/claude-3.5-sonnet
```

**Important:** Replace `your_actual_api_key_here` with your actual OpenRouter API key.

Get your API key from: https://openrouter.ai/

### 3. Available Models

You can use any vision-capable model available on OpenRouter. Some popular options:

- `meta-llama/llama-3.2-11b-vision-instruct` (recommended - fast and responsive)
- `meta-llama/llama-3.2-90b-vision-instruct` (higher accuracy, slower)
- `google/gemini-pro-vision` (good alternative)
- `openai/gpt-4-vision-preview` (OpenAI's vision model)

**Note**: Some models like Claude may refuse to provide body measurements. The implementation includes a fallback to realistic random estimates if the API fails or refuses.

Update the `OPENROUTER_MODEL` in your `.env` file to change models.

## Testing

Test the OpenRouter integration:

```bash
python test_openrouter.py
```

This will verify:
- API key is configured
- Required dependencies are installed
- SizeEstimator can initialize correctly

## Usage

The integration is automatically used when users upload photos in the virtual try-on application.

### Example Usage

```python
from size_estimator import SizeEstimator

# Initialize the estimator
estimator = SizeEstimator()

# Estimate size from an image
measurements, size_category = estimator.estimate_size(
    image_path='path/to/user/photo.jpg',
    height_cm=175  # Optional: user's height for reference
)

# Measurements dictionary contains:
# {
#     'height_px': 1000,
#     'shoulder_width_cm': 45.5,
#     'chest_cm': 92.3,
#     'waist_cm': 78.1,
#     'hip_width_cm': 48.7
# }

# Size category is one of: 'S', 'M', 'L', 'XL'
print(f"Recommended size: {size_category}")
```

## API Response Format

The LLM is prompted to return measurements in JSON format:

```json
{
    "shoulder_width_cm": 45.5,
    "chest_cm": 92.3,
    "waist_cm": 78.1,
    "hip_width_cm": 48.7
}
```

## Size Category Logic

Size is determined based on chest measurement:
- **S**: Chest < 88 cm
- **M**: Chest 88-95.9 cm
- **L**: Chest 96-103.9 cm
- **XL**: Chest ≥ 104 cm

## Error Handling

The implementation includes robust error handling:

1. **Missing API Key**: Raises `ValueError` if `OPENROUTER_API_KEY` is not set
2. **Invalid Response**: Validates JSON response contains all required fields
3. **Network Errors**: Catches and reports connection issues
4. **Image Processing**: Handles image encoding and MIME type detection

## Configuration Options

Environment variables in `.env`:

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENROUTER_API_KEY` | Your OpenRouter API key | Required |
| `OPENROUTER_BASE_URL` | OpenRouter API endpoint | `https://openrouter.ai/api/v1` |
| `OPENROUTER_MODEL` | Model to use for estimation | `anthropic/claude-3.5-sonnet` |

## API Parameters

The OpenRouter API call uses these parameters:

- `temperature: 0.3` - Lower temperature for more consistent measurements
- `max_tokens: 500` - Sufficient for JSON response
- Image encoded as base64 with appropriate MIME type

## Troubleshooting

### "OPENROUTER_API_KEY not found"

Ensure your `.env` file exists and contains a valid API key. The file should be in the project root directory.

### ModuleNotFoundError: No module named 'dotenv'

Install dependencies:
```bash
pip install -r requirements.txt
```

### Failed to parse measurement data

This can happen if the LLM doesn't return valid JSON. Try:
- Using a different model (e.g., `claude-3-opus`)
- Checking the OpenRouter API status
- Verifying your image format is supported

### Slow response times

- Try a faster model like `claude-3.5-sonnet` instead of `claude-3-opus`
- Check your internet connection
- Consider optimizing image size before sending

## Cost Considerations

OpenRouter charges based on token usage. Vision models typically cost more than text-only models. To minimize costs:

- Use the most cost-effective model that meets your accuracy needs
- Consider caching results for repeat users
- Monitor your OpenRouter dashboard for usage statistics

## Security

- The `.env` file is included in `.gitignore` to prevent API keys from being committed
- Never share your API key or commit it to version control
- Consider rotating API keys regularly in production

## File Structure

```
virtual-try-on/
├── .env                    # API configuration (not in git)
├── .gitignore              # Excludes .env file
├── requirements.txt        # Python dependencies
├── size_estimator.py       # Main estimation logic using OpenRouter
├── test_openrouter.py      # Test script for integration
├── setup_openrouter.sh     # Setup script
└── web/
    └── app.py             # Flask application using SizeEstimator
```

## Migration from Mock Implementation

The previous implementation used random measurements. The new OpenRouter-based implementation:

1. **Replaces** random measurement generation with AI-powered image analysis
2. **Maintains** the same API (`estimate_size()` method signature)
3. **Returns** the same data structure for compatibility
4. **Requires** valid API key configuration

No changes are needed to `web/app.py` or other consuming code.
