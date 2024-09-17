from flask import Flask, render_template, request, redirect, jsonify, send_from_directory, url_for
from core.prepocessing import allowed_file, process_excel, processing_status
from layout.baseUtils import delete_excel_folder, folders, logs_to_json
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
import urllib.parse
import threading
import os

load_dotenv()
app = Flask(__name__)

excel_folder = os.getenv('EXCEL_FOLDER')
doc_template = os.getenv('DOC_TEMPLATE')
folder_to_delete = None


@app.route('/', methods=['GET', 'POST'])
def index():
    return render_template('home.html')


@app.route('/contracts', methods=['GET', 'POST'])
def contract_page():
    return render_template('contracts.html')


@app.route('/templates/list')
def list_templates():
    template_list = [
        os.path.splitext(f)[0]
        for f in os.listdir(doc_template)
        if os.path.isfile(os.path.join(doc_template, f))
    ]
    return jsonify(template_list)


def create_template_folder():
    if not os.path.exists(doc_template):
        try:
            os.makedirs(doc_template)
        except Exception as e:
            logs_to_json('create_template_folder', 'create_template_folder', str(e))


@app.route('/templates')
def templates():
    try:
        create_template_folder()
        files = os.listdir(doc_template)

        page = request.args.get('page', 1, type=int)
        per_page = 5
        total_files = len(files)

        start = (page - 1) * per_page
        end = start + per_page
        files_on_page = files[start:end]

        has_prev = page > 1
        has_next = end < total_files

        return render_template('templates.html', files=files_on_page, page=page, has_prev=has_prev, has_next=has_next)
    except Exception as e:
        logs_to_json('templates_function', 'templates', str(e))


@app.route('/download/<filename>')
def download_file(filename):
    # Download file from the 'doc_template' folder
    return send_from_directory(doc_template, filename, as_attachment=True)


@app.route('/delete/<filename>', methods=['POST'])
def delete_file(filename):
    # Delete file from the 'doc_template' folder
    file_path = os.path.join(doc_template, filename)
    if os.path.exists(file_path):
        os.remove(file_path)
    return redirect(url_for('templates'))


@app.route('/add-template', methods=['POST'])
def add_template():
    # Handle file upload
    if 'file' not in request.files:
        return redirect(url_for('templates'))

    file = request.files['file']
    if file.filename != '':
        file.save(os.path.join(doc_template, file.filename))
    return redirect(url_for('templates'))


@app.route('/upload', methods=['POST'])
def upload_file():
    try:
        global processing_status
        global folder_to_delete
        if 'file' not in request.files or 'template' not in request.form:
            return redirect(request.url)

        file = request.files['file']
        selected_template = request.form['template']

        if file.filename == '':
            return redirect(request.url)

        if file and allowed_file(file.filename):
            name, _ = os.path.splitext(file.filename)
            folder_to_delete = name
            encoded_filename = urllib.parse.quote(file.filename)
            filename = secure_filename(encoded_filename)
            file_path = str(folders(excel_folder, filename, name))
            file.save(file_path)

            processing_status['status'] = 'Processing started'
            processing_status['total_files'] = 0
            processing_status['processed_files'] = 0
            threading.Thread(target=process_excel, args=(file_path, name, selected_template)).start()

            return redirect('/status')

        return redirect(request.url)
    except Exception as e:
        logs_to_json('upload_file', 'upload_file', str(e))


@app.route('/status')
def status():
    try:
        if processing_status['status'] == 'Договоры созданы успешно!':
            delete_excel_folder(folder_to_delete)
        return jsonify(processing_status)
    except Exception as e:
        logs_to_json('status', 'status', str(e))


if __name__ == '__main__':
    app.run(port=5656)
