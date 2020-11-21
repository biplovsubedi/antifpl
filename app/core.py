"""
Web Application to keep track of anti fantasy points.

Main File of the flask application. Implements a route to /

"""

import requests
import json
import random

import calendar
import time

from operator import itemgetter
from app.fixtures import fixtures

from app.manager_id_name import managers_name, managers_entry


# Api endpoints for fpl
# Returns the gw points and other details of max 50 users as a page
url_standings_base = "https://fantasy.premierleague.com/api/leagues-classic/307809/standings/?page_standings="
# Returns the live points of all the players in that gw
url_live_gw = "https://fantasy.premierleague.com/api/event/{gw}/live/"
# Returns the gw picks for a manager in a gw
url_gw_picks = "https://fantasy.premierleague.com/api/entry/{entry}/event/{gw}/picks/"
# Returns almost everything about FPL (Here it is used to check if a GW has been completed or not)
url_bootstrap_static = "https://fantasy.premierleague.com/api/bootstrap-static/"

# Contains the date of each gameweek (with deadline)
# TODO Rename to GW
fixture_date_file = 'app/data/fixtures_date.json'


"""
Endpoints:
https://fantasy.premierleague.com/api/entry/4621202/event/4/picks/  -> See picks for a player in a week
History of a player: https://fantasy.premierleague.com/api/entry/4621202/history/
"""


def request_data_from_url(url):
    """Takes a url as an input and fetches JSON data
    to that URL
    Converts JSON to dictionary and returns that to the user.format()

    Args:
        url (string): Complete url of API endpoint

    Returns:
        dict: api response data, None if error
    """
    try:
        res = requests.get(url)
    except:
        return None
    if res.status_code != 200:
        return None

    return json.loads(res.text)


def find_current_gw():
    """Find the gameweek corresponding to the request time
    Uses gameweek fixtures file to match current time to the gw
    {
        "id": 3,
        "name": "Gameweek 3",
        "deadline_time": "2020-09-26T10:00:00Z",
        "deadline_time_epoch": 1601114400
    }
    Smallest unit in epoch time is seconds.

    Returns:
        int: Gamweeek corresponding to the request time, 0 if invalid
    """
    return 9
    # with open(fixture_date_file, 'r') as file:
    #     fixtures = file.read()
    # fixture_d = json.loads(fixtures)
    epoch_time = calendar.timegm(time.gmtime())

    # TODO verify that this delay works
    # 4500s / 75min after the GW deadline
    # GW deadline is roughly 90min / 5400s before first fixture
    for f in fixtures:
        if f['deadline_time_epoch'] + 1 > epoch_time:
            return f['id'] - 1
    return 0


def is_gw_completed(gw):
    """Checks if a certain gameweek has been completed or not
    bootstrap_static contains the GW information in key 'events'
    Each gameweek has 2 parameters 'finished' and 'data_checked'.
    GW is considered completed after both these parameters are set to True

    Args:
        gw (int): gameweek no

    Returns:
        bool: True if Completed, False Otherwise
    """
    bootstrap_static = request_data_from_url(url_bootstrap_static)
    try:
        events = bootstrap_static['events']
    except:
        return False

    for ev in events:
        if ev['id'] == int(gw):
            return ev['finished'] and ev['data_checked']
    return False


def get_gw_players_data(gw):
    """Get data of the players in a given gameweek
    Used to find players' points, minutes, etc

    Args:
        gw ([type]): [description]

    Returns:
        [type]: [description]
    """
    gw_players_data = request_data_from_url(url_live_gw.format(gw=gw))
    try:
        return gw_players_data['elements']
    except KeyError:
        return {}


def get_last_gw_standings(gw):
    """Returns the points/rank information from last gameweek
    This info is used to compare the perfomance of a player in
    a certain GW, compared to the last one.

    Reads the GW file and returns it.
    Args:
        gw (int): gameweek no

    Returns:
        dictionary: last gw points, empty if not found
    """

    last_gw_file = "app/data/gw_jsons/gw_" + str(gw) + ".json"

    try:
        with open(last_gw_file, 'r') as file:
            return json.loads(file.read())
    except FileNotFoundError:
        print("file not found last gw" + last_gw_file)
        return {}


