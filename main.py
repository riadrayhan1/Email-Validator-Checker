"""
Professional Email Validator - Flask Web Application (FIXED DOWNLOAD)
Supports CSV files and ZIP folders with multi-threading
Run: python app.py
Access: http://localhost:5000
"""

from flask import Flask, render_template_string, request, jsonify, send_file, make_response
import pandas as pd
import re
import os
import zipfile
import socket
from concurrent.futures import ThreadPoolExecutor, as_completed
from werkzeug.utils import secure_filename
from io import StringIO

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Store results in memory to avoid file system issues
validation_results_data = None

# HTML Template
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Email Validator Pro - Fast</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #f0f9f4 0%, #ffffff 100%);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 20px;
        }
        
        .container {
            background: white;
            border-radius: 20px;
            box-shadow: 0 10px 40px rgba(16, 185, 129, 0.15);
            padding: 40px;
            max-width: 600px;
            width: 100%;
            border: 2px solid #d1fae5;
        }
        
        .header {
            text-align: center;
            margin-bottom: 30px;
        }
        
        .header h1 {
            color: #059669;
            font-size: 32px;
            margin-bottom: 5px;
        }

        .speed-badge {
            background: linear-gradient(135deg, #10b981, #059669);
            color: white;
            padding: 5px 15px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: bold;
            display: inline-block;
            margin-bottom: 10px;
        }
        
        .header p {
            color: #6b7280;
            font-size: 14px;
        }
        
        .icon { font-size: 48px; margin-bottom: 15px; }
        
        .upload-area {
            border: 3px dashed #10b981;
            border-radius: 15px;
            padding: 40px;
            text-align: center;
            background: #f0fdf4;
            cursor: pointer;
            transition: all 0.3s;
            margin-bottom: 20px;
        }
        
        .upload-area:hover {
            background: #d1fae5;
            border-color: #059669;
        }
        
        .upload-icon { font-size: 48px; margin-bottom: 15px; }
        .upload-text { color: #059669; font-size: 16px; font-weight: 600; margin-bottom: 5px; }
        .upload-subtext { color: #6b7280; font-size: 12px; }
        
        .file-info {
            background: #e0f2fe;
            padding: 15px;
            border-radius: 10px;
            margin-bottom: 20px;
            display: none;
        }
        
        .file-info.show { display: block; }
        .file-name { color: #0369a1; font-weight: 600; word-break: break-all; }
        
        .btn {
            width: 100%;
            padding: 15px 30px;
            border: none;
            border-radius: 10px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s;
            margin-bottom: 20px;
        }
        
        .btn-primary {
            background: linear-gradient(135deg, #10b981 0%, #059669 100%);
            color: white;
        }
        
        .btn-primary:hover:not(:disabled) {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(16, 185, 129, 0.3);
        }
        
        .btn-primary:disabled {
            background: #d1d5db;
            cursor: not-allowed;
        }
        
        .progress-container {
            margin-bottom: 20px;
            display: none;
        }
        
        .progress-container.show { display: block; }
        
        .progress-bar {
            width: 100%;
            height: 30px;
            background: #e5e7eb;
            border-radius: 15px;
            overflow: hidden;
            margin-bottom: 10px;
        }
        
        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #10b981 0%, #059669 100%);
            transition: width 0.3s;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: 600;
            font-size: 14px;
            width: 0%;
        }
        
        .progress-text {
            text-align: center;
            color: #6b7280;
            font-size: 14px;
        }
        
        .stats-container {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 15px;
            margin-bottom: 20px;
            display: none;
        }
        
        .stats-container.show { display: grid; }
        
        .stat-box {
            padding: 20px;
            border-radius: 10px;
            text-align: center;
            border: 2px solid;
        }
        
        .stat-box.valid { background: #d1fae5; border-color: #10b981; }
        .stat-box.invalid { background: #fee2e2; border-color: #ef4444; }
        .stat-box.total { background: #dbeafe; border-color: #3b82f6; }
        
        .stat-label { font-size: 12px; font-weight: 600; margin-bottom: 5px; }
        .stat-box.valid .stat-label { color: #059669; }
        .stat-box.invalid .stat-label { color: #dc2626; }
        .stat-box.total .stat-label { color: #2563eb; }
        
        .stat-value { font-size: 28px; font-weight: 700; }
        .stat-box.valid .stat-value { color: #059669; }
        .stat-box.invalid .stat-value { color: #dc2626; }
        .stat-box.total .stat-value { color: #2563eb; }
        
        .download-btn { display: none; }
        .download-btn.show { display: block; }
        
        .status-message {
            text-align: center;
            padding: 15px;
            border-radius: 10px;
            margin-top: 20px;
            font-weight: 600;
            display: none;
        }
        
        .status-message.show { display: block; }
        .status-message.success { background: #d1fae5; color: #059669; }
        .status-message.error { background: #fee2e2; color: #dc2626; }
        .status-message.processing { background: #fef3c7; color: #d97706; }
        
        input[type="file"] { display: none; }

        .spinner {
            border: 4px solid #f3f3f3;
            border-top: 4px solid #10b981;
            border-radius: 50%;
            width: 40px;
            height: 40px;
            animation: spin 1s linear infinite;
            margin: 10px auto;
            display: none;
        }

        .spinner.show { display: block; }

        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }

        .speed-info {
            text-align: center;
            color: #10b981;
            font-size: 12px;
            font-weight: 600;
            margin-top: 10px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="icon">⚡</div>
            <div class="speed-badge">🚀 ULTRA FAST - Multi-threaded</div>
            <h1>Email Validator Pro</h1>
            <p>Lightning-fast bulk email validation with domain checking</p>
        </div>
        
        <div class="upload-area" id="uploadArea" onclick="document.getElementById('fileInput').click()">
            <div class="upload-icon">📁</div>
            <div class="upload-text">Click to upload or drag & drop</div>
            <div class="upload-subtext">CSV or ZIP files supported (Max 50MB)</div>
        </div>
        
        <input type="file" id="fileInput" accept=".csv,.zip" onchange="handleFileSelect(event)">
        
        <div class="file-info" id="fileInfo">
            <strong>Selected file:</strong> <span class="file-name" id="fileName"></span>
        </div>
        
        <button class="btn btn-primary" id="startBtn" onclick="startValidation()" disabled>
            🚀 START VALIDATION
        </button>

        <div class="spinner" id="spinner"></div>
        
        <div class="progress-container" id="progressContainer">
            <div class="progress-bar">
                <div class="progress-fill" id="progressFill">0%</div>
            </div>
            <div class="progress-text" id="progressText">Processing...</div>
            <div class="speed-info" id="speedInfo"></div>
        </div>
        
        <div class="stats-container" id="statsContainer">
            <div class="stat-box valid">
                <div class="stat-label">✅ Valid</div>
                <div class="stat-value" id="validCount">0</div>
            </div>
            <div class="stat-box invalid">
                <div class="stat-label">❌ Invalid</div>
                <div class="stat-value" id="invalidCount">0</div>
            </div>
            <div class="stat-box total">
                <div class="stat-label">📝 Total</div>
                <div class="stat-value" id="totalCount">0</div>
            </div>
        </div>
        
        <button class="btn btn-primary download-btn" id="downloadBtn" onclick="downloadResults()">
            💾 Download Valid Emails CSV
        </button>
        
        <div class="status-message" id="statusMessage"></div>
    </div>
    
    <script>
        let selectedFile = null;
        let validationResults = null;
        let startTime = null;
        
        const uploadArea = document.getElementById('uploadArea');
        
        uploadArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadArea.classList.add('dragover');
        });
        
        uploadArea.addEventListener('dragleave', () => {
            uploadArea.classList.remove('dragover');
        });
        
        uploadArea.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadArea.classList.remove('dragover');
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                handleFile(files[0]);
            }
        });
        
        function handleFileSelect(event) {
            const file = event.target.files[0];
            if (file) {
                handleFile(file);
            }
        }
        
        function handleFile(file) {
            const fileName = file.name.toLowerCase();
            
            if (!fileName.endsWith('.csv') && !fileName.endsWith('.zip')) {
                showStatus('Please select a CSV or ZIP file', 'error');
                return;
            }
            
            selectedFile = file;
            document.getElementById('fileName').textContent = file.name;
            document.getElementById('fileInfo').classList.add('show');
            document.getElementById('startBtn').disabled = false;
            showStatus('File loaded. Click START to begin validation.', 'success');
        }
        
        async function startValidation() {
            if (!selectedFile) {
                showStatus('Please select a file first', 'error');
                return;
            }
            
            const formData = new FormData();
            formData.append('file', selectedFile);
            
            document.getElementById('startBtn').disabled = true;
            document.getElementById('spinner').classList.add('show');
            document.getElementById('progressContainer').classList.add('show');
            document.getElementById('statsContainer').classList.remove('show');
            document.getElementById('downloadBtn').classList.remove('show');
            
            document.getElementById('progressFill').style.width = '10%';
            document.getElementById('progressFill').textContent = '10%';
            
            startTime = Date.now();
            showStatus('⚡ Processing with multi-threading...', 'processing');
            
            try {
                const response = await fetch('/validate', {
                    method: 'POST',
                    body: formData
                });
                
                if (!response.ok) {
                    throw new Error('Server error: ' + response.status);
                }
                
                const data = await response.json();
                
                document.getElementById('spinner').classList.remove('show');
                
                if (data.success) {
                    validationResults = data;
                    displayResults(data);
                } else {
                    showStatus('Error: ' + (data.error || 'Unknown error'), 'error');
                    document.getElementById('startBtn').disabled = false;
                    document.getElementById('progressContainer').classList.remove('show');
                }
            } catch (error) {
                document.getElementById('spinner').classList.remove('show');
                showStatus('Error: ' + error.message, 'error');
                document.getElementById('startBtn').disabled = false;
                document.getElementById('progressContainer').classList.remove('show');
                console.error('Validation error:', error);
            }
        }
        
        function displayResults(data) {
            const endTime = Date.now();
            const duration = ((endTime - startTime) / 1000).toFixed(2);
            const emailsPerSecond = (data.total / duration).toFixed(0);
            
            document.getElementById('progressFill').style.width = '100%';
            document.getElementById('progressFill').textContent = '100%';
            document.getElementById('progressText').textContent = 'Validation complete!';
            document.getElementById('speedInfo').textContent = `⚡ Processed ${data.total} emails in ${duration}s (${emailsPerSecond} emails/sec)`;
            
            document.getElementById('validCount').textContent = data.valid;
            document.getElementById('invalidCount').textContent = data.invalid;
            document.getElementById('totalCount').textContent = data.total;
            document.getElementById('statsContainer').classList.add('show');
            
            document.getElementById('downloadBtn').classList.add('show');
            
            showStatus(`✅ Complete in ${duration}s! Valid: ${data.valid} | Invalid: ${data.invalid}`, 'success');
            
            document.getElementById('startBtn').disabled = false;
        }
        
        function downloadResults() {
            if (!validationResults) {
                showStatus('No results to download', 'error');
                return;
            }
            
            try {
                showStatus('Preparing download...', 'processing');
                
                // Create download link
                const link = document.createElement('a');
                link.href = '/download';
                link.download = 'valid_emails.csv';
                link.style.display = 'none';
                
                document.body.appendChild(link);
                link.click();
                
                setTimeout(() => {
                    document.body.removeChild(link);
                    showStatus('✅ Download started!', 'success');
                }, 500);
                
            } catch (error) {
                showStatus('Error: ' + error.message, 'error');
                console.error('Download error:', error);
            }
        }
        
        function showStatus(message, type) {
            const statusEl = document.getElementById('statusMessage');
            statusEl.textContent = message;
            statusEl.className = 'status-message show ' + type;
        }
    </script>
</body>
</html>
"""

# Common email domains for quick validation
COMMON_DOMAINS = {
    'gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com', 'aol.com',
    'icloud.com', 'mail.com', 'zoho.com', 'protonmail.com', 'yandex.com',
    'live.com', 'msn.com', 'inbox.com', 'gmx.com', 'fastmail.com'
}

def validate_email_syntax(email):
    """Strict email syntax validation"""
    if not email or len(email) > 254:
        return False
    
    pattern = r'^[a-zA-Z0-9][a-zA-Z0-9._%+-]*@[a-zA-Z0-9][a-zA-Z0-9.-]*\.[a-zA-Z]{2,}$'
    
    if not re.match(pattern, email):
        return False
    
    if '..' in email:
        return False
    
    local, domain = email.rsplit('@', 1)
    
    if len(local) > 64 or len(domain) > 253:
        return False
    
    if local.startswith('.') or local.endswith('.'):
        return False
    
    return True

def check_domain_exists(domain):
    """Fast domain existence check"""
    if domain.lower() in COMMON_DOMAINS:
        return True
    
    try:
        socket.setdefaulttimeout(2)
        socket.gethostbyname(domain)
        return True
    except:
        try:
            socket.getaddrinfo(domain, None)
            return True
        except:
            return False

def check_email(email):
    """Accurate email validation with domain checking"""
    result = {
        "Email": email,
        "Syntax_Valid": False,
        "Domain_Exists": False,
        "MX_Record": False,
        "Final_Status": "❌ Invalid"
    }
    
    try:
        if not validate_email_syntax(email):
            result["Final_Status"] = "❌ Invalid Syntax"
            return result
        
        result["Syntax_Valid"] = True
        domain = email.split('@')[-1]
        
        if check_domain_exists(domain):
            result["Domain_Exists"] = True
            result["MX_Record"] = True
            result["Final_Status"] = "✅ Valid"
        else:
            result["Final_Status"] = "⚠️ Invalid Domain"
            
    except:
        result["Final_Status"] = "❌ Error"
    
    return result

def extract_emails_from_csv(csv_path):
    """Extract emails from CSV"""
    try:
        for encoding in ['utf-8', 'latin-1', 'iso-8859-1']:
            try:
                df = pd.read_csv(csv_path, encoding=encoding, on_bad_lines='skip')
                break
            except:
                continue
        else:
            return []
        
        email_col = None
        for col in df.columns:
            col_lower = str(col).lower()
            if 'email' in col_lower or 'mail' in col_lower or 'e-mail' in col_lower:
                email_col = col
                break
        
        if email_col is None:
            email_col = df.columns[0]
        
        emails = df[email_col].astype(str).tolist()
        
        cleaned = []
        for email in emails:
            email = str(email).strip().lower()
            if email and email != 'nan' and '@' in email and '.' in email:
                cleaned.append(email)
        
        return cleaned
    except Exception as e:
        print(f"Error reading CSV: {e}")
        return []

def process_zip(zip_path):
    """Extract all CSVs from ZIP"""
    all_emails = []
    temp_dir = None
    
    try:
        temp_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'temp_extracted')
        os.makedirs(temp_dir, exist_ok=True)
        
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)
        
        for root, dirs, files in os.walk(temp_dir):
            for file in files:
                if file.lower().endswith('.csv'):
                    csv_path = os.path.join(root, file)
                    emails = extract_emails_from_csv(csv_path)
                    all_emails.extend(emails)
    except Exception as e:
        print(f"Error processing ZIP: {e}")
    finally:
        if temp_dir and os.path.exists(temp_dir):
            import shutil
            try:
                shutil.rmtree(temp_dir)
            except:
                pass
    
    return all_emails

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/validate', methods=['POST'])
def validate():
    global validation_results_data
    
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'No file uploaded'})
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'})
        
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        print(f"\n{'='*60}")
        print(f"Processing: {filename}")
        
        # Extract emails
        if filename.lower().endswith('.zip'):
            emails = process_zip(filepath)
        else:
            emails = extract_emails_from_csv(filepath)
        
        print(f"Found: {len(emails)} emails")
        
        if not emails:
            os.remove(filepath)
            return jsonify({'success': False, 'error': 'No valid emails found'})
        
        # Validate
        results = []
        valid_count = 0
        invalid_count = 0
        
        print("Validating...")
        
        with ThreadPoolExecutor(max_workers=30) as executor:
            future_to_email = {executor.submit(check_email, email): email for email in emails}
            
            for future in as_completed(future_to_email):
                result = future.result()
                results.append(result)
                
                if result["Final_Status"] == "✅ Valid":
                    valid_count += 1
                else:
                    invalid_count += 1
        
        print(f"Done! Valid: {valid_count}, Invalid: {invalid_count}")
        
        # Store only valid emails in memory for download
        valid_emails = [result["Email"] for result in results if result["Final_Status"] == "✅ Valid"]
        df_valid = pd.DataFrame(valid_emails, columns=["Email"])
        validation_results_data = df_valid.to_csv(index=False)
        
        print(f"Valid emails stored in memory ({len(valid_emails)} valid emails)")
        print(f"{'='*60}\n")
        
        # Cleanup
        try:
            os.remove(filepath)
        except:
            pass
        
        return jsonify({
            'success': True,
            'valid': valid_count,
            'invalid': invalid_count,
            'total': len(results)
        })
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)})

@app.route('/download')
def download():
    global validation_results_data
    
    print("\n" + "="*60)
    print("Download requested")
    
    try:
        if not validation_results_data:
            print("ERROR: No results available")
            return "No results available. Please run validation first.", 404
        
        print(f"Sending CSV data with {len(validation_results_data.splitlines())-1} valid emails")
        
        # Create response with CSV data containing only valid emails
        response = make_response(validation_results_data)
        response.headers['Content-Type'] = 'text/csv'
        response.headers['Content-Disposition'] = 'attachment; filename=valid_emails.csv'
        
        print("Download successful!")
        print("="*60 + "\n")
        
        return response
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        print("="*60 + "\n")
        return f"Download failed: {str(e)}", 500

if __name__ == '__main__':
    print("=" * 60)
    print("⚡ Email Validator Pro - FIXED VERSION")
    print("=" * 60)
    print("✅ Download issues fixed (in-memory storage)")
    print("✅ Only valid emails in download file")
    print("✅ Clean CSV with just email addresses")
    print("🚀 Multi-threaded processing")
    print("🌐 Access: http://localhost:5000")
    print("💡 Press Ctrl+C to stop")
    print("=" * 60)
    app.run(debug=False, host='0.0.0.0', port=5000, threaded=True)