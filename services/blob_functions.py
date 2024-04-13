from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient
from utils.settings import get_blob_connection_string
import os


def upload_qr_code_to_blob_storage(qr_code_buffer, filename):
    try:
        blob_connection_string = get_blob_connection_string()
        container_name = "qr-codes"
        blob_service_client = BlobServiceClient.from_connection_string(blob_connection_string)
        container_client = blob_service_client.get_container_client(container_name)

        # Check if the container exists, create if not
        if not container_client.exists():
            container_client.create_container()

        # Upload the QR code image from the in-memory buffer to Azure Blob Storage
        blob_client = container_client.get_blob_client(filename)
        blob_client.upload_blob(qr_code_buffer)

        # Get the URL of the uploaded image
        blob_url = f"https://travelfitstorage.blob.core.windows.net/{container_name}/{filename}"

        return blob_url
    except Exception as e:
        print(f"An error occurred during blob upload: {e}")

        