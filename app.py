from flask import Flask, request, redirect, render_template, flash
import boto3
from botocore.exceptions import NoCredentialsError, ClientError
import os
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configuration
S3_BUCKET = 'alteam-s3-bucket'  # Your bucket name
S3_REGION = 'us-east-1'
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'jpeg'}
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'D/qi9GfnHMnUGaQY6g9xU5G+Z79FnvaxMJE0T8ee')
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE

# Initialize S3 client with explicit credentials
try:
    s3 = boto3.client(
        's3',
        region_name=S3_REGION,
        aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY'),
        config=boto3.session.Config(signature_version='s3v4')
    )
except Exception as e:
    print(f"Error initializing S3 client: {str(e)}")
    raise

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    try:
        objects = s3.list_objects_v2(Bucket=S3_BUCKET)
        files = []
        if 'Contents' in objects:
            for obj in objects['Contents']:
                url = f"https://{S3_BUCKET}.s3.{S3_REGION}.amazonaws.com/{obj['Key']}"
                files.append((obj['Key'], url))
        return render_template('index.html', files=files)
    except ClientError as e:
        flash(f"❌ Error accessing S3: {e.response['Error']['Message']}", "danger")
        return render_template('index.html', files=[])
    except Exception as e:
        flash(f"❌ Unexpected error: {str(e)}", "danger")
        return render_template('index.html', files=[])

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        flash("❌ No file part in the request.", "danger")
        return redirect('/')

    file = request.files['file']
    
    if file.filename == '':
        flash("❌ No selected file.", "danger")
        return redirect('/')

    if not allowed_file(file.filename):
        flash("❌ File type not allowed.", "danger")
        return redirect('/')

    try:
        # Secure the filename to prevent directory traversal attacks
        filename = secure_filename(file.filename)
        s3.upload_fileobj(
            file,
            S3_BUCKET,
            filename,
            ExtraArgs={
                'ACL': 'private',  # Set appropriate permissions
                'ContentType': file.content_type  # Preserve original content type
            }
        )
        flash(f"✅ File '{filename}' uploaded successfully!", "success")
    except ClientError as e:
        flash(f"❌ Upload failed: {e.response['Error']['Message']}", "danger")
    except Exception as e:
        flash(f"❌ Unexpected error: {str(e)}", "danger")
    
    return redirect('/')

@app.route('/delete', methods=['POST'])
def delete_file():
    if 'filename' not in request.form:
        flash("❌ No filename specified.", "danger")
        return redirect('/')

    filename = request.form['filename']
    
    try:
        s3.delete_object(Bucket=S3_BUCKET, Key=filename)
        flash(f"🗑️ File '{filename}' deleted successfully!", "warning")
    except ClientError as e:
        flash(f"❌ Delete failed: {e.response['Error']['Message']}", "danger")
    except Exception as e:
        flash(f"❌ Unexpected error: {str(e)}", "danger")
    
    return redirect('/')

@app.route('/download/<filename>')
def download_file(filename):
    try:
        # Generate a presigned URL for the file (valid for 1 hour)
        url = s3.generate_presigned_url(
            'get_object',
            Params={
                'Bucket': S3_BUCKET,
                'Key': filename
            },
            ExpiresIn=3600
        )
        return redirect(url)
    except ClientError as e:
        flash(f"❌ Download failed: {e.response['Error']['Message']}", "danger")
        return redirect('/')
    except Exception as e:
        flash(f"❌ Unexpected error: {str(e)}", "danger")
        return redirect('/')

@app.route('/preview/<filename>')
def preview_file(filename):
    try:
        # Check if file is an image
        if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
            url = f"https://{S3_BUCKET}.s3.{S3_REGION}.amazonaws.com/{filename}"
            return render_template('preview.html', image_url=url)
        else:
            flash("❌ File type cannot be previewed.", "danger")
            return redirect('/')
    except Exception as e:
        flash(f"❌ Preview failed: {str(e)}", "danger")
        return redirect('/')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
