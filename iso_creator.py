# python iso_creator.py -s ../Salam -o r.iso
import os
import random
import string
from io import BytesIO
import pycdlib
import hashlib
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
import tarfile
import lzma
import py7zr

TEMP_STATE_FILE = "iso_creator_state.json"
MAX_FILE_SIZE = 1 * 1024 * 1024 * 1024  # 1 GB max file size
COMPRESSION_METHODS = ['zip', 'tar.gz', 'tar.bz2', 'tar.xz', '7z']

def generate_random_filename(length=8):
    """Generates a random filename of given length."""
    characters = string.ascii_uppercase + string.digits
    return ''.join(random.choice(characters) for _ in range(length))

def sanitize_filename(filename, max_length=8):
    """Sanitizes the filename to ensure it's safe and within the max length."""
    name, ext = os.path.splitext(filename)
    sanitized_name = ''.join(c if c.isalnum() or c == '_' else '_' for c in name)[:max_length]
    sanitized_ext = ''.join(c if c.isalnum() else '_' for c in ext)[:4]
    return (sanitized_name + sanitized_ext).upper()[:max_length]

def validate_directory(path):
    """Validates if the given path is a directory."""
    if not os.path.isdir(path):
        raise argparse.ArgumentTypeError(f"{path} is not a valid directory.")
    return path

def validate_output_file(path):
    """Validates if the given file path has a .iso extension."""
    if not path.endswith(".iso"):
        raise argparse.ArgumentTypeError("Output file must have a .iso extension.")
    return path

def calculate_checksum(file_path, algo='sha256'):
    """Calculates checksum of the file."""
    hash_func = hashlib.new(algo)
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b''):
            hash_func.update(chunk)
    return hash_func.hexdigest()

def estimate_directory_size(directory):
    """Estimates the size of a directory."""
    total_size = 0
    for dirpath, _, filenames in os.walk(directory):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            total_size += os.path.getsize(fp)
    return total_size

def check_disk_space(required_space):
    """Checks if there is sufficient disk space."""
    free_space = psutil.disk_usage(os.getcwd()).free
    if free_space < required_space:
        raise RuntimeError(f"Insufficient disk space. Required: {required_space} bytes, Available: {free_space} bytes.")

def send_email_notification(subject, message, recipient):
    """Sends an email notification."""
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
    """Saves the current state to a file."""
    with open(TEMP_STATE_FILE, 'w') as f:
        json.dump(state, f)

def load_state():
    """Loads the previously saved state."""
    if os.path.exists(TEMP_STATE_FILE):
        with open(TEMP_STATE_FILE, 'r') as f:
            return json.load(f)
    return {}

def compress_file(file_data, method, file_name):
    """Compresses the given file data using the specified method."""
    compressed_data = BytesIO()
    try:
        if method == 'zip':
            with zipfile.ZipFile(compressed_data, 'w', zipfile.ZIP_DEFLATED) as zipf:
                zipf.writestr(file_name, file_data)
        elif method == 'tar.gz':
            with tarfile.open(fileobj=compressed_data, mode='w:gz') as tarf:
                fileobj = BytesIO(file_data)
                tarf.addfile(tarf.addfile(fileobj, arcname=file_name))
        elif method == 'tar.bz2':
            with tarfile.open(fileobj=compressed_data, mode='w:bz2') as tarf:
                fileobj = BytesIO(file_data)
                tarf.addfile(tarf.addfile(fileobj, arcname=file_name))
        elif method == 'tar.xz':
            with lzma.open(compressed_data, 'wb') as f:
                f.write(file_data)
        elif method == '7z':
            with py7zr.SevenZipFile(compressed_data, mode='w') as archive:
                archive.write([file_name], arcname=file_name)
        else:
            raise ValueError("Unsupported compression method")
    except Exception as e:
        logging.error(f"Error during compression: {e}")
        raise
    compressed_data.seek(0)
    return compressed_data

def add_directory(iso, dir_path, base_path='/', name_mapping=None, compress=False, method='zip', pbar=None, include_hidden=False, exclude_files=None, exclude_dirs=None):
    """Adds files and directories to the ISO."""
    for root, dirs, files in os.walk(dir_path):
        for dir_name in dirs:
            if exclude_dirs and dir_name in exclude_dirs:
                dirs.remove(dir_name)
                continue
            else:
                dir_full_path = os.path.join(root, dir_name)
                dir_in_iso = os.path.join(base_path, os.path.relpath(dir_full_path, dir_path)).replace(os.sep, '/')
                sanitized_dir_in_iso = generate_random_filename()
                name_mapping[dir_in_iso] = sanitized_dir_in_iso
                iso.add_directory(f'/{sanitized_dir_in_iso}', udf_path=f'/{dir_in_iso}')

        for file_name in files:
            if exclude_files and file_name in exclude_files:
                continue

            if not include_hidden and file_name.startswith('.'):
                continue

            file_full_path = os.path.join(root, file_name)
            if os.path.getsize(file_full_path) > MAX_FILE_SIZE:
                logging.warning(f"Skipping large file: {file_name} (size exceeds limit).")
                continue

            file_in_iso = os.path.join(base_path, os.path.relpath(file_full_path, dir_path)).replace(os.sep, '/')
            sanitized_file_in_iso = generate_random_filename()
            name_mapping[file_in_iso] = sanitized_file_in_iso

            with open(file_full_path, 'rb') as f:
                file_data = f.read()

                if compress:
                    compressed_data = compress_file(file_data, method, file_name)
                    iso.add_fp(compressed_data, len(compressed_data.getvalue()), f'/{sanitized_file_in_iso}', udf_path=f'/{file_in_iso}')
                else:
                    iso.add_fp(BytesIO(file_data), len(file_data), f'/{sanitized_file_in_iso}', udf_path=f'/{file_in_iso}')
            
            if pbar:
                pbar.update(1)

