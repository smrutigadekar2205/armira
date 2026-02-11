import os
import sys
import cv2
import base64
import json
import time
import shutil
import numpy as np
import requests
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add parent directory to path to import size_estimator
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from size_estimator import SizeEstimator

app = Flask(__name__)
app.secret_key = 'supersecretkey'

# Serve node_modules as static files for SDK imports
app.static_folder = 'static'
node_modules_path = os.path.join(os.path.dirname(__file__), 'node_modules')
if os.path.exists(node_modules_path):
    @app.route('/node_modules/<path:filename>')
    def serve_node_modules(filename):
        from flask import send_from_directory
        return send_from_directory(node_modules_path, filename)

# Configuration
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'web', 'static', 'uploads')
USER_UPLOAD_FOLDER = os.path.join(UPLOAD_FOLDER, 'users')
GARMENT_UPLOAD_FOLDER = os.path.join(UPLOAD_FOLDER, 'garments')
RESULTS_FOLDER = os.path.join(BASE_DIR, 'web', 'static', 'results')
DATA_ROOT = os.path.join(BASE_DIR, 'data')

# API4AI Configuration
API4AI_API_KEY = os.environ.get('API4AI_API_KEY', 'a4a-J9xM0FVgstpmGHyj9xy7egW1T71GIsid')
API4AI_URL = 'https://api4ai.cloud/virtual-try-on/v1/results'

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Ensure directories exist
os.makedirs(USER_UPLOAD_FOLDER, exist_ok=True)
os.makedirs(GARMENT_UPLOAD_FOLDER, exist_ok=True)
os.makedirs(RESULTS_FOLDER, exist_ok=True)

# Default garments folder
DEFAULT_GARMENTS_FOLDER = os.path.join(BASE_DIR, 'web', 'static', 'garments_default')
DEFAULT_GARMENTS_METADATA = os.path.join(DEFAULT_GARMENTS_FOLDER, 'metadata.json')
GARMENT_METADATA_FILE = os.path.join(GARMENT_UPLOAD_FOLDER, 'metadata.json')

# Initialize default garments if they don't exist in uploads
def initialize_default_garments():
    """Copy default garments to uploads folder if not already present"""
    if not os.path.exists(GARMENT_METADATA_FILE) or os.path.getsize(GARMENT_METADATA_FILE) == 0:
        if os.path.exists(DEFAULT_GARMENTS_METADATA):
            # Copy metadata
            with open(DEFAULT_GARMENTS_METADATA, 'r') as f:
                metadata = json.load(f)
            save_garment_metadata(metadata)
            
            # Copy images
            for filename in metadata.keys():
                src = os.path.join(DEFAULT_GARMENTS_FOLDER, filename)
                dst = os.path.join(GARMENT_UPLOAD_FOLDER, filename)
                if os.path.exists(src) and not os.path.exists(dst):
                    shutil.copy2(src, dst)
            print(f"Initialized {len(metadata)} default garments")

# Run initialization on startup
initialize_default_garments()

# Allowed extensions
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/demo')
def demo():
    return render_template('demo.html')

def load_garment_metadata():
    if os.path.exists(GARMENT_METADATA_FILE):
        with open(GARMENT_METADATA_FILE, 'r') as f:
            data = json.load(f)
            # Add dummy price and material if missing
            for item in data.values():
                if 'price' not in item:
                    item['price'] = f"${np.random.randint(29, 129)}.00"
                if 'material' not in item:
                    item['material'] = np.random.choice(['Organic Cotton', 'Recycled Polyester', 'Premium Silk', 'Tech-Mesh'])
            return data
    return {}

def save_garment_metadata(metadata):
    with open(GARMENT_METADATA_FILE, 'w') as f:
        json.dump(metadata, f, indent=4)

