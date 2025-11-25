import json

def get_json(dir, name):
    path = f"{name}.json" if dir is None else f"{dir}/{name}.json"
    with open(path, "r") as file:
        return json.load(file)
def write_json(dir, name, data):
    import os, json
    path = f"{name}.json" if dir is None else f"{dir}/{name}.json"
    if dir is not None:
        os.makedirs(dir, exist_ok=True)
    with open(path, "w") as file:
        json.dump(data, file, indent=2)

    print(f"{name}.json saved!")

