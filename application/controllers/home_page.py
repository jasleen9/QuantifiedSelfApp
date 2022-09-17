from flask import Flask, request , redirect , url_for , flash , abort , render_template
from flask import current_app as app
from flask_security import login_required
import flask_login
from application.models import *
from datetime import datetime

# ------------ HOME PAGE ------------------------------------

@app.route('/')
@login_required

def home_page():
    tracker_list = []

    for i in Tracker.query.filter_by(user_id = flask_login.current_user.id).all():

        last_tracked = Tracker_log.query.filter_by(tracker_id = i.id).order_by(Tracker_log.timestamp.desc()).all()
        last_tracked = last_tracked[0].timestamp if last_tracked else "-"

        tracker_list.append({'id' : i.id , 'name' : i.name , 'description': i.description, 'last_tracked':last_tracked})
    return render_template('home.html' , title = 'Home Page' , trackers = tracker_list)