@app.route('/upload_user', methods=['POST'])
def upload_user():
    filename = None
    
    # Reset session for new photo/session
    session.pop('user_image', None)
    session.pop('measurements', None)
    session.pop('size_category', None)
    
    # Handle Webcam Upload
    if 'webcam_image' in request.form and request.form['webcam_image']:
        data_url = request.form['webcam_image']
        # Format: data:image/jpeg;base64,...
        header, encoded = data_url.split(",", 1)
        data = base64.b64decode(encoded)
        
        filename = f"webcam_{int(time.time())}.jpg"
        filepath = os.path.join(USER_UPLOAD_FOLDER, filename)
        
        with open(filepath, "wb") as f:
            f.write(data)
            
    # Handle File Upload
    elif 'user_image' in request.files:
        file = request.files['user_image']
        if file.filename != '' and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(USER_UPLOAD_FOLDER, filename)
            file.save(filepath)
    
    if not filename:
        flash('No image provided')
        return redirect(url_for('demo'))
        
    # Estimate size
    height_cm = request.form.get('height_cm')
    height_cm = float(height_cm) if height_cm else None
    
    # Get manual measurements
    u_chest = request.form.get('u_chest_cm')
    u_waist = request.form.get('u_waist_cm')
    u_hip = request.form.get('u_hip_cm')
    
    manual_measurements = {}
    if u_chest: manual_measurements['chest_cm'] = float(u_chest)
    if u_waist: manual_measurements['waist_cm'] = float(u_waist)
    if u_hip: manual_measurements['hip_cm'] = float(u_hip)
    
    estimator = SizeEstimator()
    # Need full path
    filepath = os.path.join(USER_UPLOAD_FOLDER, filename)
    
    estimation_result = estimator.estimate_size(filepath, height_cm)
    
    if estimation_result:
        measurements, size_category = estimation_result
    else:
        measurements = {}
        size_category = 'Unknown'
        flash('Could not detect a person in the image for automatic sizing. Please use manual inputs or try another photo.')
    
    # Merge manual measurements
    measurements.update(manual_measurements)

    
    # Refine size category if manual measurements exist
    if 'chest_cm' in measurements:
        chest = measurements['chest_cm']
        # Consistency with SizeEstimator
        if chest < 88: size_category = 'S'
        elif chest < 96: size_category = 'M'
        elif chest < 104: size_category = 'L'
        else: size_category = 'XL'
    
    # Store in session
    session['user_image'] = filename
    session['measurements'] = measurements
    session['size_category'] = size_category
    
    return redirect(url_for('select_garments'))

@app.route('/upload_user_for_tryon', methods=['POST'])
def upload_user_for_tryon():
    """Simple upload for virtual try-on - returns JSON with filename"""
    filename = None
    
    # Handle File Upload (from blob)
    if 'image' in request.files:
        file = request.files['image']
        if file.filename != '' and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(USER_UPLOAD_FOLDER, filename)
            file.save(filepath)
    
    if not filename:
        return jsonify({'error': 'No image provided'}), 400
    
    return jsonify({'success': True, 'filename': filename})

@app.route('/garments')
def select_garments():
    if 'user_image' not in session:
        return redirect(url_for('index'))
        
    # Allow override via query param, default to estimated size
    estimated_size = session.get('size_category', 'M')
    current_size = request.args.get('size', estimated_size)
    
    # Determine arguments for get_available_garments
    filter_arg = current_size
    use_measurements = session.get('measurements', {})
    
    # If specific size selected (and it matches estimate), or if it's 'All', we might use measurements?
    # Actually, always passing measurements allows 'Custom' items to potentially match if the logic allows.
    # But if user selects 'S', we generally want 'S' items.
    
    garments = get_available_garments(size_filter=filter_arg, user_measurements=use_measurements)
    
    return render_template('garments.html', 
                           user_image=session['user_image'], 
                           size_category=current_size,
                           estimated_size=estimated_size,
                           measurements=use_measurements,
                           garments=garments)


