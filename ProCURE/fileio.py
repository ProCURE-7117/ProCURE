import json

# Define Class for four read-write functions
class FileIO:

    def file_reader(path):
        with open(path, 'r', encoding='utf-8') as file:
            data = file.read()
        return data

    def file_writer(path, file):
        with open(path, 'w') as files:
            files.write(file)

    def json_reader(path):
        with open(path, 'r', encoding='utf-8') as file:
            data = json.load(file)
        return data

    def json_writer(path, file):
        with open(path, 'w') as json_file:
            json.dump(file, json_file, indent=4)

    # JSON Lines format: one JSON object per line
    def read_jsonl(file_path):
        data = []
        with open(file_path, 'r', encoding='utf-8') as file:
            for line in file:
                json_obj = json.loads(line.strip())
                data.append(json_obj)
        return data
    
    def write_jsonl(data, file_path):
        with open(file_path, 'w', encoding='utf-8') as file:
            for item in data:
                json_line = json.dumps(item, ensure_ascii=False)
                file.write(json_line + '\n')