from flask import Flask, render_template, request, redirect, jsonify, send_from_directory, url_for, abort
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
doc_result = os.getenv('DOC_RESULT')
folder_to_delete = None


@app.route('/', methods=['GET', 'POST'])
def index():
    return render_template('home.html')


@app.route('/processing', methods=['GET', 'POST'])
def contract_page():
    return render_template('processing.html')


# @app.route('/processing', methods=['GET', 'POST'])
# def processing_page():
#     return render_template('processing.html')


@app.route('/templates/list')
def list_templates():
    template_list = [
        os.path.splitext(f)[0]
        for f in os.listdir(doc_template)
        if os.path.isfile(os.path.join(doc_template, f))
    ]
    return jsonify(template_list)


def create_folder_if_not_exists(path):
    if not os.path.exists(path):
        try:
            os.makedirs(path)
        except Exception as e:
            logs_to_json('create_folder_if_not_exists', 'create_folder_if_not_exists', str(e))


@app.route('/templates')
def templates():
    try:
        create_folder_if_not_exists(doc_template)
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


@app.route('/contracts', defaults={'folder': ''})
@app.route('/contracts/<path:folder>')
def contracts(folder):
    try:
        create_folder_if_not_exists(doc_result)

        folder_path = os.path.join(doc_result, folder)

        if not os.path.isdir(folder_path):
            return "Folder does not exist", 404

        items = os.listdir(folder_path)
        folders = [item for item in items if os.path.isdir(os.path.join(folder_path, item))]
        files = [item for item in items if os.path.isfile(os.path.join(folder_path, item))]

        page = request.args.get('page', 1, type=int)
        per_page = 10
        total_items = len(files)
        start = (page - 1) * per_page
        end = start + per_page
        files_on_page = files[start:end]

        has_prev = page > 1
        has_next = end < total_items

        return render_template(
            'contracts.html',
            folders=folders,
            files=files_on_page,
            page=page,
            has_prev=has_prev,
            has_next=has_next,
            current_folder=folder
        )
    except Exception as e:
        logs_to_json('contracts_function', 'contracts', str(e))
        return "An error occurred", 500


@app.route('/download/<filename>')
def download_file(filename):
    return send_from_directory(doc_template, filename, as_attachment=True)


@app.route('/download_contract/<path:filename>')
def download_contract(filename):
    try:
        file_path = os.path.join(doc_result, filename)
        directory = os.path.dirname(file_path)
        filename = os.path.basename(file_path)

        if not os.path.isfile(file_path):
            abort(404)

        return send_from_directory(directory, filename, as_attachment=True)

    except Exception as e:
        logs_to_json('download_contract_function', 'download_contract', str(e))
        abort(500)


@app.route('/delete_contract/<path:filename>', methods=['POST'])
def delete_contract(filename):
    try:
        file_path = os.path.join(doc_result, filename)
        # relative_directory = os.path.dirname(filename)

        if os.path.exists(file_path):
            os.remove(file_path)
        return redirect(url_for('contracts'))

    except Exception as e:
        logs_to_json('delete_contract_function', 'delete_contract', str(e))
        abort(500)


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
