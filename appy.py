from flask import Flask, render_template, request, send_file, jsonify
from PIL import Image
import io
import math
import os
import traceback
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max file size
app.config['UPLOAD_FOLDER'] = '/tmp/uploads'

# Create upload folder if it doesn't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'tif', 'tiff'}

# --- Health & diagnostics (from ChatGPT's working code) ---
@app.route("/health")
def health():
    return {"status": "ok"}, 200

# --- Global error handler: print full trace to logs (from ChatGPT) ---
@app.errorhandler(Exception)
def handle_any_error(e):
    traceback.print_exc()
    return {"error": "Internal Server Error", "detail": str(e)}, 500

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generate', methods=['POST'])
def generate_panels():
    try:
        if 'pattern' not in request.files:
            return jsonify({'error': 'No pattern file uploaded'}), 400
        
        file = request.files['pattern']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'error': 'Invalid file type. Use PNG, JPG, or TIFF'}), 400
        
        # Get parameters
        wall_width = float(request.form.get('wall_width', 120))
        wall_height = float(request.form.get('wall_height', 96))
        panel_width = float(request.form.get('panel_width', 50))
        dpi = int(request.form.get('dpi', 150))
        overlap = float(request.form.get('overlap', 2))
        
        # Load pattern image
        pattern_img = Image.open(file.stream)
        pattern_width, pattern_height = pattern_img.size
        
        # Calculate pixels per inch from pattern
        pattern_ppi_width = pattern_width / wall_width
        pattern_ppi_height = pattern_height / wall_height
        
        # Calculate panel dimensions in pixels
        panel_width_px = int(panel_width * dpi)
        panel_height_px = int(wall_height * dpi)
        overlap_px = int(overlap * dpi)
        
        # Calculate number of panels needed
        effective_panel_width = panel_width - overlap
        num_panels = math.ceil(wall_width / effective_panel_width)
        
        # Scale pattern to target DPI
        scale_factor = dpi / pattern_ppi_width
        scaled_width = int(pattern_width * scale_factor)
        scaled_height = int(pattern_height * scale_factor)
        scaled_pattern = pattern_img.resize((scaled_width, scaled_height), Image.Resampling.LANCZOS)
        
        # Store panels in session/temp storage
        app.config['CURRENT_PANELS'] = {
            'num_panels': num_panels,
            'scaled_pattern': scaled_pattern,
            'panel_width_px': panel_width_px,
            'panel_height_px': panel_height_px,
            'dpi': dpi,
            'effective_panel_width': effective_panel_width,
            'scaled_width': scaled_width,
            'scaled_height': scaled_height
        }
        
        return jsonify({
            'success': True,
            'num_panels': num_panels,
            'message': f'Generated {num_panels} panels successfully'
        })
    
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/download/<int:panel_num>')
def download_panel(panel_num):
    try:
        if 'CURRENT_PANELS' not in app.config:
            return jsonify({'error': 'No panels generated yet'}), 400
        
        panels_data = app.config['CURRENT_PANELS']
        
        if panel_num < 1 or panel_num > panels_data['num_panels']:
            return jsonify({'error': 'Invalid panel number'}), 400
        
        # Regenerate the specific panel
        scaled_pattern = panels_data['scaled_pattern']
        panel_width_px = panels_data['panel_width_px']
        panel_height_px = panels_data['panel_height_px']
        dpi = panels_data['dpi']
        effective_panel_width = panels_data['effective_panel_width']
        scaled_width = panels_data['scaled_width']
        scaled_height = panels_data['scaled_height']
        
        # Calculate panel position
        start_x = int((panel_num - 1) * effective_panel_width * dpi)
        
        # Create panel
        panel = Image.new('RGB', (panel_width_px, panel_height_px), 'white')
        
        # Tile pattern across panel
        x_offset = 0
        while x_offset < panel_width_px:
            y_offset = 0
            while y_offset < panel_height_px:
                # Calculate source position with wrapping
                src_x = (start_x + x_offset) % scaled_width
                src_y = y_offset % scaled_height
                
                # Calculate how much to copy
                copy_width = min(scaled_width - src_x, panel_width_px - x_offset)
                copy_height = min(scaled_height - src_y, panel_height_px - y_offset)
                
                # Copy pattern section
                section = scaled_pattern.crop((src_x, src_y, src_x + copy_width, src_y + copy_height))
                panel.paste(section, (x_offset, y_offset))
                
                y_offset += copy_height
            x_offset += copy_width
        
        # Save panel to bytes
        panel_io = io.BytesIO()
        panel.save(panel_io, 'PNG', dpi=(dpi, dpi))
        panel_io.seek(0)
        
        return send_file(
            panel_io,
            mimetype='image/png',
            as_attachment=True,
            download_name=f'panel_{panel_num:02d}.png'
        )
    
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))