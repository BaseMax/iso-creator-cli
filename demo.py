import os
import random
import string
from io import BytesIO
import pycdlib

def generate_random_filename(length=8):
    """
    Generates a random filename consisting of uppercase letters and digits,
    ensuring it fits the 8.3 format for ISO9660 (8 characters max for name, 3 for extension).
    """
    characters = string.ascii_uppercase + string.digits
    return ''.join(random.choice(characters) for _ in range(length))

def add_directory(iso, dir_path, base_path='/', name_mapping=None):
    """
    Recursively adds files from a directory to the ISO image.
    """
    for root, dirs, files in os.walk(dir_path):
        for dir_name in dirs:
            dir_full_path = os.path.join(root, dir_name)
            dir_in_iso = os.path.join(base_path, os.path.relpath(dir_full_path, dir_path)).replace(os.sep, '/')
            
            sanitized_dir_in_iso = generate_random_filename()
            name_mapping[dir_in_iso] = sanitized_dir_in_iso

            print(dir_in_iso)
            iso.add_directory(f'/{sanitized_dir_in_iso}', udf_path=f'/{dir_in_iso}')

        for file_name in files:
            file_full_path = os.path.join(root, file_name)
            file_in_iso = os.path.join(base_path, os.path.relpath(file_full_path, dir_path)).replace(os.sep, '/')

            sanitized_file_in_iso = generate_random_filename()
            name_mapping[file_in_iso] = sanitized_file_in_iso

            with open(file_full_path, 'rb') as f:
                file_data = f.read()
                iso.add_fp(BytesIO(file_data), len(file_data), f'/{sanitized_file_in_iso}', udf_path=f'/{file_in_iso}')

def create_iso_from_files_and_dirs(selected_files_dirs, iso_filename='new.iso'):
    iso = pycdlib.PyCdlib()
    iso.new(udf='2.60')
    
    name_mapping = {}

    for item in selected_files_dirs:
        if os.path.isdir(item):
            add_directory(iso, item, name_mapping=name_mapping)
        elif os.path.isfile(item):
            file_in_iso = '/' + generate_random_filename()
            name_mapping[item] = file_in_iso

            with open(item, 'rb') as f:
                file_data = f.read()
                iso.add_fp(BytesIO(file_data), len(file_data), file_in_iso, udf_path=file_in_iso)
        else:
            print(f"Skipping invalid item: {item}")

    iso.write(iso_filename)
    iso.close()

    print("Name mapping:", name_mapping)

selected_files_dirs = ["./"]
create_iso_from_files_and_dirs(selected_files_dirs, 'new.iso')
