from flask import render_template, flash, redirect, url_for, request
from app import app_name, db
from app.forms import LoginForm, RegistrationForm, EditProfileForm, \
    PostForm, ResetPasswordRequestForm, ResetPasswordForm
from flask_login import current_user, login_user, logout_user, login_required
from app.models import User, Post
from app.email import send_password_reset_email
from werkzeug.urls import url_parse
from datetime import datetime
import random

@app_name.route('/', methods = ['GET', 'POST'])
@app_name.route('/index', methods = ['GET', 'POST'])
@login_required
def index():
    cnt = len(Post.query.all())
    rand_num = random.randint(1, cnt)
    posts = Post.query.get(rand_num)

    return render_template('index.html', title = 'Home', posts = posts) #,form)

@app_name.route('/history')
@login_required
def history():
    '''Show all facts about Greenfield & Brownfield'''
    page = request.args.get('page', 1, type = int)
    posts = Post.query.order_by(Post.id).paginate(
        page, app_name.config['POSTS_PER_PAGE'], False)

    next_url = url_for('history', page = posts.next_num) if posts.has_next \
        else None
    prev_url = url_for('history', page = posts.prev_num) if posts.has_prev \
        else None
    
    return render_template('history.html', title = 'History', 
        posts = posts.items, next_url = next_url, prev_url = prev_url)

@app_name.route('/login', methods = ['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    form = LoginForm()

    if form.validate_on_submit(): #When click submit
        user = User.query.filter_by(username = form.username.data).first()    
        
        if user is None or not user.check_password(form.password.data):
            flash('Invalid username or password')
            return redirect(url_for('login'))

        login_user(user, remember = form.remember_me.data)
        next_page = request.args.get('next')

        if not next_page or url_parse(next_page).netloc != '':
            next_page = url_for('index')

        return redirect(next_page)

    return render_template('login.html', title = 'Sign In', form = form)

@app_name.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))

@app_name.route('/register', methods = ['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    form = RegistrationForm()

    if form.validate_on_submit(): #When click submit
        user = User(
            username = form.username.data, 
            email = form.email.data
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('You have registered a new account.')
        return redirect(url_for('login'))

    return render_template('register.html', title = 'Sign Up', form = form)

@app_name.route('/user/<username>', methods = ['GET', 'POST']) # <..> has dynamic content inside
@login_required
def user(username):
    '''profile page'''
    user = User.query.filter_by(username = username).first_or_404()
    
    page = request.args.get('page', 1, type = int)

    form = PostForm()

    if form.validate_on_submit(): #add new informative post
        post = Post(
            body = form.post.data.encode('utf-8'), 
            author = current_user
        )
        db.session.add(post)
        db.session.commit()
        flash('Your post has been accepted! Thanks for contribution.')
        return redirect(url_for('user', username = user.username))

    posts = Post.query.filter_by(user_id = current_user.id).paginate(
        page, app_name.config['POSTS_PER_PAGE_USER'], False)

    next_url = url_for('user', username = user.username, page = posts.next_num) \
        if posts.has_next else None
    
    prev_url = url_for('user', username = user.username, page = posts.prev_num) \
        if posts.has_prev else None

    return render_template('user.html', user = user, form = form, 
        posts = posts.items, next_url = next_url, prev_url = prev_url)

@app_name.route('/edit_profile', methods = ['GET', 'POST'])
@login_required
def edit_profile():
    form = EditProfileForm(current_user.username)

    if form.validate_on_submit():
        current_user.username = form.username.data
        current_user.about_me = form.about_me.data
        db.session.commit()
        flash('Changes have been saved')
        return redirect(url_for('edit_profile'))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.about_me.data = current_user.about_me
    return render_template('edit_profile.html', title = 'Edit Profile',
        form = form)

@app_name.route('/reset_password_request', methods = ['GET', 'POST'])
def reset_password_request():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = ResetPasswordRequestForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email = form.email.data).first()
        if user:
            send_password_reset_email(user)
        flash('Check your email for the instructions to reset'\
            ' your password')
        return redirect(url_for('login'))
    return render_template('reset_password_request.html', title = 'Reset'\
        'Password', form = form )

@app_name.route('/reset_password/<token>', methods = ['GET', 'POST'])
def reset_password(token):
    '''firstly make sure that person is not authorized (otherwise redirect),
    then let him change the password if token is valid'''
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    user = User.verify_reset_password_token(token)
    if not user:
        return redirect(url_for('index'))

    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)
        db.session.commit()
        flash('Your password has been reset.')
        return redirect(url_for('login'))
    return render_template('reset_password.html', form = form)