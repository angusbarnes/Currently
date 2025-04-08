from envparser import load_env
from load_characterisation import characterise_load
from contextlib import redirect_stdout


ENV = load_env()

IDS = []
with open('substation_ids.txt', 'r') as id_file:
    IDS = map(lambda x: x.strip(), id_file.readlines())


for id in IDS:
    with open(f'./reports/{id}.txt', 'w') as f:
            f.write(characterise_load(ENV['DATABASE_PATH'], id))