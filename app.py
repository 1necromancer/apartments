# -*- coding: utf-8 -*-
from flask import Flask, render_template, request, send_file, redirect
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
from datetime import datetime
from docx.shared import Pt
from docx import Document
import pandas as pd
import os
import re


load_dotenv()
app = Flask(__name__)


# Configuration for file paths
excel_folder = os.getenv('EXCEL_FOLDER')
doc_template = os.getenv('DOC_TEMPLATE')
doc_result = os.getenv('DOC_RESULT')

# Configuration for allowed file extensions
ALLOWED_EXTENSIONS = {'xlsx', 'xls', 'csv'}


def folders(path, file_name, project_name=None, user_name=None):
    try:
        if project_name is None:
            folder_path = path
        else:
            if user_name is None:
                folder_path = os.path.join(path, project_name)
            else:
                folder_path = os.path.join(path, project_name, user_name)
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
        return os.path.join(folder_path, file_name)
    except Exception as e:
        print(e)


# Helper function to check if the file extension is allowed
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# Helper function to replace placeholders in the Word document
def replace_text(doc, placeholder, replacement):
    for paragraph in doc.paragraphs:
        if placeholder in paragraph.text:
            paragraph.text = paragraph.text.replace(placeholder, str(replacement))
    for table in doc.tables:  # If there are tables
        for row in table.rows:
            for cell in row.cells:
                replace_text(cell, placeholder, replacement)


# Helper function to set formatting
def set_formatting(doc):
    for paragraph in doc.paragraphs:
        for run in paragraph.runs:
            run.font.name = 'Times New Roman'
            run.font.size = Pt(12)
            run.font.highlight_color = None  # Remove highlighting

    for table in doc.tables:  # If there are tables
        for row in table.rows:
            for cell in row.cells:
                for paragraph in cell.paragraphs:
                    for run in paragraph.runs:
                        run.font.name = 'Times New Roman'
                        run.font.size = Pt(12)
                        run.font.highlight_color = None  # Remove highlighting


