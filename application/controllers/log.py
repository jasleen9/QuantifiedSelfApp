from flask import current_app as app
from flask import Flask, url_for , redirect , flash , abort , render_template , request

from flask_wtf import FlaskForm

from wtforms import (StringField , TextAreaField , SelectField , HiddenField , DateTimeField , IntegerField)
from wtforms.validators import InputRequired, Length , AnyOf , ValidationError
from application.models import *
from flask_security import login_required
import flask_login
from datetime import datetime


date_format = '%m/%d/%Y, %I:%M:%S %p'

#------------------------------LOG VALIDATION-------------------------------------------------

def check_tracker_id_exists(form, field):
    tracker_data = Tracker.query.filter_by(user_id=flask_login.current_user.id, id=form.tid.data).one_or_none()
    if not tracker_data:
        raise ValidationError("Don't mess around with Tracker ID")

def check_log_id_exists(form,field):
    check_tracker_id_exists(form, field)
    log_data = Tracker_log.query.filter_by(tracker_id=form.tid.data, id=form.lid.data).one_or_none()
    if not log_data:
        raise ValidationError("Don't mess around with Log ID")

def lvalue_check(form, field):
    if field:
        check_tracker_id_exists(form, field)
        tracker_data = Tracker.query.filter_by(user_id=flask_login.current_user.id, id=form.tid.data).one_or_none()
        datatype = list(set([i.datatype for i in tracker_data.ttype]))
        datatype = datatype[0] if len(datatype) > 0 else ''

        if datatype == 'integer':
            try:
                int(field.data)
            except:
                raise ValidationError('Input must be Integer')
        elif datatype == 'float':
            try:
                float(field.data)
            except:
                raise ValidationError('Input must be float')
        
class Add_Log_Form(FlaskForm):
    ldate = DateTimeField('Timestamp', format=date_format, validators=[InputRequired()])
    tid = HiddenField("Tracker ID", validators=[InputRequired(), check_tracker_id_exists])
    lvalue = StringField("Value", validators=[lvalue_check])
    lnote = TextAreaField("Note", validators=[Length(max=255)])

class Edit_Log_Form(Add_Log_Form):
    lid = HiddenField("Log ID" , validators = [InputRequired() , check_log_id_exists])



#-----------------------ADD TRACKER LOG--------------------------------------------------------------

@app.route('/tracker/<int:id>/log/add', methods = ['GET', 'POST'])
@login_required
def add_tracker_log(id):
    tracker_data = Tracker.query.filter_by(user_id=flask_login.current_user.id, id=id).one_or_none()
    if tracker_data :
        datatypes = list(set([i.datatype for i in tracker_data.ttype]))
        data = {
            'id': tracker_data.id,
            'name': tracker_data.name,
            'description': tracker_data.description,
            'user_id': tracker_data.user_id,
            'type': datatypes[0] if len(datatypes) > 0 else '',
            'choices': {i.id: (i.value if i.value else '') for i in tracker_data.ttype}
        }

        if request.method == 'GET':
            return render_template('tracker/log.html' , tracker = data)
        else:
            add_form = Add_Log_Form()
            if not add_form.validate_on_submit():
                flash('Validation error occured while logging tracker' , 'error')
                return render_template('tracker/log.html' ,  title='Log Tracker', form=add_form, retry=True, tracker=data, date_format=date_format)

            if request.form['tid'] == str(id):
                try:
                    log = Tracker_log(tracker_id = tracker_data.id, note = request.form['lnote'], timestamp = datetime.strptime(request.form['ldate'], '%m/%d/%Y, %I:%M:%S %p'))
                    db.session.add(log)
                    db.session.commit()
                except:
                    app.logger.exception(f'Error ocurred while adding tracker log')
                    # database rolled back if error occurs
                    db.session.rollback()
                    flash('Internal error occurred, wasn\'t able to add tracker log', 'error')
                    return redirect(url_for('home_page'))

                try:
                    if data['type'] == 'ms':
                        choices = request.form.getlist('lchoice')
                        for i in choices:
                            x = Tracker_log_value(log_id = log.id, value = i)
                            db.session.add(x)                    
                        db.session.commit()
                    
                    else:
                        x = Tracker_log_value(log_id = log.id, value = int(request.form['lvalue']) if data['type'] == 'integer' else float(request.form['lvalue']))
                        db.session.add(x)
                        db.session.commit()
                except:
                    app.logger.exception(f'Error ocurred while adding tracker log value')
                    # if any internal error occurs, rollback the database
                    db.session.rollback()
                    flash('Internal error occurred, wasn\'t able to add tracker log value', 'error')
                    return redirect(url_for('add_tracker_log', id=id))

                flash('Succesfully Saved tracker log', 'success')
                return redirect(url_for('show_tracker_log', id=id))
            else:
                abort(404)
    
    else:
        abort(404)




