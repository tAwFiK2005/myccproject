from flask import Flask, request, redirect, render_template, flash
import boto3

S3_BUCKET = 'alteam-s3-bucket'#اسم البوكت بتاعك
S3_REGION = 'us-east-1'
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg'}

app = Flask(__name__)
app.secret_key = 'D/qi9GfnHMnUGaQY6g9xU5G+Z79FnvaxMJE0T8ee'
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB

s3 = boto3.client('s3', region_name=S3_REGION)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    objects = s3.list_objects_v2(Bucket=S3_BUCKET)
    files = []
    if 'Contents' in objects:
        for obj in objects['Contents']:
            url = f"https://{S3_BUCKET}.s3.{S3_REGION}.amazonaws.com/{obj['Key']}"
            files.append((obj['Key'], url))
    return render_template('index.html', files=files)

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        flash("❌ No file part in the request.", "danger")
        return redirect('/')

    file = request.files['file']
    if file.filename == '':
        flash("❌ No selected file.", "danger")
        return redirect('/')

    if file and allowed_file(file.filename):
        s3.upload_fileobj(file, S3_BUCKET, file.filename)
        flash(f"✅ File '{file.filename}' uploaded successfully!", "success")
        return redirect('/')
    else:
        flash("❌ File type not allowed.", "danger")
        return redirect('/')

@app.route('/delete', methods=['POST'])
def delete_file():
    filename = request.form['filename']
    s3.delete_object(Bucket=S3_BUCKET, Key=filename)
    flash(f"🗑️ File '{filename}' deleted successfully!", "warning")
    return redirect('/')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)