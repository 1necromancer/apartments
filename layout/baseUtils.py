from dotenv import load_dotenv
from datetime import datetime
from pathlib import Path
import shutil
import json
import os

env_path = Path(__file__).resolve().parent.parent / '.env'
load_dotenv(dotenv_path=env_path)
excel_folder = os.getenv('EXCEL_FOLDER')


def logs_to_json(error_from_function, folder_name, error):
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    data_to_store = {
        "from": error_from_function,
        "folder_name": folder_name,
        "time": current_time,
        "error": error
    }

    try:
        with open(folders('storage', 'logs.json'), 'r+') as file:
            stored_data = json.load(file)
            stored_data.append(data_to_store)
            file.seek(0)
            json.dump(stored_data, file, indent=4)
    except FileNotFoundError:
        with open(folders('storage', 'logs.json'), 'w') as file:
            json.dump([data_to_store], file, indent=4)


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


def delete_excel_folder(folder_to_delete):
    try:
        excel_path = os.path.join(os.getcwd(), excel_folder, folder_to_delete)
        if os.path.exists(excel_path):
            shutil.rmtree(excel_path)
            return "Excel folder deleted successfully"
        else:
            return "Excel folder does not exists"
    except Exception as e:
        logs_to_json('delete_excel_folder_function', folder_to_delete, str(e))
        return "Error while deleting excel folder"
