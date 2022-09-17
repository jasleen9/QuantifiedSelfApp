from flask import current_app as app
from flask import Flask , request , redirect , url_for , flash , abort , render_template

import flask_login
from flask_security import login_required

from flask_wtf import FlaskForm
from wtforms import (StringField , TextAreaField , SelectField , HiddenField)
from wtforms.validators import InputRequired , Length , AnyOf , ValidationError

from datetime import datetime , timedelta
from application.models import *
import collections


#---------------------- TRACKER VALIDATION ------------------------------

tracker_types = ['ms' , 'integer' , 'float']

def check_tid(form, field):
    #one_or_none : Return at most one result or raise an exception. Returns None if the query selects no rows.
    tracker_data = Tracker.query.filter_by(user_id = flask_login.current_user.id , id = form.tid.data).one_or_none()
    if not tracker_data:
        raise ValidationError("Something wrong with Tracker id")

class Add_Tracker_Form(FlaskForm):
    tname = StringField('Tracker Name', validators=[InputRequired(), Length(min=4, max=50)])
    tdescription = TextAreaField('Tracker Description', validators=[Length(max=255)])
    ttype = SelectField('Tracker Type', choices=tracker_types, validators=[InputRequired(), AnyOf(tracker_types, message='Invalid Type supplied')])
    tchoices = TextAreaField('Multi Select choices')
    
class Edit_Tracker_Form(Add_Tracker_Form):
    tid = HiddenField('Current Tracker ID', validators = [InputRequired(), check_tid])
    oldtype = HiddenField('Old Tracker Type', validators = [InputRequired(), AnyOf(tracker_types, message="Old validator is of invalid type")])


#----------------------- CREATE NEW TRACKER -----------------------------


@app.route('/tracker/add' , methods = ['GET' , 'POST'])
@login_required
def add_tracker():
    if request.method == 'GET':
        return render_template('tracker/edit_add_tracker.html' , title = 'Add New Tracker')
    else:
        add_form = Add_Tracker_Form()     

        if not add_form.validate_on_submit():
            flash('Error in creating new tracker' , 'error')
            return render_template('tracker/edit_add_tracker.html', title='Add Tracker', form=add_form, retry=True)
        try:
            #get new tracker's values
            new_tracker = Tracker(name = request.form['tname'], description = request.form['tdescription'] , user_id = flask_login.current_user.id)
            # add value of new tracker to database
            db.session.add(new_tracker)
            db.session.commit()
        except:
            # handle internal error
            app.logger.exception('Error occured while creating new tracker')
            #last session changes are rolled back
            db.session.rollback()
            # flash error message
            flash('Error occured in creating new tracker, please try again' , 'error')
            return redirect(url_for('add_tracker'))

        try:
            ttype = request.form['ttype']

            # for multi-select tracker type

            if ttype == 'ms':
                #new choice after pressing 'Enter'
                tchoices = request.form['tchoices'].strip().split('\n')
                # adding choices to database
                for i in tchoices:
                    new_choice = Tracker_type(tracker_id = new_tracker.id, datatype = ttype , value = i.strip())
                    db.session.add(new_choice)


            elif ttype == 'float':
                new_choice = Tracker_type(tracker_id  = new_tracker.id, datatype = ttype, value = None)
                db.session.add(new_choice)


            elif ttype == 'integer':
                new_choice = Tracker_type(tracker_id  = new_tracker.id, datatype = ttype, value = None)
                db.session.add(new_choice)

            #commit all changes
            db.session.commit()

        except:
            # some internal error occurred
            app.logger.exception('Error occurred while adding Tracker Type to the new tracker.')
            # rollback whatever the last session changes were.
            db.session.rollback()            
            # set error flash message
            flash('There was an error setting the tracker type, please edit the tracker info to change the type', 'error')
            # redirect to home page
            return redirect(url_for('home_page'))

        # set success flask message to be displayed on home page
        flash('Tracker added successfully' , 'success')

        return redirect(url_for('home_page'))




# -------------------------------- SHOW TRACKER INFO ------------------------------------------