@app.route('/upload_garment', methods=['POST'])
def upload_garment():
    if 'garment_image' not in request.files:
        flash('No file part')
        return redirect(request.url)
        
    file = request.files['garment_image']
    if file.filename == '':
        flash('No selected file')
        return redirect(request.url)
        
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(GARMENT_UPLOAD_FOLDER, filename)
        file.save(filepath)
        
        # Save metadata
        size_type = request.form.get('size_type', 'standard')
        size = request.form.get('size', 'M').upper()
        category = request.form.get('category', 'Tops')
        
        garment_data = {
            'size_type': size_type,
            'category': category,
            'uploaded_at': time.time()
        }
        
        if size_type == 'standard':
            garment_data['size'] = size
        else:
            # Custom measurements
            try:
                garment_data['measurements'] = {
                    'chest': float(request.form.get('g_chest_cm') or 0),
                    'waist': float(request.form.get('g_waist_cm') or 0),
                    'length': float(request.form.get('g_length_cm') or 0)
                }
                # Auto-assign a standard size label for easier filtering fallback
                chest = garment_data['measurements']['chest']
                if chest > 0:
                    if chest < 88: garment_data['size'] = 'S'
                    elif chest < 96: garment_data['size'] = 'M'
                    elif chest < 104: garment_data['size'] = 'L'
                    else: garment_data['size'] = 'XL'
                else:
                    garment_data['size'] = 'Custom'
            except ValueError:
                garment_data['size'] = 'Unknown'
                
        metadata = load_garment_metadata()
        metadata[filename] = garment_data
        save_garment_metadata(metadata)
        
        flash(f'Garment "{category} - {garment_data["size"]}" added to wardrobe!')
        return redirect(url_for('demo'))

def get_available_garments(size_filter=None, user_measurements=None):
    metadata = load_garment_metadata()
    garments = []
    if os.path.exists(GARMENT_UPLOAD_FOLDER):
        for f in os.listdir(GARMENT_UPLOAD_FOLDER):
            if allowed_file(f):
                # Get info from metadata, default to M if missing
                info = metadata.get(f, {'size': 'M', 'category': 'Unknown'})
                
                # Matching Logic
                is_match = False
                
                # 1. Custom Measurement Match (if user has measurements and garment has measurements)
                if user_measurements and info.get('size_type') == 'custom' and 'measurements' in info:
                    # Simple logic: fit if garment chest >= user chest (allow some ease)
                    u_chest = user_measurements.get('chest_cm')
                    g_chest = info['measurements'].get('chest')
                    u_waist = user_measurements.get('waist_cm')
                    g_waist = info['measurements'].get('waist')
                    
                    is_custom_match = True
                    has_criteria = False
                    
                    if u_chest and g_chest:
                        has_criteria = True
                        # Allow garment to be up to 15cm larger, but not smaller
                        if not (u_chest <= g_chest <= u_chest + 15):
                            is_custom_match = False
                    
                    if u_waist and g_waist:
                        has_criteria = True
                        if not (u_waist <= g_waist <= u_waist + 15):
                            is_custom_match = False
                            
                    if has_criteria and is_custom_match:
                        is_match = True
                
                # 2. Standard Size Match (Fallback or if no custom measurements)
                if not is_match and size_filter:
                    if info['size'] == size_filter or info['size'] == 'OS':
                        is_match = True
                
                # 3. No filter or "All"
                if not is_match and (not size_filter or size_filter == 'All'):
                    is_match = True
                    
                if is_match:
                    garments.append({
                        'filename': f, 
                        'size': info['size'],
                        'category': info.get('category', 'Unknown'),
                        'measurements': info.get('measurements')
                    })
                    
    return garments

@app.route('/studio')
def studio():
    garment_filename = request.args.get('garment_image')
    if not garment_filename:
        flash('Please select a garment first.')
        return redirect(url_for('select_garments'))

    metadata = load_garment_metadata()
    
    # Get current garment info
    current_garment = metadata.get(garment_filename, {})
    current_garment['filename'] = garment_filename
    
    # If current garment doesn't have price/material (old dummy), use first real garment instead
    if 'price' not in current_garment or 'material' not in current_garment:
        for f, info in metadata.items():
            if 'price' in info and 'material' in info:
                current_garment = info.copy()
                current_garment['filename'] = f
                garment_filename = f
                break

    # Get all garments for the switcher (only those with price and material)
    all_garments = []
    for f, info in metadata.items():
        # Only include garments that have price and material (real downloaded images)
        if 'price' in info and 'material' in info:
            info['filename'] = f
            all_garments.append(info)

    return render_template('studio.html',
                           current_garment=current_garment,
                           all_garments=all_garments)

@app.route('/studio2')
def studio2():
    """AR Studio 2 - Real-time AR effects using Snap Camera Kit"""
    return render_template('studio2.html')

@app.route('/studio3')
def studio3():
    """AR Studio 3 - Real-time AI transformations using DecartAI Realtime API"""
    api_key = os.environ.get('DECART_API_KEY', '')
    return render_template('studio3.html', api_key=api_key)

