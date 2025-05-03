import random
import string
from database import save_file as db_save_file, get_file as db_get_file

def gen_code(length=8):
    """تابعی برای تولید یک کد تصادفی از حروف و اعداد"""
    characters = string.ascii_letters + string.digits
    code = ''.join(random.choice(characters) for _ in range(length))
    return code

def save_file(file_id, code):
    return db_save_file(file_id, code)

def get_file(code):
    """دریافت فایل از دیتابیس بر اساس کد"""
    return db_get_file(code)