@app.route('/tracker/<int:id>/show', methods = ['GET', 'POST'], defaults= {'period': 'w'})
@app.route('/tracker/<int:id>/show/<string:period>', methods = ['GET', 'POST'])
@login_required
def show_tracker_log(id, period):
    # check if a tracker with the provided id and made by current user exists or not.
    tracker_data = Tracker.query.filter_by(user_id=flask_login.current_user.id, id=id).one_or_none()
    # if it exists, proceed.
    if tracker_data:
        datatypes = list(set([i.datatype for i in tracker_data.ttype]))
        tdata = {
            'id': tracker_data.id,
            'name': tracker_data.name,
            'description': tracker_data.description,
            'user_id': tracker_data.user_id,
            'type': datatypes[0] if len(datatypes) > 0 else '',
            'choices': {i.id: (i.value.strip() if i.value else '') for i in tracker_data.ttype}
        }
        log_data = []
        chart_data = {}
        for i in tracker_data.values:
            this_data = {
                'id': i.id,
                'timestamp': i.timestamp,
                'note': i.note,
                'value': [tdata['choices'][int(x.value)] for x in i.values] if tdata['type'] == 'ms' else [x.value for x in i.values]
            }
            log_data.append(this_data)

            if tdata['type'] == 'ms':                
                options = list(set(this_data['value']))
                for i in options:
                    if i in chart_data:
                        chart_data[i] += this_data['value'].count(i)
                    else:
                        chart_data[i] = this_data['value'].count(i)
            
            else:          
                include = False      
                difference_in_time = datetime.today() - this_data['timestamp']
                if period == 'w' and difference_in_time.days <= 7:
                    ts = datetime.strftime(i.timestamp, "%Y-%m-%d")
                    include = True
                elif period == 'm' and difference_in_time.days <= 30:
                    ts = datetime.strftime(i.timestamp, "%Y-%m-%d")                
                    include = True
                elif period == 'd' and difference_in_time.days <= 0:
                    ts = datetime.strftime(i.timestamp, "%H:%M")                    
                    include = True
                elif period == 'a':
                    ts = datetime.strftime(i.timestamp, "%Y-%m-%d")
                    include = True
                
                if include:
                    if ts in chart_data:
                        chart_data[ts] += int("".join(this_data['value'])) if tdata['type'] == 'integer' else float("".join(this_data['value']))
                    else:
                        chart_data[ts] = int("".join(this_data['value'])) if tdata['type'] == 'integer' else float("".join(this_data['value']))

        if tdata['type'] != 'ms':
            if period == 'w':
                delta = 7
                for i in range(delta):
                    key = datetime.strftime(datetime.today()-timedelta(i), "%Y-%m-%d")
                    if key not in chart_data:
                        chart_data[key] = 0
            elif period == 'm':
                delta = 30
                for i in range(delta):
                    key = datetime.strftime(datetime.today()-timedelta(i), "%Y-%m-%d")
                    if key not in chart_data:
                        chart_data[key] = 0
            elif period == 'd':
                delta = 24
                for i in range(delta):
                    key = datetime.strftime(datetime.today()-timedelta(hours=i), "%H:00")
                    if key not in chart_data:
                        chart_data[key] = 0
        
        return render_template('tracker/show.html', tracker = tdata, logs = log_data, period = period, total=len(tracker_data.values), chart=collections.OrderedDict(sorted(chart_data.items())))



#-----------------------------------DELETE TRACKER PAGE----------------------------------------------------------


@app.route('/tracker/<int:id>/delete', methods = ['GET'])
@login_required
def delete_tracker(id):
    # check if a tracker with the provided id and made by current user exists or not.
    tracker_data = Tracker.query.filter_by(user_id=flask_login.current_user.id, id=id).one_or_none()
    # if it exists, proceed.
    if tracker_data:
        try:            
            db.session.delete(tracker_data)
            db.session.commit()
        except:
            app.logger.exception(f'Error ocurred while deleting tracker with id {id}')
            # if any internal error occurs, rollback the database
            db.session.rollback()
            flash('Internal error occurred, wasn\'t able to delete tracker', 'error')
            return redirect(url_for('home_page'))
        
        flash('Succesfully deleted tracker', 'success')
        return redirect(url_for('home_page'))
    else:
        abort(404)