@app.route('/studio3-test')
def studio3_test():
    """Test page for Studio 3 - Simple interface for testing DecartAI"""
    return app.send_static_file('studio3-test.html')

@app.route('/api_virtual_try_on', methods=['POST'])
def api_virtual_try_on():
    """Virtual try-on using API4AI API"""
    user_image_name = request.form.get('user_image')
    garment_image_name = request.form.get('garment_image')
    
    if not user_image_name or not garment_image_name:
        return jsonify({'error': 'Missing user_image or garment_image'}), 400
    
    # Get file paths
    user_path = os.path.join(USER_UPLOAD_FOLDER, user_image_name)
    garment_path = os.path.join(GARMENT_UPLOAD_FOLDER, garment_image_name)
    
    if not os.path.exists(user_path) or not os.path.exists(garment_path):
        return jsonify({'error': 'Image files not found'}), 404
    
    try:
        # Prepare files for API4AI
        files = {
            'image': open(user_path, 'rb'),
            'image-apparel': open(garment_path, 'rb')
        }
        
        headers = {
            'X-API-KEY': API4AI_API_KEY
        }
        
        # Call API4AI
        response = requests.post(API4AI_URL, headers=headers, files=files)
        
        # Close files
        files['image'].close()
        files['image-apparel'].close()
        
        # Debug: log response
        print(f"API4AI Response Status: {response.status_code}")
        print(f"API4AI Response Headers: {response.headers.get('content-type')}")
        print(f"API4AI Response (first 500 chars): {response.text[:500]}")
        
        if response.status_code != 200:
            return jsonify({'error': f'API error: {response.status_code}', 'details': response.text}), 500
        
        # Parse response
        result = response.json()
        
        if 'results' not in result or len(result['results']) == 0:
            return jsonify({'error': 'No results returned from API'}), 500
        
        # Extract the base64 image
        result_data = result['results'][0]
        entities = result_data.get('entities', [])
        
        person_in_apparel = None
        for entity in entities:
            if entity.get('kind') == 'image' and entity.get('name') == 'person-in-apparel':
                person_in_apparel = entity
                break
        
        if not person_in_apparel:
            return jsonify({'error': 'No person-in-apparel result found'}), 500
        
        # Decode base64 image
        image_data = base64.b64decode(person_in_apparel['image'])
        
        # Save result
        result_filename = f"api_result_{int(time.time())}_{user_image_name}"
        result_path = os.path.join(RESULTS_FOLDER, result_filename)
        
        with open(result_path, 'wb') as f:
            f.write(image_data)
        
        return jsonify({
            'success': True,
            'result_image': result_filename,
            'width': result_data.get('width'),
            'height': result_data.get('height')
        })
        
    except Exception as e:
        return jsonify({'error': f'Processing error: {str(e)}'}), 500

