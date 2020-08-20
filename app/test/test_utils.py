import json

def read_payload_file(file_path):
    with open(file_path, 'r') as myfile:
        data = myfile.read()
    return data

def read_json_data_file(file_path):
    with open(file_path, 'r') as myfile:
        file_data = myfile.read()
        return json.loads(file_data)