#----------------------EDIT TRACKER PAGE---------------------------------------------------------------

@app.route('/tracker/<int:id>/edit', methods = ['GET', 'POST'])
@login_required
def edit_tracker(id):
    # if the request method is get
    # check if a tracker with the provided id and made by current user exists or not.
    tracker_data = Tracker.query.filter_by(user_id=flask_login.current_user.id, id=id).one_or_none()
    # if it exists, proceed.
    if tracker_data:            
        # get datatype of the tracker
        datatypes = list(set([i.datatype for i in tracker_data.ttype]))
        # collect all the data about the current tracker being edited.
        data = {
            'id': tracker_data.id,
            'name': tracker_data.name,
            'description': tracker_data.description,
            'user_id': tracker_data.user_id,
            # set datatype to empty if no type is defined earlier
            'type': datatypes[0] if len(datatypes) > 0 else '',
            # get all the choices of the tracker, replace NULL values with ''
            'choices': [(i.id, (i.value if i.value else '')) for i in tracker_data.ttype] if len(datatypes) > 0 else ''
        }
        if request.method == 'GET':
            flash('Opened tracker', 'info')
            return render_template('tracker/edit_add_tracker.html', title=f'Edit Tracker {id}', edit_mode=True, tracker=data)
                
        else:
            edit_form = Edit_Tracker_Form()
            # if it exists, proceed. Additionally also check if tracker url id and form hidden field id matches or not.
            if not edit_form.validate_on_submit():
                flash('Validation error occurred while editing tracker', 'error')
                return render_template('tracker/add_edit.html', form=edit_form, retry=True, title=f'Edit Tracker {id}', edit_mode=True, tracker=data)

            if id == int(request.form['tid']):
                try:
                    # update values of tracker
                    tracker_data.name = request.form['tname']
                    tracker_data.description = request.form['tdescription']

                    
                    

                    # add new data types for the tracker
                    ttype = request.form['ttype']
                    oldtype = request.form['oldtype']

                    if oldtype != ttype:
                        for i in tracker_data.ttype:
                            db.session.delete(i)
                        # if tracker type is multiple select
                        if ttype == 'ms':
                            # get all the choices splitted across the \n
                            tchoices = request.form['tchoices'].strip().split('\n')
                            # add each choice to the database
                            for i in tchoices:
                                new_choice = Tracker_type(tracker_id  = tracker_data.id, datatype = ttype, value = i)
                                db.session.add(new_choice)
                        
                        # if tracker type is integer values
                        elif ttype == 'integer':
                            new_choice = Tracker_type(tracker_id  = tracker_data.id, datatype = ttype, value = None)
                            db.session.add(new_choice)
                        
                        # if tracker type is float values
                        elif ttype == 'float':
                            new_choice = Tracker_type(tracker_id  = tracker_data.id, datatype = ttype, value = None)
                            db.session.add(new_choice)
                    
                    else:
                        # if tracker type is multiple select
                        if ttype == 'ms':

                            old_ids = tracker_data.ttype
                            for x in old_ids:
                                new_value = request.form[f'tchoices_edit{x.id}']
                                if new_value != '':
                                    x.value = new_value
                                else:
                                    vals = db.delete(Tracker_log_value).where(Tracker_log_value.value.in_([x.id]))                                    
                                    db.session.execute(vals)
                                    db.session.delete(x)
                            
                            # if newly added choices.
                            tchoices = request.form['tchoices'].strip().split('\n')
                            # add each choice to the database
                            for i in tchoices:
                                if i != '':
                                    new_choice = Tracker_type(tracker_id  = tracker_data.id, datatype = ttype, value = i)
                                    db.session.add(new_choice)

                    
                    # commit all the above changes to the database
                    db.session.commit()
                
                except:
                    app.logger.exception(f'Error ocurred while editing tracker with id {id}')
                    # if any internal error occurs, rollback the database
                    db.session.rollback()
                    flash('Internal error occurred, wasn\'t able to update tracker', 'error')
                    return redirect(url_for('edit_tracker', id=id))
                
                flash('Succesfully updated tracker info', 'success')
                return redirect(url_for('home_page'))
            else:
                abort(404)
    else:
        abort(404)

