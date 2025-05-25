import json

def get_resources():
  with open("resources.txt", "r", encoding="utf-8") as f:
      return json.loads(f.read())

def get_processes():
  with open("processes.txt", "r", encoding="utf-8") as f:
      return json.loads(f.read())

