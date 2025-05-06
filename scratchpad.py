from envparser import load_env
from tqdm import tqdm
from load_characterisation import characterise_load, create_load_report
from contextlib import redirect_stdout


ENV = load_env()

IDS = []
with open('substation_ids.txt', 'r') as id_file:
    IDS = map(lambda x: x.strip(), id_file.readlines())

IDS = list(IDS)

pload_total, qload_total = 0, 0
for id in tqdm(IDS):
    pload, qload = create_load_report(characterise_load(ENV['DATABASE_PATH'], id))
    pload_total += pload
    qload_total += qload

print(f"Average Loads Per Sub: P = {pload_total/len(IDS):.2f}, Q = {qload_total/len(IDS):.2f}")