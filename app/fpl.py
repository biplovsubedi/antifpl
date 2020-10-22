from flask import Flask, render_template
import requests
import json

import calendar
import time

from operator import itemgetter


app = Flask(__name__)

url_standings_base = "https://fantasy.premierleague.com/api/leagues-classic/307809/standings/?page_standings="
url_live_gw = "https://fantasy.premierleague.com/api/event/{gw}/live/"
url_gw_picks = "https://fantasy.premierleague.com/api/entry/{entry}/event/{gw}/picks/"

fixture_date_file = 'app/data/fixtures_date.json'


"""
Endpoints: 
https://fantasy.premierleague.com/api/entry/4621202/event/4/picks/  -> See picks for a player in a week
History of a player: https://fantasy.premierleague.com/api/entry/4621202/history/




"""


def request_data_from_url(url):
    try:
        res = requests.get(url)
    except:
        return None
    if res.status_code != 200:
        return None

    return json.loads(res.text)


def find_current_gw():

    with open(fixture_date_file, 'r') as file:
        fixtures = file.read()

    epoch_time = calendar.timegm(time.gmtime())
    fixture_d = json.loads(fixtures)

    for f in fixture_d:
        if f['deadline_time_epoch'] + 4500 > epoch_time:
            return f['id'] - 1
    return 0


def get_last_gw_standings(gw):

    last_gw_file = "app/data/gw_jsons/gw_" + str(gw) + ".json"

    try:
        with open(last_gw_file, 'r') as file:
            return json.loads(file.read())
    except FileNotFoundError:
        print("file not found last gw" + last_gw_file)
        return {}


def dump_json_with_time(gw, data):
    location = ['app/data/gw_standings/standings_{gw}.json'.format(
        gw=gw), 'app/data/gw_standings/standings_current.json']
    epoch_time = calendar.timegm(time.gmtime())
    new_dict = {
        'gameweek': gw,
        'updated': epoch_time,
        'data': data
    }
    for l in location:
        with open(l, 'w') as file:
            file.write(json.dumps(new_dict))
    return new_dict


def find_captains(picks):
    # Find the captains and vice captains for the gw
    captain, vice_captain = None, None
    for player in picks['picks']:
        if player['is_captain'] == True:
            captain = player["element"]
        elif player["is_vice_captain"] == True:
            vice_captain = player["element"]
        if captain != None and vice_captain != None:
            return (captain, vice_captain)


def filter_all_gw_picks(gw, complete_gw_picks):
    filtered_gw_picks = {}
    for player, picks in complete_gw_picks.items():
        filtered_gw_picks[player] = {
            "active_chip": picks["active_chip"],
            "itb": float(picks['entry_history']['bank'])/10.0,
            "squad_value": float(picks['entry_history']['value'])/10.0,
            "transfer_cost": int(picks['entry_history']['event_transfers_cost']),
            "transfers": int(picks['entry_history']['event_transfers']),
            "captains": find_captains(picks)
        }
    with(open(f'app/data/gw_teams/filtered/gw_filtered_{gw}.json', 'w')) as f:
        f.write(json.dumps(filtered_gw_picks))
    return filtered_gw_picks


def process_gw_player_teams(gw, gw_standings):
    print("Loading gw picks for all the users")
    complete_gw_picks = {}

    try:
        with(open(f'app/data/gw_teams/all/gw_all_{gw}.json', 'r')) as f:
            complete_gw_picks = json.loads(f.read())
            return filter_all_gw_picks(gw, complete_gw_picks)
    except FileNotFoundError:
        pass

    # fetch the picks for each player
    for player in gw_standings:
        entry_id = player['entry']
        picks = request_data_from_url(
            url_gw_picks.format(entry=entry_id, gw=gw))
        if picks != None:
            complete_gw_picks[entry_id] = picks

    # Save complete gw teams
    with(open(f'app/data/gw_teams/all/gw_all_{gw}.json', 'w')) as f:
        f.write(json.dumps(complete_gw_picks))

    return filter_all_gw_picks(gw, complete_gw_picks)