def dump_json_with_time(gw, data, gw_completed):
    """Takes a python datatype and converts it to JSON
    Adds extra meta information around gameweek, updated time and gw status
    gameweek -> used to compare is new gameweek has started
    updated -> To reduce the number of API calls. The file is only
        updated and new API call is made if the new request is beyond
        a certain threshold limit past updated time (current: 200 s)
    status -> To stop the update of certain gw after the gw has been
        completed. Values: ('completed' / 'ongoing')


    Args:
        gw (int): gameweek
        data (dict): data to be saved
        gw_completed (bool): Whether the GW has been completed or not

    Returns:
        dict: dict that has been saved
    """
    location = ['app/data/gw_standings/standings_{gw}.json'.format(
        gw=gw), 'app/data/gw_standings/standings_current.json']
    epoch_time = calendar.timegm(time.gmtime())

    new_dict = {
        'gameweek': gw,
        'updated': epoch_time,
        'data': data,
        'status': 'completed' if gw_completed else 'ongoing'
    }
    for l in location:
        with open(l, 'w') as file:
            file.write(json.dumps(new_dict))
    return new_dict


def find_captains(picks):
    """Find the Captain/Vice Captain picks for a fpl manager
        in a gameweek.
    picks dictionary has a 'picks' key which contains the list of
    selected players for a gw, and their position/captaincy
    Loop in the list and find the player(s) with armband

    Args:
        picks (dict): gameweek picks for a manager

    Returns:
        tuple: id of captain, vice captain
    """
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
    """Filter unnecesssary information from a GW picks for a manager
    GW picks has lot of details including, all players, GW stats for
    a manager.
    Since this is used multiple times, to compute penalties, we filter
    the necessary information only.

    Return format:
    {
        'manager_id' : {
            "active_chip": 'wildcard' ,
            "itb": 2.2,
            "squad_value": 98.2,
            "transfer_cost": 4,
            "transfers": 2,
            "captains": (2,56)
        }
    }

    Args:
        gw (int): gameweek
        complete_gw_picks (dict): Contains the entire information about
        the gw picks for each manager
        Format:
        {
            'manager_id1' : picks,
            'manager_id2' : picks,
            ...
        }

    Returns:
        dict: filtered information on the gw pick
    """
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


def fetch_pick_for_all_players(gw, players_id):
    """For all the players in the league, find their respective
    gameweek picks.
    This information is used to find captains/vice captains, bank/squad value,
    weekly players pick, calcualte penalties.

    Return Format:
    {
        'manager_id1' : picks,
        'manager_id2' : picks,
        ...
    }

    Args:
        gw (int): gameweek
        gw_standings (dict): list of FPL managers in the mini league

    Returns:
        dict: Contains the gw picks information for all managers
    """
    complete_gw_picks = {}
    for entry_id in players_id:
        # entry_id = player['entry']

        picks = request_data_from_url(
            url_gw_picks.format(entry=entry_id, gw=gw))

        if picks != None:
            complete_gw_picks[entry_id] = picks

    # Save complete gw teams
    with(open(f'app/data/gw_teams/all/gw_all_{gw}.json', 'w')) as f:
        f.write(json.dumps(complete_gw_picks))

    return complete_gw_picks


def process_gw_player_teams(gw, gw_standings):
    """Starts the process to load the gw picks for all managers
    Checks if has already been done, return the file if available

    Args:
        gw (int): gameweek
        gw_standings (list): List of all managers in the ML

    Returns:
        dict: Filtered GW picks for all managers
    """
    complete_gw_picks = {}

    try:
        with(open(f'app/data/gw_teams/all/gw_all_{gw}.json', 'r')) as f:
            complete_gw_picks = json.loads(f.read())
            return filter_all_gw_picks(gw, complete_gw_picks)
    except FileNotFoundError:
        pass

    complete_gw_picks = fetch_pick_for_all_players(
        gw, [g['entry'] for g in gw_standings])

    return filter_all_gw_picks(gw, complete_gw_picks)


