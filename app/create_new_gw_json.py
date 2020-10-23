import json
import sys

gw_standings_file = "data/gw_standings/standings_{gw}.json"
final_gw_jsons = "data/gw_jsons/gw_{gw}.json"


def read_current_gw_data(gw):
    """Get the data for the current gameweek

    """
    with(open(gw_standings_file.format(gw=gw), 'r')) as f:
        return json.loads(f.read())


def write_new_gw_data(gw, data):
    """Write filtered information of a gw
    This data is used a base for next gameweek

    """
    with(open(final_gw_jsons.format(gw=gw), 'w')) as f:
        f.write(json.dumps(data))


def process_new_gw_file(gw):
    """Extract the manager id, points, and rank
    from the current gameweek and store only these
    information to the new file 

    Args:
        gw ([type]): [description]
    """
    last_gw = read_current_gw_data(gw)

    last_gw_data = last_gw['data']
    new_gw_data = {}
    for p in last_gw_data:
        d_ = {}
        d_['name'] = p['player_name']
        d_['points'] = p['total_points']
        d_['rank'] = p['rank']
        new_gw_data[p["id"]] = d_

    write_new_gw_data(gw, new_gw_data)


if __name__ == "__main__":
    """Specify the gameweek number to process the file on

    Example: python create_new_gw_json.py 5
    """
    gw = sys.argv[1]
    process_new_gw_file(int(gw))
