import os
import uuid
import time
import logging
import threading
import subprocess
from pathlib import Path

from flask import Flask, request, send_file, jsonify, send_from_directory
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

app = Flask(__name__)
CORS(app, origins="*")

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"
)

log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

# Windows-compatible temp folders inside your project
BASE_DIR    = Path(__file__).parent
UPLOAD_DIR  = BASE_DIR / "temp" / "uploads"
OUTPUT_DIR  = BASE_DIR / "temp" / "outputs"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# LibreOffice path for Windows
LIBREOFFICE = r"C:\Program Files\LibreOffice\program\soffice.exe"

MAX_FILE_SIZE_MB = 25

ALLOWED_EXTENSIONS = {
    'pdf', 'docx', 'doc', 'pptx', 'ppt', 'xlsx', 'xls',
    'jpg', 'jpeg', 'png', 'webp', 'gif', 'html', 'htm', 'txt'
}

MIME_TYPES = {
    'pdf':  'application/pdf',
    'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'doc':  'application/msword',
    'pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    'ppt':  'application/vnd.ms-powerpoint',
    'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'jpg':  'image/jpeg',
    'jpeg': 'image/jpeg',
    'png':  'image/png',
    'gif':  'image/gif',
    'webp': 'image/webp',
    'html': 'text/html',
    'txt':  'text/plain',
}

conversion_count = 0
conversion_lock = threading.Lock()

def cleanup_old_files():
    while True:
        now = time.time()
        for folder in [UPLOAD_DIR, OUTPUT_DIR]:
            for f in folder.iterdir():
                if f.is_file() and (now - f.stat().st_mtime) > 300:
                    f.unlink(missing_ok=True)
        time.sleep(60)

threading.Thread(target=cleanup_old_files, daemon=True).start()

def get_extension(filename):
    return filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''

def is_allowed(filename):
    return get_extension(filename) in ALLOWED_EXTENSIONS

def make_safe_name(filename):
    stem = Path(filename).stem
    safe = "".join(c if c.isalnum() or c in (' ', '_', '-') else '_' for c in stem)
    return safe.strip()[:50] or "document"

def convert_with_libreoffice(input_path, output_dir, target_format):
    print(f"Running LibreOffice: {LIBREOFFICE}")
    result = subprocess.run(
        [LIBREOFFICE, "--headless", "--convert-to", target_format,
         "--outdir", str(output_dir), str(input_path)],
        capture_output=True, text=True, timeout=120
    )
    print("LibreOffice stdout:", result.stdout)
    print("LibreOffice stderr:", result.stderr)
    if result.returncode != 0:
        raise RuntimeError(f"LibreOffice failed: {result.stderr}")
    out = output_dir / f"{input_path.stem}.{target_format}"
    if not out.exists():
        raise RuntimeError("LibreOffice did not produce an output file")
    return out

def convert_pdf_to_docx(input_path, output_path):
    try:
        from pdf2docx import Converter
    except ImportError:
        raise RuntimeError("pdf2docx not installed. Run: pip install pdf2docx")
    cv = Converter(str(input_path))
    cv.convert(str(output_path))
    cv.close()
    return output_path

def convert_image_to_pdf(input_path, output_path):
    try:
        import img2pdf
    except ImportError:
        raise RuntimeError("img2pdf not installed.")
    with open(output_path, "wb") as f:
        f.write(img2pdf.convert(str(input_path)))
    return output_path

def convert_image_to_image(input_path, output_path, to_ext):
    try:
        from PIL import Image
    except ImportError:
        raise RuntimeError("Pillow not installed.")
    img = Image.open(input_path).convert("RGB")
    fmt = 'JPEG' if to_ext in ('jpg', 'jpeg') else to_ext.upper()
    img.save(output_path, format=fmt)
    return output_path