def get_gw_teams_players(gw, gw_standings):
    """Find the gw picks (filtered for all managers)
    Checks if the file exists, else calls the function to create it

    Args:
        gw (int): gameweek
        gw_standings (list): list of all managers in the ML

    Returns:
        dict: filtered dict on gw picks
    """
    try:
        with(open(f'app/data/gw_teams/filtered/gw_filtered_{gw}.json', 'r')) as f:
            return json.loads(f.read())
    except FileNotFoundError:
        return process_gw_player_teams(gw, gw_standings)


def calculate_player_minutes(gw):
    """Extract the playing minutes for all players in a gw
    Each player has a ton of stats in each GW, Only one that we need
    for processing is the minutes. So we filter out unnecessary
    information
    GW minutes is used to compute inactive players penalties

    Dictionary converstion is done to save lookup time O(N) -> O(1)

    Args:
        gw (int): gameweek

    Returns:
        dict: contains player's id(key) and mintues(val)
    """

    players = get_gw_players_data(gw)

    ret_d = {}
    for p in players:
        ret_d[p['id']] = p['stats']['minutes']
    return ret_d


def calculate_player_points(gw, only_played=False):
    """Extract the playing points for all players in a gw
    Each player has a ton of stats in each GW, Only one that we need
    for processing is the points. So we filter out unnecessary
    information
    GW points is used to compute inactive players penalties

    Dictionary converstion is done to save lookup time O(N) -> O(1)

    Args:
        gw (int): gameweek

    Returns:
        dict: contains player's id(key) and mintues(val)
    """

    players = get_gw_players_data(gw)

    ret_d = {}
    for p in players:
        if only_played and p['stats']['minutes'] == 0:
            continue
        ret_d[p['id']] = p['stats']['total_points']
    return ret_d


def get_gw_all_teams(gw):
    """Return the file that contains the information of all managers, and
    their picks for a gw.format()


    Args:
        gw (int): gameweek

    Returns:
        dict: file contents, {} if file does not exist
    """
    try:
        with(open(f'app/data/gw_teams/all/gw_all_{gw}.json', 'r')) as f:
            return json.loads(f.read())
    except FileNotFoundError:
        last_gw_dict = get_last_gw_standings(gw-1)
        return fetch_pick_for_all_players(gw, last_gw_dict.keys())
        # return {}


def find_inactive_players(picks, player_minutes):
    """Find the number of inactive players for a certian manager
    Loops in the manager picks (players) in a GW and checks if
    the player_minutes
    Find the count of players who are playing -> 'multiplier' != 0
    and minutes != 0.

    Args:
        picks (dict): Contains the information on the manager's GW picks
        player_minutes (dict): Contains the minutes played by all
            players in that GW

    Returns:
        int: Number of starting XI players who didn't play in that GW
    """
    active_cnt = 0
    for p in picks['picks']:
        if p['multiplier'] != 0 and player_minutes[p['element']] != 0:
            active_cnt += 1
    return abs(11 - active_cnt)


def get_inactive_players_penalty(gw, gw_standings):
    """Calculate the penalties for inactive players for each
    manager in the mini league.
    There are 2 sort of inactive penalties:
    1. C/VC penalty -> C/VC failed to play (+15 Points)
    2. Inactive players pen -> Less than 11 players in the staring XI
        player more than 0 minutes (+9 points per player)

    Return Format:
    {
        'manager_id' : {
            'cap_penalty' : 15,
            'inactive_players' : 1,
            'inactive_players_pen' : 9
        },
        ....
    }

    Args:
        gw (int): gameweek
        gw_standings (list): List of managers/info in the ML

    Returns:
        dict: Contains the managers(key) and penalties dict(val)
    """
    # get gw players data
    player_minutes = calculate_player_minutes(gw)

    fetch_pick_for_all_players(gw, [g['entry'] for g in gw_standings])
    gw_teams_all = get_gw_all_teams(gw)

    ret_d = {}
    for id, picks in gw_teams_all.items():
        ret_d[id] = {}
        cap, vc = find_captains(picks)
        if player_minutes[cap] == 0 and player_minutes[vc] == 0:
            ret_d[id]['cap_penalty'] = 15
        else:
            ret_d[id]['cap_penalty'] = 0

        inactive_players = find_inactive_players(picks, player_minutes)
        ret_d[id]['inactive_players'] = inactive_players
        ret_d[id]['inactive_players_pen'] = 9 * inactive_players

    return ret_d


