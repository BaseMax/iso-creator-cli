import os
import argparse
import hashlib
import shutil
import logging
import smtplib
from email.mime.text import MIMEText
from datetime import datetime
from pycdlib import PyCdlib
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor
import psutil
import json

TEMP_STATE_FILE = "iso_creator_state.json"

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

def process_file(iso, file_path, rel_path, verbose):
    try:
        iso.add_file(file_path, f"/{rel_path.upper().replace(os.sep, '/')}")
        if verbose:
            logging.info(f"Added: {rel_path}")
    except Exception as e:
        logging.error(f"Failed to add file {rel_path}: {e}")

def compress_iso(output, compression):
    compressed_output = f"{output}.{compression}"
    try:
        with open(output, 'rb') as src, open(compressed_output, 'wb') as dst:
            if compression == 'gz':
                import gzip
                with gzip.GzipFile(fileobj=dst, mode='wb') as gz, tqdm(desc="Compressing ISO") as pbar:
                    shutil.copyfileobj(src, gz, length=1024 * 1024)
                    pbar.update(1024 * 1024)
            elif compression == 'bz2':
                import bz2
                with bz2.BZ2File(dst, 'wb') as bz, tqdm(desc="Compressing ISO") as pbar:
                    shutil.copyfileobj(src, bz, length=1024 * 1024)
                    pbar.update(1024 * 1024)
            elif compression == 'xz':
                import lzma
                with lzma.LZMAFile(dst, 'wb') as xz, tqdm(desc="Compressing ISO") as pbar:
                    shutil.copyfileobj(src, xz, length=1024 * 1024)
                    pbar.update(1024 * 1024)
            else:
                raise ValueError("Unsupported compression format")
        logging.info(f"Compressed ISO: {compressed_output}")
    except Exception as e:
        logging.error(f"Compression failed: {e}")

def create_iso_pycdlib(source, output, label="ISO_LABEL", verbose=False, exclude=None, include=None,
                       compression=None, max_size=None, dry_run=False, checksum_algo="sha256",
                       include_hidden=False, email=None):
    iso = PyCdlib()
    try:
        iso.new(vol_ident=label)
        total_size = 0
        file_list = []

        dir_size = estimate_directory_size(source)
        check_disk_space(dir_size)

        state = load_state()
        processed_files = state.get("processed_files", set())

        with ThreadPoolExecutor() as executor:
            futures = []
            for root, dirs, files in os.walk(source):
                for file in tqdm(files, desc="Processing files"):
                    full_path = os.path.join(root, file)
                    rel_path = os.path.relpath(full_path, start=source)

                    if not include_hidden and file.startswith('.'):
                        continue

                    if exclude and any(excluded in rel_path for excluded in exclude):
                        continue

                    if include and not any(rel_path.endswith(inc) for inc in include):
                        continue

                    if rel_path in processed_files:
                        continue

                    file_size = os.path.getsize(full_path)
                    if max_size and (total_size + file_size > max_size):
                        logging.warning(f"File {rel_path} skipped due to exceeding max size limit.")
                        continue

                    if dry_run:
                        file_list.append(rel_path)
                        continue

                    total_size += file_size
                    futures.append(executor.submit(process_file, iso, full_path, rel_path, verbose))

            for future in tqdm(futures, desc="Adding files to ISO"):
                future.result()

        if dry_run:
            logging.info("Dry Run: The following files would be added:")
            for file in file_list:
                logging.info(file)
            return

        iso.write(output)
        iso.close()

        if compression:
            compress_iso(output, compression)

        checksum = calculate_checksum(output, algo=checksum_algo)
        logging.info(f"ISO image created successfully: {output}")
        logging.info(f"Checksum ({checksum_algo}): {checksum}")

        if email:
            send_email_notification(
                subject="ISO Creation Complete",
                message=f"Your ISO file has been created successfully: {output}\nChecksum: {checksum}",
                recipient=email,
            )
    except Exception as e:
        logging.error(f"Error during ISO creation: {e}")
        iso.close()
        exit(1)

def main():
    logging.basicConfig(filename="iso_creator.log", level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

    parser = argparse.ArgumentParser(description="Advanced ISO creation tool with PyCdlib.")
    parser.add_argument("-s", "--source", type=validate_directory, required=True, help="Source directory.")
    parser.add_argument("-o", "--output", type=validate_output_file, required=True, help="Output ISO file path.")
    parser.add_argument("-l", "--label", type=str, default=None, help="ISO label. Default: source directory name.")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose output.")
    parser.add_argument("-e", "--exclude", nargs="*", help="Exclude specific files or directories.")
    parser.add_argument("-i", "--include", nargs="*", help="Include only specific file extensions (e.g., .txt .jpg).")
    parser.add_argument("-c", "--compression", choices=['gz', 'bz2', 'xz'], help="Compress the ISO file.")
    parser.add_argument("--max-size", type=int, help="Maximum ISO size in bytes.")
    parser.add_argument("--dry-run", action="store_true", help="Simulate ISO creation.")
    parser.add_argument("--checksum", choices=['sha256', 'sha1', 'md5'], default="sha256", help="Checksum algorithm.")
    parser.add_argument("--include-hidden", action="store_true", help="Include hidden files in the ISO.")
    parser.add_argument("--email", type=str, help="Email address for notifications.")

    args = parser.parse_args()

    if args.label is None:
        args.label = datetime.now().strftime("ISO_%Y%m%d_%H%M%S")

    create_iso_pycdlib(
        source=args.source,
        output=args.output,
        label=args.label,
        verbose=args.verbose,
        exclude=args.exclude,
        include=args.include,
        compression=args.compression,
        max_size=args.max_size,
        dry_run=args.dry_run,
        checksum_algo=args.checksum,
        include_hidden=args.include_hidden,
        email=args.email
    )

if __name__ == "__main__":
    main()
