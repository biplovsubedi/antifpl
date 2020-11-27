import json

import calendar
import time
from flask import Flask, render_template

from app.core import find_current_gw, request_data_from_url, get_gw_all_teams, get_gw_players_data, is_gw_completed


def sort_dictionary_by_val(d):
    return {k: v for k, v in sorted(d.items(), key=lambda item: item[1])}


def add_player_metadata(players):

    # get metadata
    with open('app/data/players_metadata.json') as f:
        p_meta = json.loads(f.read())

    ret_l = []
    for id, sel in players.items():
        ret_l.append({
            'id': str(id),
            'selection': sel,
            'name': p_meta[str(id)]['web_name'],
            'team': p_meta[str(id)]['team_short_name']
        })
    return ret_l


def get_picks_static(gw):
    """Create a static dictionary that holds the following
    information for the gameweek.
    1. starting_xi - count of selection of each player in each squad xi
    2. squad_xv - count of selection of each player in each squad
    3. captains - count of captaincy pick of each player
    4. cvc - count of captain/vice captain picks of each player

    Args:
        gw ([type]): [description]
        all_teams ([type]): [description]

    Returns:
        [type]: [description]
    """

    try:
        with open(f'app/data/stats/static_{gw}.json', 'r') as f:
            return json.loads(f.read())
    except FileNotFoundError:
        pass

    all_teams = get_gw_all_teams(gw)

    ret_d = {
        'starting_xi': {},
        'squad_xv': {},
        'captains': {},
        'cvc': {}
    }
    for team in all_teams.values():

        for player in team['picks']:
            try:
                ret_d['squad_xv'][str(player['element'])] += 1
            except KeyError:
                ret_d['squad_xv'][str(player['element'])] = 1
            if player['multiplier'] != 0:
                try:
                    ret_d['starting_xi'][str(player['element'])] += 1
                except KeyError:
                    ret_d['starting_xi'][str(player['element'])] = 1

            if player['is_vice_captain'] or player['is_captain']:
                try:
                    ret_d['cvc'][str(player['element'])] += 1
                except KeyError:
                    ret_d['cvc'][str(player['element'])] = 1
            if player['is_captain']:
                try:
                    ret_d['captains'][str(player['element'])] += 1
                except KeyError:
                    ret_d['captains'][str(player['element'])] = 1

    # Sort the results
    ret_d['starting_xi'] = sort_dictionary_by_val(ret_d['starting_xi'])
    ret_d['squad_xv'] = sort_dictionary_by_val(ret_d['squad_xv'])
    ret_d['captains'] = sort_dictionary_by_val(ret_d['captains'])
    ret_d['cvc'] = sort_dictionary_by_val(ret_d['cvc'])

    # Add metadata to stats dict
    ret_d['starting_xi'] = add_player_metadata(ret_d['starting_xi'])[::-1]
    ret_d['squad_xv'] = add_player_metadata(ret_d['squad_xv'])[::-1]
    ret_d['captains'] = add_player_metadata(ret_d['captains'])[::-1]
    ret_d['cvc'] = add_player_metadata(ret_d['cvc'])[::-1]

    with open(f'app/data/stats/static_{gw}.json', 'w') as f:
        f.write(json.dumps(ret_d))

    return json.loads(json.dumps(ret_d))


def calculate_player_stats(gw):
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
        ret_d[str(p['id'])] = {
            'minutes': p['stats']['minutes'],
            'points': p['stats']['total_points']
        }
    return json.loads(json.dumps(ret_d))


def get_picks_dynamic(gw, picks_static):

    player_stats = calculate_player_stats(gw)

    for p in picks_static['starting_xi']:
        p['minutes'] = player_stats[p['id']]['minutes']
        p['points'] = player_stats[p['id']]['points']

    for p in picks_static['squad_xv']:
        p['minutes'] = player_stats[p['id']]['minutes']
        p['points'] = player_stats[p['id']]['points']

    for p in picks_static['captains']:
        p['minutes'] = player_stats[p['id']]['minutes']
        p['points'] = player_stats[p['id']]['points']

    for p in picks_static['cvc']:
        p['minutes'] = player_stats[p['id']]['minutes']
        p['points'] = player_stats[p['id']]['points']

    return picks_static


def get_statistics(gw=None):

    gw = gw or find_current_gw()
    current = calendar.timegm(time.gmtime())
    try:
        with open(f'app/data/stats/dynamic_{gw}.json', 'r') as f:
            data = json.loads(f.read())
            if data['completed'] == True or current - data['updated'] < 1000:
                return data
    except FileNotFoundError:
        pass

    picks_static = get_picks_static(gw)
    picks_dynamic = get_picks_dynamic(gw, picks_static)

    dynamic_dict = {
        'gameweek': gw,
        'completed': is_gw_completed(gw),
        'data': picks_dynamic,
        'updated': calendar.timegm(time.gmtime())
    }

    with open(f'app/data/stats/dynamic_{gw}.json', 'w') as f:
        f.write(json.dumps(dynamic_dict))
    return json.loads(json.dumps(dynamic_dict))