def get_teams_data(teams):

    try:
        with(open('app/data/teams_meta.json', 'r')) as f:
            return json.loads(f.read())
    except:
        pass

    return_d = {}

    for t in teams:
        return_d[int(t['id'])] = {
            'name': t['name'],
            'short_name': t['short_name'],
            'code': t['code']
        }
    with(open('app/data/teams_meta.json', 'w')) as f:
        f.write(json.dumps(return_d))
    return return_d


def get_players_metadata():
    """Returns the metadata of each player

    # Refresh each week ??

    Returns:
        [type]: [description]
    """

    try:
        with(open('app/data/players_metadata.json', 'r')) as f:
            return json.loads(f.read())
    except FileNotFoundError:
        pass

    bootstrap_static_data = request_data_from_url(url_bootstrap_static)

    teams_data = get_teams_data(bootstrap_static_data['teams'])

    players_dict = {}
    for p in bootstrap_static_data['elements']:
        try:
            team = teams_data[p['team']]
        except KeyError:
            team = teams_data[str(p['team'])]
        players_dict[p['id']] = {
            'position': p['element_type'],
            'web_name': p['web_name'],
            'team_id': team,
            'team_name': team['name'],
            'team_short_name': team['short_name']
        }
    with(open('app/data/players_metadata.json', 'w')) as f:
        f.write(json.dumps(players_dict))
    return players_dict


def fetch_dream_team(gw):

    # Find all the players in a GW
    players_points = calculate_player_points(gw, only_played=True)
    players_metadata = get_players_metadata()

    # sort players points in ascending order -> cast to list
    keys = list(players_points.keys())
    random.shuffle(keys)

    # players_points = sorted([(k, players_points[k])
    #                          for k in keys], key=lambda item: item[1])

    players_points_ = {k: players_points[k] for k in keys}

    players_points = sorted(players_points_.items(), key=lambda item: item[1])

    dream_team = {
        '1': [],
        '2': [],
        '3': [],
        '4': []
    }
    total_points = 0
    honorable_mentions = {
        '1': [],
        '2': [],
        '3': [],
        '4': []
    }

    # represents max number of players in a position
    # 1 GK, 2 DEF, 3 MID, 4 FWD
    max_pos = [0, 1, 5, 5, 3]
    # print(players_points[:20])
    for p in players_points:
        try:
            player = players_metadata[str(p[0])]
        except KeyError:
            player = players_metadata[int(p[0])]

        # find position
        pos = player['position']

        is_def_mid_full = (pos == 2 or pos == 3) and len(
            dream_team['2']) + len(dream_team['3']) == 9
        is_gk_remaining = len(dream_team['1']) == 0 and len(
            dream_team['2']) + len(dream_team['3']) + len(dream_team['4']) == 10
        is_mid_fwd_full = (pos == 3 or pos == 4) and len(
            dream_team['3']) + len(dream_team['4']) == 7

        if (max_pos[pos]) == 0 or is_def_mid_full or is_mid_fwd_full or (is_gk_remaining and pos != 1) or sum(max_pos) == 3:
            # Add players with same points as the last person in dream to honorable mentions

            if len(dream_team[str(pos)]) > 0 and p[1] == dream_team[str(pos)][-1]['points']:
                honorable_mentions[str(pos)].append({
                    'name': player['web_name'],
                    'points': p[1],
                    'team': player['team_short_name'],
                    'id': str(p[0])
                })

            continue
        # All 11 players selected
        # This is causing some players to miss out
        if sum(max_pos) == 3:
            continue

        max_pos[pos] -= 1

        dream_team[str(pos)].append({
            'name': player['web_name'],
            'points': p[1],
            'team': player['team_short_name'],
            'id': str(p[0])
        })
        total_points += p[1]

    dream_team['total'] = total_points
    return (dream_team, honorable_mentions)