def create_iso_from_files_and_dirs(selected_files_dirs, iso_filename='new.iso', label="ISO_LABEL", verbose=False, include_hidden=False, exclude_dirs=None, exclude_files=None, dry_run=False, compress=False, method='zip', email=None):
    """Creates the ISO file from selected files and directories."""
    iso = pycdlib.PyCdlib()
    iso.new(vol_ident=label, udf='2.60')
    
    name_mapping = {}
    total_files = sum([len(files) for _, _, files in os.walk(selected_files_dirs[0])])
    
    with tqdm(total=total_files, desc="Adding files to ISO", unit='file') as pbar:
        for item in selected_files_dirs:
            if os.path.isdir(item):
                add_directory(iso, item, name_mapping=name_mapping, compress=compress, method=method, pbar=pbar, include_hidden=include_hidden, exclude_files=exclude_files, exclude_dirs=exclude_dirs)
            elif os.path.isfile(item):
                file_in_iso = '/' + generate_random_filename()
                name_mapping[item] = file_in_iso  

                with open(item, 'rb') as f:
                    file_data = f.read()
                    if dry_run:
                        logging.info(f"Dry-run: Adding {item}")
                    else:
                        iso.add_fp(BytesIO(file_data), len(file_data), file_in_iso, udf_path=file_in_iso)
                pbar.update(1)
            else:
                logging.warning(f"Skipping invalid item: {item}")
    
    if not dry_run:
        iso.write(iso_filename)
        iso.close()

        checksum = calculate_checksum(iso_filename)
        logging.info(f"ISO created successfully. Checksum ({checksum})")
    
    if not dry_run and email:
        send_email_notification("ISO Creation Successful", f"The ISO file has been created successfully. Checksum: {checksum}", email)

def main():
    """Main entry point for the script."""
    logging.basicConfig(filename="iso_creator.log", level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

    parser = argparse.ArgumentParser(description="Advanced ISO creation tool with PyCdlib.")
    parser.add_argument("-s", "--source", type=validate_directory, required=True, help="Source directory.")
    parser.add_argument("-o", "--output", type=validate_output_file, required=True, help="Output ISO file path.")
    parser.add_argument("-l", "--label", type=str, default=None, help="ISO label. Default: source directory name.")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose output.")
    parser.add_argument("--include-hidden", action="store_true", help="Include hidden files.", default=False)
    parser.add_argument("--exclude-dirs", type=str, nargs="*", help="Exclude specific directories.")
    parser.add_argument("--exclude-files", type=str, nargs="*", help="Exclude specific files.")
    parser.add_argument("--dry-run", action="store_true", help="Simulate the process without creating the ISO.")
    parser.add_argument("--email", type=str, help="Email address for notifications.")
    parser.add_argument("--compress", action="store_true", help="Compress files before adding them to the ISO.")
    parser.add_argument("--compression-method", type=str, choices=COMPRESSION_METHODS, default='zip', help="Compression method to use.")
    parser.add_argument("--multi-thread", action="store_true", help="Use multi-threading for parallel file processing.")

    args = parser.parse_args()

    if args.label is None:
        args.label = datetime.now().strftime("ISO_%Y%m%d_%H%M%S")

    dir_size = estimate_directory_size(args.source)
    check_disk_space(dir_size)

    if args.multi_thread:
        logging.info("Multi-threading enabled. Using threads to process files.")
        threads = []
        for item in args.source:
            thread = threading.Thread(target=create_iso_from_files_and_dirs, args=(item, args.output, args.label, args.verbose, args.include_hidden, args.exclude_dirs, args.exclude_files, args.dry_run, args.compress, args.compression_method))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
    else:
        create_iso_from_files_and_dirs(
            selected_files_dirs=[args.source],
            iso_filename=args.output,
            label=args.label,
            verbose=args.verbose,
            include_hidden=args.include_hidden,
            exclude_dirs=args.exclude_dirs,
            exclude_files=args.exclude_files,
            dry_run=args.dry_run,
            email=args.email,
            compress=args.compress,
            method=args.compression_method
        )

if __name__ == "__main__":
    main()
