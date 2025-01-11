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
- `--include-hidden`: Include hidden files in the ISO.
- `--exclude-dirs`: Exclude specific directories (comma-separated).
- `--exclude-files`: Exclude specific files (comma-separated).
- `--dry-run`: Simulate the process without actually creating the ISO file.
- `--email`: The email address to send notifications to upon successful creation.
- `--compress`: Compress files before adding them to the ISO.
- `--compression-method`: Choose a compression method (options: zip, tar.gz, tar.bz2, tar.xz, 7z).
- `--multi-thread`: Use multithreading for faster file processing.

### Examples

1. **Create an ISO file from a directory:**

    ```bash
    python iso_creator.py -s /path/to/source -o output.iso
    ```

2. **Create a compressed ISO with .tar.gz compression:**

    ```bash
    python iso_creator.py -s /path/to/source -o output.iso --compress --compression-method tar.gz
    ```

3. **Perform a dry-run (simulate creation):**

    ```bash
    python iso_creator.py -s /path/to/source -o output.iso --dry-run
    ```

4. **Send email notification upon successful creation:**

    ```bash
    python iso_creator.py -s /path/to/source -o output.iso --email your_email@example.com
    ```


5. **Exclude Specific Files or Directories**:
    
    Exclude files in the `temp` directory from the ISO:
    
    ```
    python iso_creator.py -s /path/to/source -o /path/to/output.iso --exclude-dirs temp
    ```

6. **Dry Run**:
    
    Perform a dry run of the ISO creation without actually creating the ISO:
    
    ```
    python iso_creator.py -s /path/to/source -o /path/to/output.iso --dry-run
    ```

### License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for more details.

Read more https://clalancette.github.io/pycdlib/pycdlib-api.html and https://clalancette.github.io/pycdlib/example-creating-udf-iso.html

Copyright 2025, Max Base