def get_dream_team(gw=None):
    # find gw

    curr_gw_ = find_current_gw()
    try:
        gw = int(gw)
    except:
        gw = curr_gw_

    if gw == None or int(gw) >= int(curr_gw_) or int(gw) < 1:
        gw = curr_gw_

    current = calendar.timegm(time.gmtime())
    try:
        with(open(f'app/data/dream/{gw}.json', 'r')) as f:
            data = json.loads(f.read())
            if data['completed'] == True or current - data['updated'] < 1000:
                return data
    except FileNotFoundError:
        pass

    gw_completed_ = is_gw_completed(gw)

    dream_team = fetch_dream_team(gw)
    final_dict = {
        'updated': calendar.timegm(time.gmtime()),
        'data': dream_team,
        'completed': gw_completed_,
        'gameweek': gw
    }

    with(open(f'app/data/dream/{gw}.json', 'w')) as f:
        f.write(json.dumps(final_dict))
    return final_dict


def process_total_gw(gw, gw_standings, gw_completed_=False):
    """Main function that processes all the GW information

    Gets the information (points, rank) from the last gameweek
    Gets the team value, transfer hits for all managers

    Checks if the gw is completed:
        Gets the C/VC, inactive players penalties for all managers

    Note: C/VC, inactive players penalties only added after GW completed

    For each player in the minileague, computes all of these information

    Sorts the list on the final points tally, creates rankings, and stores
    this information as stadings_{gw} / standings_current JSON files.

    NOTE: The returned list is used to create the table on the Front End

    Args:
        gw (int): gameweek
        gw_standings (list): list of managers in the ML

    Returns:
        list: Contains the final informtion of all managers to be displayed
    """
    last_gw_total = get_last_gw_standings(gw-1)

    # Get hits/captain/VC/Team Value
    players_gw_teams = get_gw_teams_players(gw, gw_standings)

    # check if gw is completed
    inactive_players_penalties = {}
    if(gw_completed_):
        inactive_players_penalties = get_inactive_players_penalty(
            gw, gw_standings)

    # print(inactive_players_penalties)

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
            cap_penalty = inactive_players_penalties[str(
                player['entry'])]['cap_penalty']
            inactive_players = inactive_players_penalties[str(
                player['entry'])]['inactive_players']
            inactive_players_pen = inactive_players_penalties[str(
                player['entry'])]['inactive_players_pen']
        except:
            cap_penalty = 0
            inactive_players = 0
            inactive_players_pen = 0

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
                'final_gw_points': player['event_total'] + bank_penalty + gw_pick["transfer_cost"] + int(cap_penalty) + int(inactive_players_pen),
                'total_points': player['event_total'] + last_gw_points + bank_penalty + gw_pick["transfer_cost"] + cap_penalty + inactive_players_pen,
                "active_chip": gw_pick["active_chip"],
                "itb": gw_pick['itb'],
                # "sqaud_value": round(gw_pick["squad_value"] - gw_pick['itb'], 1),
                "sqaud_value": gw_pick["squad_value"],
                "transfer_cost": gw_pick["transfer_cost"],
                "captains": gw_pick["captains"],
                "transfers": gw_pick["transfers"],
                "cap_penalty": cap_penalty,
                "inactive_players": inactive_players,
                'inactive_players_pen': inactive_players_pen

            })
        except KeyError:
            pass

    # sort the list
    final_gw_total = sorted(final_gw_total, key=itemgetter('total_points'))
    # Add rank value
    for i, item in enumerate(final_gw_total):
        item['rank'] = i+1

    # dump data to gw_standings and status == finished
    return dump_json_with_time(gw, final_gw_total, gw_completed_ and inactive_players_penalties != {})


def get_standings_list(url):
    """Return the list that contains the users and their points

    Args:
        url (string): url corresponding to the milileage page

    Returns:
        list: List of managers in that page of Mini league
    [{'id': 29643925, 'event_total': 23, 'player_name': 'Danny Wakeling', 'rank': 59,
        'last_rank': 50, 'rank_sort': 59, 'total': 180, 'entry': 4505438, 'entry_name': 'Anti Stars'}]
    """

    result_dict = request_data_from_url(url)
    if result_dict == None:
        return []
    return result_dict['standings']['results']


