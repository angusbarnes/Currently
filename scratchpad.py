from envparser import load_env
from tqdm import tqdm
from load_characterisation import characterise_load, create_load_report
from contextlib import redirect_stdout


ENV = load_env()

IDS = []
with open('substation_ids.txt', 'r') as id_file:
    IDS = map(lambda x: x.strip(), id_file.readlines())


for id in tqdm(list(IDS)):
    create_load_report(characterise_load(ENV['DATABASE_PATH'], id))