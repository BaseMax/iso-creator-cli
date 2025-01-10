# ISO Creator CLI

This is a powerful Python command-line tool for creating ISO files from directories using the `PyCdlib` library. It supports advanced features such as compression, checksum calculation, file filtering, and email notifications upon completion.

## Features

- Create ISO files from directories.
- Support for file inclusion and exclusion (based on extensions, file paths, or hidden files).
- Compress ISO files into `.gz`, `.bz2`, or `.xz` formats.
- Calculate file checksums (`sha256`, `sha1`, or `md5`).
- Email notification upon successful ISO creation.
- Dry-run mode to simulate ISO creation without modifying any files.
- Multithreaded file processing for faster creation.

## Installation

1. Clone this repository:

    ```bash
    git clone https://github.com/BaseMax/iso-creator-cli.git
    cd iso-creator-cli
    ```

2. Install dependencies:

    ```bash
    pip install -r requirements.txt
    ```

3. Ensure you have the required libraries for compression (e.g., `gzip`, `bz2`, `lzma`).

## Usage

The `iso_creator` tool is a command-line utility that requires several arguments to work. Below is the basic syntax:

```bash
python iso_creator.py -s SOURCE_DIR -o OUTPUT_FILE [OPTIONS]
```

### Required Arguments

- `-s, --source`: The source directory to be converted into an ISO file.
- `-o, --output`: The output ISO file path (must end with `.iso`).

### Optional Arguments

- `-l, --label`: The label for the ISO. If not provided, the source directory name is used.
- `-v, --verbose`: Enable verbose output.
- `-e, --exclude`: Exclude specific files or directories from the ISO.
- `-i, --include`: Include only specific file extensions (e.g., `.txt .jpg`).
- `-c, --compression`: Compress the ISO file. Available options are `gz`, `bz2`, or `xz`.
- `--max-size`: Set a maximum size for the ISO file in bytes.
- `--dry-run`: Simulate ISO creation without writing the file.
- `--checksum`: Choose a checksum algorithm. Options are `sha256`, `sha1`, or `md5`. Default is `sha256`.
- `--include-hidden`: Include hidden files (those starting with a dot) in the ISO.
- `--email`: Email address to receive notifications once the ISO creation is complete.

### Examples

1. **Basic ISO Creation**:

    Create an ISO from the source directory `/path/to/source` and output it to `/path/to/output.iso`:

    ```
    python iso_creator.py -s /path/to/source -o /path/to/output.iso
    ```


2. **ISO Creation with Compression**:  

    Create an ISO with compression (`xz` format) from `/path/to/source` to `/path/to/output.iso`:

    ```
    python iso_creator.py -s /path/to/source -o /path/to/output.iso -c xz
    ```

3. **ISO Creation with Specific Label and Checksum**:  

    Create an ISO with a custom label and `sha1` checksum algorithm:

    ```
    python iso_creator.py -s /path/to/source -o /path/to/output.iso -l MyISO -c sha1
    ```

4. **Include Specific File Types**:  

    Include only `.txt` and `.jpg` files in the ISO:
    
    ```
    python iso_creator.py -s /path/to/source -o /path/to/output.iso -i .txt .jpg
    ```

5. **Exclude Specific Files or Directories**:
    
    Exclude files in the `temp` directory from the ISO:
    
    ```
    python iso_creator.py -s /path/to/source -o /path/to/output.iso -e temp
    ```

6. **Dry Run**:
    
    Perform a dry run of the ISO creation without actually creating the ISO:
    
    ```
    python iso_creator.py -s /path/to/source -o /path/to/output.iso --dry-run
    ```

7. **Email Notification**:
    
    Send an email notification upon successful ISO creation:
    
    ```
    python iso_creator.py -s /path/to/source -o /path/to/output.iso --email your_email@example.com
    ```

### License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for more details.

Copyright 2025, Max Base