def dump_managers_id(standings):
    """Utility function used to store the manager's name, id
    Not used in the actual app, but used to map the managers from
    the google sheet CSV

    Args:
        standings (list): All managers in the ML
    """
    d = {}
    for user in standings:
        d[user['player_name']] = user['entry']

    with open('managers_id.json', 'w') as f:
        f.write(json.dumps(d))


def calculate_live_points(players, points):

    count = 0
    for p in players:
        count += p["multiplier"] * points[p["element"]]
    return count


def get_live_points(gw):

    points = calculate_player_points(gw)
    all_teams = get_gw_all_teams(gw)

    last_gw_total = get_last_gw_standings(gw-1)
    final_gw_total = []
    for manager_id, gw_data in all_teams.items():

        try:
            last_gw_points = last_gw_total[str(manager_id)]['points']
            last_gw_rank = last_gw_total[str(manager_id)]['rank']
        except KeyError:
            last_gw_points = 0
            last_gw_rank = ''

        gw_points = calculate_live_points(gw_data["picks"], points)
        bank_penalty = 25 if gw_data["entry_history"]["bank"] > 30 else 0
        gw_points_with_pen = gw_points + bank_penalty + \
            gw_data["entry_history"]["event_transfers_cost"]
        total_points = last_gw_points + gw_points_with_pen

        manager_d = {
            'player_name':  managers_name[manager_id],
            'entry_name':  managers_entry[manager_id],
            'entry':  int(manager_id),
            'event_total': gw_points,
            'last_gw_points': last_gw_points,
            'last_gw_rank': last_gw_rank,
            'final_gw_points': gw_points_with_pen,
            'total_points': total_points,
            "active_chip": gw_data["active_chip"],
            "itb": float(gw_data["entry_history"]["bank"])/10.0,
            "sqaud_value": float(gw_data["entry_history"]["value"])/10.0,
            "transfer_cost": gw_data["entry_history"]["event_transfers_cost"],
            "transfers": gw_data["entry_history"]["event_transfers"]
        }
        final_gw_total.append(manager_d)

    # sort the list
    final_gw_total = sorted(final_gw_total, key=itemgetter('total_points'))
    # Add rank value
    for i, item in enumerate(final_gw_total):
        item['rank'] = i+1

    # dump data to gw_standings and status == finished
    return dump_json_with_time(gw, final_gw_total, False)


def get_live_result():
    """Return the current state of all teams in the mini league

    Note: At a time we can fetch 50 managers from a ML
    Since we have 131 managers atm, we send paginated request 3 times

    Returns:
        dictionary : current points of all mini league teams
    """

    gw = find_current_gw()
    gw_completed_ = is_gw_completed(gw)

    standings_list = []

    if not gw_completed_:
        return get_live_points(gw)

    for i in range(1, 4):
        res = get_standings_list(f"{url_standings_base}{i}")
        standings_list.extend(res)
    # dump_managers_id(standings_list)
    return process_total_gw(gw, standings_list, gw_completed_)


def fetch_standings():
    """Get the standings/data of all the managers to display in the app

    Main function called from the react controller, to get the acutal
    managers data

    Checks if the standings_current file is available, else compute it

    Finds if the status of gw in the file is completed or not
        if yes, finds if the current gameweek is same as the one in the file
        if yes, no futher computation required, return file data

    Finds when the data in the file was updated
        If less than 200 sec ago, return the data from the file

    Only compute new, if the above conditions don't satisfy

    Returns:
        list: List of managers data to be displayed
    """
    # check if the data needs to be fetched // or stored json
    try:
        with open('app/data/gw_standings/standings_current.json', 'r') as file:
            data = json.loads(file.read())
    except:
        return get_live_result()

    updated = data['updated']
    try:
        status = data['status']
    except KeyError:
        status = "ongoing"
    gameweek = data['gameweek']

    if status == 'completed' and gameweek == find_current_gw():
        return data

    current = calendar.timegm(time.gmtime())

    if current - updated < 500:
        return data
    return get_live_result()
