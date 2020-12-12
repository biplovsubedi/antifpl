""" 
This file is used to process the CSV file containing the previous GW
information for each manager. 
CSV file extracted from the google sheets

Convert to a JSON file that has manager's id, rank, points, name for 
that gameweek. 

"""


import csv
import json
import sys

current_gw = 11  # GW of the file to be converted
csv_file_name = "app/data/csvs/Reddit Anti-Fantasy '20 -'21 - GW {gw}.csv"
output_json_name = "app/data/gw_jsons/gw_{gw}.json"
manager_id_file = "app/data/manager_id_mapping.json"


def read_csv(gw):
    """Read the csv file containing GW data

    Convert that CSV to python dict
    Format:
    {
       "1471816": {
        "points": 280,
        "name": "Some name",
        "rank": 131
        }, 
        ....
    }

    Args:
        gw (int): gameweek

    Returns:
        dict: manager id(k) dict of points, name, rank (v)
    """

    data = {}

    with open(csv_file_name.format(gw=gw)) as csvfile:
        reader = csv.reader(csvfile, delimiter=',')

        for i, r in enumerate(reader):
            if i < 3:
                continue
            data[r[2]] = {'points': int(r[7]), 'rank': int(r[0])}
    return data


def read_manager_id():
    """Read the file that contains manager's name (k), id(v)

    Returns:
        dict: file data
    """
    with open(manager_id_file, 'r') as jfile:
        return json.loads(jfile.read())


def create_gw_json(gw):
    """Convert the CSV dict data to the required format

    Extracting: points, name, rank
    Join the 2 dicts (gw_info, manager_id on manager name)

    Args:
        gw ([type]): [description]
    """
    gw_res = read_csv(gw)
    manager_id_dict = read_manager_id()

    final_dict = {}

    for k in manager_id_dict.keys():
        try:
            final_dict[manager_id_dict[k]] = {
                'points': gw_res[k]['points'],
                'name': k,
                'rank': gw_res[k]['rank']
            }
        except KeyError:
            pass
    with open(output_json_name.format(gw=gw), 'w') as file:
        file.write(json.dumps(final_dict))


if __name__ == "__main__":
    """Specify the gameweek number to process the file on

    Example: python create_new_gw_json.py 5
    """
    gw = sys.argv[1]
    create_gw_json(int(gw))
