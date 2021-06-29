import json

class JSONDeserializer():
    def __init__(self, filepath) -> None:
        self.filepath = filepath

    def deserialize(self):
        with open(self.filepath, "r") as file:
            return json.load(file)


class JSONSerializer():
    def __init__(self, filepath) -> None:
        self.filepath = filepath

    def serialize(self, data):
        with open(self.filepath, "w") as file:
            json.dump(data, file)

