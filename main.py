import os
import random
import string
from io import BytesIO
import pycdlib
import hashlib
import shutil
import logging
import smtplib
from email.mime.text import MIMEText
from datetime import datetime
from tqdm import tqdm
import psutil
import json
import argparse
import threading
import zipfile

TEMP_STATE_FILE = "iso_creator_state.json"

def generate_random_filename(length=8):
    characters = string.ascii_uppercase + string.digits
    return ''.join(random.choice(characters) for _ in range(length))

def sanitize_filename(filename, max_length=8):
    name, ext = os.path.splitext(filename)
    sanitized_name = ''.join(c if c.isalnum() or c == '_' else '_' for c in name)[:max_length]
    sanitized_ext = ''.join(c if c.isalnum() else '_' for c in ext)[:4]
    result = sanitized_name.upper() + sanitized_ext.upper()
    return result[:max_length]

def validate_directory(path):
    if not os.path.isdir(path):
        raise argparse.ArgumentTypeError(f"{path} is not a valid directory.")
    return path

def validate_output_file(path):
    if not path.endswith(".iso"):
        raise argparse.ArgumentTypeError("Output file must have a .iso extension.")
    return path

def calculate_checksum(file_path, algo='sha256'):
    hash_func = hashlib.new(algo)
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b''):
            hash_func.update(chunk)
    return hash_func.hexdigest()

def estimate_directory_size(directory):
    total_size = 0
    for dirpath, _, filenames in os.walk(directory):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            total_size += os.path.getsize(fp)
    return total_size

def check_disk_space(required_space):
    free_space = psutil.disk_usage(os.getcwd()).free
    if free_space < required_space:
        raise RuntimeError(f"Insufficient disk space. Required: {required_space} bytes, Available: {free_space} bytes.")

def send_email_notification(subject, message, recipient):
    sender = "your_email@example.com"
    password = "your_password"
    try:
        msg = MIMEText(message)
        msg["Subject"] = subject
        msg["From"] = sender
        msg["To"] = recipient
        with smtplib.SMTP("smtp.example.com", 587) as server:
            server.starttls()
            server.login(sender, password)
            server.sendmail(sender, recipient, msg.as_string())
        logging.info("Email notification sent successfully.")
    except Exception as e:
        logging.error(f"Failed to send email notification: {e}")

def save_state(state):
    with open(TEMP_STATE_FILE, 'w') as f:
        json.dump(state, f)

def load_state():
    if os.path.exists(TEMP_STATE_FILE):
        with open(TEMP_STATE_FILE, 'r') as f:
            return json.load(f)
    return {}

def add_directory(iso, dir_path, base_path='/', name_mapping=None, compress=False, pbar=None):
    for root, dirs, files in os.walk(dir_path):
        for dir_name in dirs:
            dir_full_path = os.path.join(root, dir_name)
            dir_in_iso = os.path.join(base_path, os.path.relpath(dir_full_path, dir_path)).replace(os.sep, '/')
            sanitized_dir_in_iso = generate_random_filename()  
            name_mapping[dir_in_iso] = sanitized_dir_in_iso
            iso.add_directory(f'/{sanitized_dir_in_iso}', udf_path=f'/{dir_in_iso}')
        
        for file_name in files:
            file_full_path = os.path.join(root, file_name)
            file_in_iso = os.path.join(base_path, os.path.relpath(file_full_path, dir_path)).replace(os.sep, '/')
            sanitized_file_in_iso = generate_random_filename()
            name_mapping[file_in_iso] = sanitized_file_in_iso

            with open(file_full_path, 'rb') as f:
                file_data = f.read()

                if compress:
                    with BytesIO() as compressed_file:
                        with zipfile.ZipFile(compressed_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
                            zipf.writestr(file_name, file_data)
                        compressed_file.seek(0)
                        iso.add_fp(compressed_file, len(compressed_file.getvalue()), f'/{sanitized_file_in_iso}', udf_path=f'/{file_in_iso}')
                else:
                    iso.add_fp(BytesIO(file_data), len(file_data), f'/{sanitized_file_in_iso}', udf_path=f'/{file_in_iso}')
            
            if pbar:
                pbar.update(1)

def create_iso_from_files_and_dirs(selected_files_dirs, iso_filename='new.iso', label="ISO_LABEL", verbose=False, include_hidden=False, email=None, compress=False):
    iso = pycdlib.PyCdlib()
    iso.new(vol_ident=label, udf='2.60')
    
    name_mapping = {}  
    total_files = sum([len(files) for _, _, files in os.walk(selected_files_dirs[0])])
    
    with tqdm(total=total_files, desc="Adding files to ISO", unit='file') as pbar:
        for item in selected_files_dirs:
            if os.path.isdir(item):
                add_directory(iso, item, name_mapping=name_mapping, compress=compress, pbar=pbar)
            elif os.path.isfile(item):
                file_in_iso = '/' + generate_random_filename()  
                name_mapping[item] = file_in_iso  

                with open(item, 'rb') as f:
                    file_data = f.read()
                    iso.add_fp(BytesIO(file_data), len(file_data), file_in_iso, udf_path=file_in_iso)
                pbar.update(1)
            else:
                logging.warning(f"Skipping invalid item: {item}")
    
    iso.write(iso_filename)
    iso.close()

    checksum = calculate_checksum(iso_filename)
    logging.info(f"ISO created successfully. Checksum ({checksum})")
    
    if email:
        send_email_notification("ISO Creation Successful", f"The ISO file has been created successfully. Checksum: {checksum}", email)

def main():
    logging.basicConfig(filename="iso_creator.log", level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

    parser = argparse.ArgumentParser(description="Advanced ISO creation tool with PyCdlib.")
    parser.add_argument("-s", "--source", type=validate_directory, required=True, help="Source directory.")
    parser.add_argument("-o", "--output", type=validate_output_file, required=True, help="Output ISO file path.")
    parser.add_argument("-l", "--label", type=str, default=None, help="ISO label. Default: source directory name.")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose output.")
    parser.add_argument("--include-hidden", action="store_true", help="Include hidden files.", default=True)
    parser.add_argument("--email", type=str, help="Email address for notifications.")
    parser.add_argument("--compress", action="store_true", help="Compress files before adding them to the ISO.")

    args = parser.parse_args()

    if args.label is None:
        args.label = datetime.now().strftime("ISO_%Y%m%d_%H%M%S")

    dir_size = estimate_directory_size(args.source)
    check_disk_space(dir_size)

    create_iso_from_files_and_dirs(
        selected_files_dirs=[args.source],
        iso_filename=args.output,
        label=args.label,
        verbose=args.verbose,
        include_hidden=args.include_hidden,
        email=args.email,
        compress=args.compress
    )

if __name__ == "__main__":
    main()
