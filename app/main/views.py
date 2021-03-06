from flask import render_template, flash, url_for, session, redirect, request, jsonify, current_app as app
from ..models import User, Event, User_Event
from .. import db
from . import main
from .forms import ApplicationForm, OriginatingForm
from flask_login import current_user, login_required
import os

@main.route('/', methods=['GET', 'POST'])
def index():
	if current_user.is_authenticated:
		events = Event.query.all()
		return render_template('index.html', events=events)
	flash("Please login first.")
	return redirect(url_for('auth.login'))

@main.route('/event/<event_id>')
@login_required
def showEvent(event_id):
	e = Event.query.filter_by(event_id=event_id).first()
	host = User.query.filter_by(user_id=e.host_id).first()
	record = User_Event.query.filter_by(attendee_id=current_user.user_id, event_id=event_id).first()
	statusTxt = None
	if record is not None:
		if record.status is 1:
			statusTxt = '已申请'
		if record.status is 2:
			statusTxt = '已通过'
		if record.status is 3:
			statusTxt = '未通过'
	return render_template('event/event.html', host=host, e=e, statusTxt=statusTxt)

@main.route('/apply/<event_id>', methods=['GET', 'POST'])
@login_required
def apply(event_id):
	applicationForm = ApplicationForm()
	event = Event.query.filter_by(event_id=event_id).first()
	attendee = current_user
	host = User.query.filter_by(user_id=event.host_id).first()
	if host == attendee:
		flash('不能申请参与自己的项目!')
		return redirect(url_for('.showEvent', event_id=event_id))
	if applicationForm.validate_on_submit(): # 提交申请表并且不为空
		if User_Event.query.filter_by(attendee_id=attendee.user_id, event_id=event_id).first() is not None:
			flash('不能重复提交.')
		else:
			record = User_Event(attendee_id=attendee.user_id, event_id=event_id, status=1, form=applicationForm.text.data)
			db.session.add(record)
			db.session.commit()
			flash('Success!')
		return redirect(url_for('.showEvent', event_id=event_id))
	return render_template('event/apply.html', event=event, form=applicationForm)

@main.route('/manageApplicants/<event_id>', methods=['GET'])
@login_required
def showManagingTable(event_id):
	event = Event.query.filter_by(event_id=event_id).first()
	user = User.query.filter_by(user_id=event.host_id).first()

	if user.username is not current_user.username:
		flash('不是你发起的活动！')
		return redirect(url_for('.showEvent', event_id=event_id))

	rows = db.session.execute('SELECT `User`.`user_id` AS `attendee_id`,\
		`User`.`username` AS `attendee_name`,\
		`User_Event`.`ue_id`, `User_Event`.`event_id`, `User_Event`.`status`, `User_Event`.`form`\
		FROM User INNER JOIN User_Event\
		ON User.user_id=User_Event.attendee_id\
		WHERE event_id=:e', \
		{ "e": event.event_id })
	return render_template('event/manageApplicants.html', rows=rows)

@main.route('/operateAttendee')
@login_required
def operateAttendee():
	ue_id = request.args.get('id', type=int)
	newStatus = request.args.get('newStatus', type=int)
	# update database…
	record = User_Event.query.filter_by(ue_id=ue_id).one()
	record.status = newStatus
	db.session.commit()
	return jsonify(success=True)

@main.route('/hostings')
@login_required
def showHostings():
	hostings = Event.query.filter_by(host_id=current_user.user_id).all()
	return render_template('page/hostings.html', hostings=hostings)

@main.route('/applicantions')
@login_required
def showApplications():
	records = User_Event.query.filter_by(attendee_id=current_user.user_id).all()
	applications = db.session.execute('SELECT * \
		FROM Event INNER JOIN User_Event \
		ON Event.event_id=User_Event.event_id WHERE User_Event.attendee_id=:a', \
		{"a": current_user.user_id })
	return render_template('page/applications.html', applications=applications)

@main.route('/originate', methods=['GET', 'POST'])
@login_required
def originate():
	form = OriginatingForm()
	if form.validate_on_submit():
		event = Event(host_id=current_user.user_id, title=form.title.data, \
			description=form.description.data, city=form.city.data, \
			location=form.location.data, date=form.date.data)
		if form.quota_limit.data is not None:
			event.quota_limit = form.quota_limit.data
		if form.poster is not None:
			file = form.poster.data
			event.poster = file.filename
			file.save(os.path.join(app.config['UPLOAD_FOLDER'], file.filename))
		db.session.add(event)
		db.session.commit()
		flash('Success!')
		return redirect(url_for('.showEvent', event_id=event.event_id))
	return render_template('page/originate.html', form=form)

@main.route('/delete/<event_id>', methods=['GET', 'POST'])
@login_required
def delete(event_id):
	to_delete = Event.query.filter_by(event_id=event_id).one()
	print("to_delete:")
	print(to_delete)
	if to_delete.host_id != current_user.user_id:
		flash("You can't delete event hosted by others.")
	else: # 执行
		# 移除图片文件
		poster = to_delete.poster
		os.remove(os.path.join(app.config['UPLOAD_FOLDER'], str(poster)))
		# 删除 User_Event 表相关的数据
		records = User_Event.query.filter_by(event_id=event_id).all()
		for r in records:
			db.session.delete(r)
		db.session.commit()
		# 删除 Event 表中该行
		db.session.delete(to_delete)
		db.session.commit()

		flash("Success.")
	return redirect(url_for('.index'))














