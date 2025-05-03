# utils.py

from database import save_file as db_save_file, get_file as db_get_file

def save_file(file_id):
    return db_save_file(file_id)

def get_file(code):
    return db_get_file(code)