def get_gw_teams_players(gw, gw_standings):
    try:
        with(open(f'app/data/gw_teams/filtered/gw_filtered_{gw}.json', 'r')) as f:
            return json.loads(f.read())
    except FileNotFoundError:
        return process_gw_player_teams(gw, gw_standings)


def process_total_gw(gw, gw_standings):
    last_gw_total = get_last_gw_standings(gw-1)

    # Get hits/captain/VC/Team Value
    players_gw_teams = get_gw_teams_players(gw, gw_standings)

    final_gw_total = []
    for player in gw_standings:
        try:
            last_gw_points = last_gw_total[str(player['entry'])]['points']
            last_gw_rank = last_gw_total[str(player['entry'])]['rank']
        except KeyError:
            last_gw_points = 0
            last_gw_rank = ''
            # print("no record for last gw" + str(player['entry']))

        try:
            gw_pick = players_gw_teams[str(player["entry"])]
        except KeyError:
            print('No gw picks for player')
            gw_pick = {
                "active_chip": "",
                "itb": 0.0,
                "squad_value": 0.0,
                "transfer_cost": 0,
                "transfers": 0,
                "captains": (0, 0)
            }

        try:
            bank_penalty = 0
            if gw_pick['itb'] > 3.0:
                bank_penalty = 25

            final_gw_total.append({
                'id':  player['id'],
                'player_name':  player['player_name'],
                'entry_name':  player['entry_name'],
                'entry':  player['entry'],
                'event_total':  player['event_total'],
                'last_gw_points': last_gw_points,
                'last_gw_rank': last_gw_rank,
                'total_points': player['event_total'] + last_gw_points + bank_penalty + gw_pick["transfer_cost"],
                "active_chip": gw_pick["active_chip"],
                "itb": gw_pick['itb'],
                "sqaud_value": round(gw_pick["squad_value"] - gw_pick['itb'], 1),
                "transfer_cost": gw_pick["transfer_cost"],
                "captains": gw_pick["captains"],
                "transfers": gw_pick["transfers"],
            })
        except KeyError:
            pass

    # sort the list
    final_gw_total = sorted(final_gw_total, key=itemgetter('total_points'))
    # Add rank value
    for i, item in enumerate(final_gw_total):
        item['rank'] = i+1

    # dump data to gw_standings
    return dump_json_with_time(gw, final_gw_total)


def get_standings_list(url):
    """Return the list that contains the users and their points

    Args:
        url ([type]): [description]

    Returns:
    [{'id': 29643925, 'event_total': 23, 'player_name': 'Danny Wakeling', 'rank': 59, 'last_rank': 50, 'rank_sort': 59, 'total': 180, 'entry': 4505438, 'entry_name': 'Anti Stars'}]
    """

    result_dict = request_data_from_url(url)
    if result_dict == None:
        return []
    return result_dict['standings']['results']


def dump_managers_id(standings):
    d = {}
    for user in standings:
        d[user['player_name']] = user['entry']

    with open('managers_id.json', 'w') as f:
        f.write(json.dumps(d))


def get_live_result():
    """Return the current state of all teams in the mini league

    Returns:
        dictionary : current points of all mini league teams
    """

    standings_list = []
    for i in range(1, 4):
        res = get_standings_list(f"{url_standings_base}{i}")
        standings_list.extend(res)
    # dump_managers_id(standings_list)
    return process_total_gw(find_current_gw(), standings_list)


def fetch_standings():
    # check if the data needs to be fetched // or stored json
    try:
        with open('app/data/gw_standings/standings_current.json', 'r') as file:
            data = json.loads(file.read())
    except:
        return get_live_result()

    updated = data['updated']
    current = calendar.timegm(time.gmtime())

    if current - updated < 200:
        return data
    return get_live_result()


@app.route('/')
def hello():
    standings_data = fetch_standings()
    return render_template('index.html', standings=standings_data['data'], gameweek=standings_data['gameweek'])
