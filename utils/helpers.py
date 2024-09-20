import logging
import os
import docx
import PyPDF2
import pandas as pd
logger = logging.getLogger(__name__)

def load_directory_or_file(item_path: str = None):
    if os.path.isdir(item_path):
        logger.debug(f'Loading directory {item_path}')
        return extract_text_from_files_in_folder(item_path)
    elif os.path.isfile(item_path):
        logger.debug(f'Loading file {item_path}')
        if item_path.lower().endswith('.docx'):
            return extract_text_from_docx(item_path)
        elif item_path.lower().endswith('.pdf'):
            return extract_text_from_pdf(item_path)
        elif item_path.lower().endswith('.txt'):
            return extract_text_from_txt(item_path)
        else:
            raise NotImplementedError(f"Unsupported file type: {item_path}. Must be PDF, DOCX, or TXT")
    else:
        raise NotImplementedError(f"Unsupported item path: {item_path}")

def extract_text_from_docx(file_path):
    doc = docx.Document(file_path)
    return "\n".join([para.text for para in doc.paragraphs])

def extract_text_from_pdf(file_path):
    pdf_text = []
    with open(file_path, 'rb') as file:
        pdf_reader = PyPDF2.PdfFileReader(file)
        for page_num in range(pdf_reader.numPages):
            page = pdf_reader.getPage(page_num)
            pdf_text.append(page.extractText())
    return "\n".join(pdf_text)

def extract_text_from_txt(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        return file.read()

def extract_text_from_files_in_folder(folder_path):
    text_data = {}
    valid_extensions = ['.docx', '.pdf', '.txt']
    for root, dirs, files in os.walk(folder_path):
        for file in files:
            file_path = os.path.join(root, file)
            file_extension = os.path.splitext(file)[1].lower()
            if file_extension in valid_extensions:
                logger.debug(f'Loading file {file_path}')
                if file_extension == '.docx':
                    text_data[file] = extract_text_from_docx(file_path)
                elif file_extension == '.pdf':
                    text_data[file] = extract_text_from_pdf(file_path)
                elif file_extension == '.txt':
                    text_data[file] = extract_text_from_txt(file_path)
    return '.'.join([x for x in text_data.values()])

def read_file_to_dataframe(file_path: str) -> pd.DataFrame:
    """
    Reads a CSV or XLSX file into a pandas DataFrame from either a local file or a GCS URI.

    Args:
        file_path (str): The local file path or GCS URI of the CSV/XLSX file.

    Returns:
        pd.DataFrame: The pandas DataFrame containing the data.

    Raises:
        ValueError: If the file path or GCS URI format is invalid.
    """
    # Determine file type based on extension
    _, file_extension = os.path.splitext(file_path)
    if file_extension not in ['.csv','.tsv', '.xlsx', '.xlsm']:
        raise ValueError("Unsupported file type. Only TSV, CSV, XLSM, and XLSX are supported.")

    if file_path.startswith('gs://'):
        # Process GCS URI
        parts = file_path.replace("gs://", "").split("/", 1)
        bucket_name = parts[0]
        blob_path = parts[1]

        storage_client = storage.Client()
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(blob_path)

        # Download the blob to a BytesIO object
        byte_stream = io.BytesIO()
        blob.download_to_file(byte_stream)
        byte_stream.seek(0)

        # Read the appropriate file type
        if file_extension == '.csv':
            return pd.read_csv(byte_stream)
        elif file_extension == '.tsv':
            return pd.read_csv(byte_stream, sep='\t')

        else:  # '.xlsx'
            return pd.read_excel(byte_stream)
    else:
        # Process local file
        assert os.path.exists(file_path),f"Could not find {file_path}"
        if file_extension == '.csv':
            return pd.read_csv(file_path)
        elif file_extension == '.tsv':
            return pd.read_csv(file_path, sep='\t')
        else:  # '.xlsx'
            return pd.read_excel(file_path)


def read_text(file_path: str, multiline: bool = False) -> [str, list]:
    """
    Return a string or a list of strings from a file on GCP or local.

    Args:
        file_path (str): The file path or GCS URI of the text file. For GCS, format as 'gs://bucket-name/path/to/file.txt'.
        multiline (bool): If True, returns a list of lines. Otherwise, returns a single string.

    Returns:
        str or list: The content of the file as a single string or a list of strings.

    Raises:
        ValueError: If the GCS URI format is invalid.
    """
    if file_path.startswith('gs://'):
        return read_text_from_gcs(file_path, multiline)
    else:
        with open(file_path, 'r') as f:
            return f.readlines() if multiline else f.read()


def read_text_from_gcs(gcs_uri: str, multiline: bool) -> [str, list]:
    """
    Reads all text from a text file in a Google Cloud Storage (GCS) bucket.

    Args:
        gcs_uri (str): The GCS URI of the text file in the format 'gs://bucket-name/path/to/file.txt'.
        multiline (bool): If True, returns a list of lines. Otherwise, returns a single string.

    Returns:
        str or list: The content of the file as a single string or a list of strings.

    Raises:
        ValueError: If the GCS URI format is invalid.
    """
    # Parse GCS URI
    if not gcs_uri.startswith("gs://"):
        raise ValueError("Invalid GCS URI")

    parts = gcs_uri.replace("gs://", "").split("/", 1)
    bucket_name = parts[0]
    file_path = parts[1]

    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(file_path)

    # Read the contents of the file
    text_data = blob.download_as_text()

    return text_data.splitlines() if multiline else text_data