def do_convert(input_path, from_ext, to_ext):
    uid = uuid.uuid4().hex[:8]
    output_path = OUTPUT_DIR / f"converted_{uid}.{to_ext}"

    OFFICE = {'docx', 'doc', 'pptx', 'ppt', 'xlsx', 'xls'}
    IMAGES = {'jpg', 'jpeg', 'png', 'gif', 'webp'}

    if from_ext in OFFICE:
        result = convert_with_libreoffice(input_path, OUTPUT_DIR, to_ext)
        if result != output_path:
            result.rename(output_path)
        return output_path

    if from_ext == 'pdf' and to_ext in ('docx', 'doc'):
        return convert_pdf_to_docx(input_path, output_path)

    if from_ext in IMAGES and to_ext == 'pdf':
        return convert_image_to_pdf(input_path, output_path)

    if from_ext in IMAGES and to_ext in IMAGES:
        return convert_image_to_image(input_path, output_path, to_ext)

    if from_ext in ('html', 'htm', 'txt') or to_ext == 'pdf':
        result = convert_with_libreoffice(input_path, OUTPUT_DIR, to_ext)
        if result != output_path:
            result.rename(output_path)
        return output_path

    raise RuntimeError(f"Conversion from {from_ext} to {to_ext} is not supported")

@app.route('/')
def serve_index():
    return send_from_directory(str(BASE_DIR / 'static'), 'index.html')

@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory(str(BASE_DIR / 'static'), filename)

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok'})

@app.route('/stats', methods=['GET'])
def stats():
    return jsonify({'conversions': conversion_count})

@app.route('/convert', methods=['POST'])
@limiter.limit("10 per minute")
def convert_file():
    global conversion_count
    print("=== CONVERT REQUEST RECEIVED ===")

    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400

    file = request.files['file']
    target_format = request.form.get('to', '').lower().strip('.')
    print(f"Converting to: {target_format}")

    if not file.filename:
        return jsonify({'error': 'No file selected'}), 400

    if not is_allowed(file.filename):
        return jsonify({'error': 'File type not supported'}), 400

    if not target_format or target_format not in ALLOWED_EXTENSIONS:
        return jsonify({'error': 'Target format not supported'}), 400

    file_data = file.read()
    size_mb = len(file_data) / (1024 * 1024)
    if size_mb > MAX_FILE_SIZE_MB:
        return jsonify({'error': f'File too large ({size_mb:.1f}MB). Max is {MAX_FILE_SIZE_MB}MB'}), 413

    from_ext = get_extension(file.filename)
    safe_name = make_safe_name(file.filename)
    input_path = UPLOAD_DIR / f"{safe_name}_{uuid.uuid4().hex[:8]}.{from_ext}"
    input_path.write_bytes(file_data)
    del file_data

    output_path = None
    try:
        print(f"Converting {from_ext} → {target_format}")
        output_path = do_convert(input_path, from_ext, target_format)
        print(f"Success! Output: {output_path}")
    except subprocess.TimeoutExpired:
        return jsonify({'error': 'Conversion timed out'}), 504
    except RuntimeError as e:
        print(f"RuntimeError: {e}")
        return jsonify({'error': str(e)}), 500
    except Exception as e:
        print(f"Unexpected error: {e}")
        return jsonify({'error': 'Conversion failed. Please try again.'}), 500
    finally:
        input_path.unlink(missing_ok=True)

    if not output_path or not output_path.exists():
        return jsonify({'error': 'No output file produced'}), 500

    mime = MIME_TYPES.get(target_format, 'application/octet-stream')
    download_name = f"{safe_name}.{target_format}"

    response = send_file(
        output_path,
        mimetype=mime,
        as_attachment=True,
        download_name=download_name
    )

    @response.call_on_close
    def delete_output():
        if output_path:
            output_path.unlink(missing_ok=True)

    with conversion_lock:
        conversion_count += 1

    return response

@app.errorhandler(429)
def rate_limit_exceeded(e):
    return jsonify({'error': 'Too many requests. Please wait a minute.'}), 429

if __name__ == '__main__':
    print()
    print("=" * 50)
    print("  Convertly — Secure Document Converter")
    print("=" * 50)
    print(f"  Frontend  →  http://localhost:5000")
    print(f"  Uploads   →  {UPLOAD_DIR}")
    print(f"  Outputs   →  {OUTPUT_DIR}")
    print("=" * 50)
    app.run(debug=True, host='0.0.0.0', port=5000)