# Process the Excel file and generate the Word document
def process_excel(file_path):
    file_extension = file_path.rsplit('.', 1)[1].lower()
    df_zalogoderzhatel = None
    df_zalogodatel = None
    # Handle CSV and Excel files accordingly
    if file_extension == 'csv':
        df_main = pd.read_csv(file_path)
    else:
        df_main = pd.read_excel(file_path, sheet_name='текст ДЗ заполнен')
        df_main.columns = df_main.columns.str.strip()
        df_zalogodatel = pd.read_excel(file_path, sheet_name='Залогодатель', header=None)
        df_zalogoderzhatel = pd.read_excel(file_path, sheet_name='Залогодержатель', header=None)

        # Process 'Залогодержатель' sheet
        df_zalogoderzhatel = df_zalogoderzhatel.T
        df_zalogoderzhatel.columns = df_zalogoderzhatel.iloc[0]
        df_zalogoderzhatel = df_zalogoderzhatel.drop(df_zalogoderzhatel.index[0]).reset_index(drop=True)
        df_zalogoderzhatel.columns = df_zalogoderzhatel.columns.str.strip()

        # Process 'Залогодатель' sheet
        df_zalogodatel = df_zalogodatel.T
        df_zalogodatel.columns = df_zalogodatel.iloc[0]
        df_zalogodatel = df_zalogodatel.drop(df_zalogodatel.index[0]).reset_index(drop=True)
        df_zalogodatel.columns = df_zalogodatel.columns.str.strip()

    # Load the Word document template
    doc = Document('doc_template/Проект ДКП.docx')

    # Extract and replace contract details
    contract_string = df_main.iloc[0]['Договор купли продажи']
    match = re.search(r'№\s*([^от]+?)\s+от', contract_string)
    contract_number = match.group(1).strip() if match else None
    date_match = re.search(r'от\s*(\d{2})\.(\d{2})\.(\d{4})', contract_string)

    if contract_number is not None:
        replace_text(doc, 'P_section', contract_number)
    if date_match is not None:
        replace_text(doc, 'dd_p', date_match.group(1))
        replace_text(doc, 'mm_p', date_match.group(2))
        replace_text(doc, 'yy_p', date_match.group(3))

    # Replace placeholders for seller information
    replace_text(doc, 'ТОО_продавец', df_zalogoderzhatel['Наименование компании'].iloc[0])
    replace_text(doc, 'должность_продавца', df_zalogoderzhatel['в лице (Подписанта) — должности'].iloc[0])
    replace_text(doc, 'ФИО_продавца', df_zalogoderzhatel['в лице (Подписанта) - Фамилии И.О.'].iloc[0])
    replace_text(doc, 'ИИН_продавца', df_zalogoderzhatel['БИН'].iloc[0])

    # Replace placeholders for buyer information
    replace_text(doc, 'должность_покупателя', df_zalogodatel['в лице (Подписанта) — должности'].iloc[0])
    replace_text(doc, 'ФИО_покупателя', df_zalogodatel['в лице (Подписанта) - Фамилии И.О.'].iloc[0])
    replace_text(doc, 'ИИН_покупателя', df_zalogodatel['БИН'].iloc[0])

    # Replace apartment details
    replace_text(doc, 'общая_площадь', df_main.iloc[0]['Общая площадь'])
    replace_text(doc, 'дом_номер, кв. квартира_номер,', df_main.iloc[0]['Адрес квартиры'])
    replace_text(doc, 'кадастровый_номер', df_main.iloc[0]['РКА'])

    # Replace ownership document details
    replace_text(doc, 'на_основании_чего от', df_main.iloc[0]['№ договора ПДКП/дата'])

    # Replace sum and payment deadline
    replace_text(doc, 'сумма_тенге', df_main.iloc[0]['Сумма уступленного долга по ПДКП (тенге)'])

    date_value = df_main.iloc[0]['Срок полного выкупа (ПДКП)']
    formatted_date = pd.to_datetime(date_value).strftime('%Y-%m-%d')
    replace_text(doc, 'год_расчета', formatted_date)

    # Replace seller's legal information
    replace_text(doc, 'БИН_продавца', df_zalogoderzhatel['БИН'].iloc[0])
    replace_text(doc, 'ИИК_продавца', df_zalogoderzhatel['IBAN'].iloc[0])
    replace_text(doc, 'БИК_продавца', df_zalogoderzhatel['БИК'].iloc[0])
    replace_text(doc, 'Банк_продаца', df_zalogoderzhatel['Банк'].iloc[0])
    replace_text(doc, 'телефон_продавца', df_zalogoderzhatel['Контактные телефоны:'].iloc[0])
    replace_text(doc, 'подпись_должность_пр', df_zalogoderzhatel['Подписант, должность'].iloc[0])
    replace_text(doc, 'подпись_должность_пок', df_zalogodatel['Подписант, должность'].iloc[0])

    # Apply formatting changes
    set_formatting(doc)

    # Save the processed document
    output_filename = f'doc_result/Проект ДКП_{datetime.now().strftime("%Y%m%d%H%M%S")}.docx'
    doc.save(output_filename)

    return output_filename


# Route to display upload form
@app.route('/', methods=['GET', 'POST'])
def index():
    return render_template('index.html')


# Route to handle file upload and processing
@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return redirect(request.url)

    file = request.files['file']

    if file.filename == '':
        return redirect(request.url)

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file_path = os.path.join(excel_folder, file.filename)
        file.save(file_path)

        # Process the file and generate Word document
        output_filename = process_excel(file_path)

        # Send the generated document as a downloadable file
        return send_file(output_filename, as_attachment=True)

    return redirect(request.url)


if __name__ == '__main__':
    if not os.path.exists(excel_folder):
        os.makedirs(excel_folder)
    if not os.path.exists('doc_result'):
        os.makedirs('doc_result')

    app.run(port=5656)
