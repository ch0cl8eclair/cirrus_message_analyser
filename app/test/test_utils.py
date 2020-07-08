def read_payload_file(file_path):
    with open(file_path, 'r') as myfile:
        data = myfile.read()
    return data
