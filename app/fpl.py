"""
Web Application to keep track of anti fantasy points.

Main File of the flask application. Implements a route to /

"""
import io
from flask import Flask, render_template

from app.core import fetch_standings, get_dream_team, find_current_gw
from app.stats import get_statistics

fplapp = Flask(__name__)


@fplapp.route('/')
def hello():
    """Entry point for the flask app
    Only route '/' is defined for now

    Gets the managers' standings list and uses it to render the html

    Returns:
        html template: rendered HTML template with the standings data
    """
    standings_data = fetch_standings()
    return render_template('index.html', standings=standings_data['data'], gameweek=standings_data['gameweek'], status=standings_data['status'])


@fplapp.route('/dream')
def dream_team():
    """
    Controller for dream team view
    """
    final_dict = get_dream_team()
    return render_template('dreamteam.html',
                           dteam=final_dict['data'][0],
                           hmention=final_dict['data'][1],
                           gameweek=final_dict['gameweek'],
                           gameweeks=int(final_dict['gameweek']),
                           status="Completed" if final_dict['completed'] == True else "Ongoing")


@fplapp.route('/dream<gw>')
def dream_team_gw(gw):
    final_dict = get_dream_team(gw)
    return render_template('dreamteam.html',
                           dteam=final_dict['data'][0],
                           hmention=final_dict['data'][1],
                           gameweek=final_dict['gameweek'],
                           gameweeks=find_current_gw(),
                           status="Completed" if final_dict['completed'] == True else "Ongoing")


@fplapp.route('/stats')
def gw_statistics():
    """Controller to render the gw stats view
    """
    stats_dict = get_statistics()
    return render_template('stats.html',
                           gameweek=stats_dict['gameweek'],
                           status="Completed" if stats_dict['completed'] == True else "Ongoing",
                           data=stats_dict['data']
                           )


# @fplapp.route('/stats_treemap')
# def get_stats_treemap():
#     fig = create_figure()
#     output = io.BytesIO()