# -----------------------------------------EDIT TRACKER LOG------------------------------------------------------------------

@app.route('/tracker/<int:tracker_id>/log/<int:log_id>/edit', methods = ['GET', 'POST'])
@login_required
def edit_tracker_log(tracker_id, log_id):
    tracker_data = Tracker.query.filter_by(user_id=flask_login.current_user.id, id=tracker_id).one_or_none()
    if tracker_data:
        log_data = Tracker_log.query.filter_by(tracker_id=tracker_data.id, id=log_id).one_or_none()
        if log_data:
            datatypes = list(set([i.datatype for i in tracker_data.ttype]))
            tdata = {
                'id': tracker_data.id,
                'name': tracker_data.name,
                'description': tracker_data.description,
                'user_id': tracker_data.user_id,
                'type': datatypes[0] if len(datatypes) > 0 else '',
                'choices': {i.id: (i.value.strip() if i.value else '') for i in tracker_data.ttype}
            }

            ldata = {
                'id': log_data.id,
                'timestamp': datetime.strftime(log_data.timestamp, date_format),
                'note': log_data.note,
                'value': [i.value for i in log_data.values]
            }

            if request.method == 'GET':
                return render_template('tracker/log.html', title='Edit Log', edit_mode = True, tracker = tdata, log = ldata)
            
            else:
                edit_form = Edit_Log_Form()
                if not edit_form.validate_on_submit():
                    flash('Validation error occurred while editing tracker log', 'error')
                    return render_template('tracker/log.html', title='Edit Log', edit_mode=True, form=edit_form, retry=True, tracker=tdata, log=ldata, date_format=date_format)
                
                if request.form['tid'] == str(tracker_data.id) and request.form['lid'] == str(log_data.id):
                    try:
                        log_data.timestamp = datetime.strptime(request.form['ldate'], '%m/%d/%Y, %I:%M:%S %p')
                        log_data.note = request.form['lnote']
                        
                        for i in log_data.values:
                            db.session.delete(i)

                        if tdata['type'] == 'ms':
                            choices = request.form.getlist('lchoice')
                            for i in choices:
                                x = Tracker_log_value(log_id = log_data.id, value = i)
                                db.session.add(x)
                        
                        else:
                            x = Tracker_log_value(log_id = log_data.id, value = request.form['lvalue'])
                            db.session.add(x)
                        
                        db.session.commit()
                    except:
                        app.logger.exception(f'Error ocurred while editing tracker log with id {log_id}')
                        # if any internal error occurs, rollback the database
                        db.session.rollback()
                        flash('Internal error occurred, wasn\'t able to update tracker log value', 'error')
                        return redirect(url_for('show_tracker_log', id=tracker_id))
                    
                    flash('Succesfully updated tracker log', 'success')
                    return redirect(url_for('show_tracker_log', id=tracker_id))
                else:
                    abort(404)
        else:
            abort(404)
    else:
        abort(404)


# -----------------------------------DELETE TRACKER LOG--------------------------------------------------------


@app.route('/tracker/<int:tracker_id>/log/<int:log_id>/delete', methods = ['GET'])
@login_required
def delete_tracker_log(tracker_id, log_id):
    # check if a tracker with the provided id and made by current user exists or not.
    tracker_data = Tracker.query.filter_by(user_id=flask_login.current_user.id, id=tracker_id).one_or_none()
    # if it exists, proceed.
    if tracker_data:
        log_data = Tracker_log.query.filter_by(tracker_id=tracker_data.id, id=log_id).one_or_none()
        if log_data:
            try:            
                db.session.delete(log_data)
                db.session.commit()
            except:
                app.logger.exception(f'Error ocurred while deleting tracker log with id {log_id}')
                # if any internal error occurs, rollback the database
                db.session.rollback()
                flash('Internal error occurred, wasn\'t able to delete tracker log', 'error')
                return redirect(url_for('home_page'))
        
            flash('Succesfully deleted tracker log', 'success')
            return redirect(url_for('show_tracker_log', id=tracker_id))
        else:
            abort(404)
    else:
        abort(404)