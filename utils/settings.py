import os

def get_blob_connection_string():
    blob_connection_string = os.getenv("BLOB_CONNECTION_STRING")
    return blob_connection_string