@app.route('/try_on', methods=['POST'])
def try_on():
    user_image_name = request.form.get('user_image')
    garment_image_name = request.form.get('garment_image')
    
    if not user_image_name or not garment_image_name:
        flash('Selection missing. Please ensure you have captured your photo and selected a garment.')
        return redirect(url_for('demo'))

    # Simulation Logic
    time.sleep(2) # Realistic processing delay
    
    src_user = os.path.join(USER_UPLOAD_FOLDER, user_image_name)
    src_garment = os.path.join(GARMENT_UPLOAD_FOLDER, garment_image_name)
    
    # Check if files exist
    if not os.path.exists(src_user) or not os.path.exists(src_garment):
         flash('Session or garment data lost. Please try again.')
         return redirect(url_for('demo'))
         
    # Simple Dummy Processing using OpenCV
    try:
        user_img = cv2.imread(src_user)
        # Load garment with alpha channel if possible
        garment_img = cv2.imread(src_garment, cv2.IMREAD_UNCHANGED)
        
        if user_img is None or garment_img is None:
            raise Exception("Could not read images")

        # 1. Resize garment to be roughly 40% of user image width
        h_u, w_u = user_img.shape[:2]
        target_w = int(w_u * 0.45) # Slightly larger
        
        # Check if garment has alpha
        has_alpha = False
        if garment_img.shape[2] == 4:
            has_alpha = True
            aspect = garment_img.shape[0] / garment_img.shape[1]
        else:
            aspect = garment_img.shape[0] / garment_img.shape[1]
            
        target_h = int(target_w * aspect)
        
        garment_resized = cv2.resize(garment_img, (target_w, target_h))
        
        # 2. Naive placement: Centered horizontally, 22% down from top
        x_offset = (w_u - target_w) // 2
        y_offset = int(h_u * 0.22)
        
        # 3. Overlay with Alpha Blending
        h_g, w_g = garment_resized.shape[:2]
        
        # Clip to user image boundaries
        y1, y2 = y_offset, y_offset + h_g
        x1, x2 = x_offset, x_offset + w_g
        
        y1_g, y2_g = 0, h_g
        x1_g, x2_g = 0, w_g
        
        # Boundary checks
        if y1 < 0:
            y1_g = -y1
            y1 = 0
        if y2 > h_u:
            y2_g = h_g - (y2 - h_u)
            y2 = h_u
        if x1 < 0:
            x1_g = -x1
            x1 = 0
        if x2 > w_u:
            x2_g = w_g - (x2 - w_u)
            x2 = w_u

        if y2 > y1 and x2 > x1:
            # Region of interest on user image
            roi = user_img[y1:y2, x1:x2]
            # Region of garment
            garment_crop = garment_resized[y1_g:y2_g, x1_g:x2_g]
            
            if has_alpha:
                # Extract alpha channel
                alpha = garment_crop[:, :, 3] / 255.0
                alpha = np.stack([alpha]*3, axis=2) # 3 channels
                
                # Extract BGR channels
                garment_bgr = garment_crop[:, :, :3]
                
                # Blend
                weighted_garment = garment_bgr * alpha
                weighted_user = roi * (1.0 - alpha)
                
                dst = cv2.add(weighted_garment, weighted_user)
                user_img[y1:y2, x1:x2] = dst
            else:
                # Fallback to white background removal mask
                gray_g = cv2.cvtColor(garment_crop, cv2.COLOR_BGR2GRAY)
                _, mask = cv2.threshold(gray_g, 240, 255, cv2.THRESH_BINARY_INV)
                
                img1_bg = cv2.bitwise_and(roi, roi, mask=cv2.bitwise_not(mask))
                img2_fg = cv2.bitwise_and(garment_crop, garment_crop, mask=mask)
                
                dst = cv2.add(img1_bg, img2_fg)
                user_img[y1:y2, x1:x2] = dst

        # Add watermark
        cv2.putText(user_img, "ARmira TRY-ON GENERATED", (20, h_u - 20), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        
        # Save result
        result_filename = f"result_{int(time.time())}_{user_image_name}"
        cv2.imwrite(os.path.join(RESULTS_FOLDER, result_filename), user_img)
        
        # Generate random AI fit analysis with basic logic
        import random
        
        # Get sizes to compare
        user_size = session.get('size_category', 'M')
        
        # Get garment size
        metadata = load_garment_metadata()
        garment_info = metadata.get(garment_image_name, {})
        garment_size = garment_info.get('size', 'M')
        
        size_map = {'S': 1, 'M': 2, 'L': 3, 'XL': 4, 'Custom': 2, 'OS': 2, 'Unknown': 2}
        
        u_val = size_map.get(user_size, 2)
        g_val = size_map.get(garment_size, 2)
        
        diff = u_val - g_val
        
        if diff == 0:
            fit_score = random.randint(90, 99)
            recommendation = random.choice(['Perfect fit!', 'Matches your body type well.', 'True to size.'])
            tension = 'None'
            drape = 'Excellent'
        elif diff > 0:
            # User is bigger than garment
            fit_score = random.randint(60, 75)
            recommendation = 'Might be too tight. Consider sizing up.'
            tension = 'High (Chest/Waist)'
            drape = 'Stretched'
        else:
            # User is smaller than garment
            fit_score = random.randint(70, 85)
            recommendation = 'Loose fit. Consider sizing down for a snugger look.'
            tension = 'Low'
            drape = 'Loose'
            
        fit_metrics = {
            'fit_score': fit_score,
            'drape_quality': drape,
            'tension_map': tension,
            'recommendation': recommendation
        }
        
        return render_template('result.html', result_image=result_filename, analysis=fit_metrics)

    except Exception as e:
        flash(f'Processing error: {str(e)}')
        return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
