import csv
import json


current_gw = 4
csv_file_name = "src/data/csvs/Reddit Anti-Fantasy '20 -'21 - GW {gw}.csv"
output_json_name = "src/data/gw_jsons/gw_{gw}.json"
manager_id_file = "src/data/manager_id_mapping.json"


def read_csv(gw):

    data = {}

    with open(csv_file_name.format(gw=gw)) as csvfile:
        reader = csv.reader(csvfile, delimiter=',')

        for i, r in enumerate(reader):
            if i < 3:
                continue
            data[r[2]] = {'points': int(r[7]), 'rank': int(r[0])}
    return data


def read_manager_id():
    with open(manager_id_file, 'r') as jfile:
        return json.loads(jfile.read())


def create_gw_json(gw):
    gw_res = read_csv(gw)
    manager_id_dict = read_manager_id()

    final_dict = {}

    for k in manager_id_dict.keys():
        final_dict[manager_id_dict[k]] = {
            'points': gw_res[k]['points'],
            'name': k,
            'rank': gw_res[k]['rank']
        }

    with open(output_json_name.format(gw=gw), 'w') as file:
        file.write(json.dumps(final_dict))


read_csv(current_gw)
create_gw_json(current_gw)
