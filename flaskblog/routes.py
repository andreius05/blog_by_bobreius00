import datetime

from flaskblog import app,db,bcrypt,login_manager,socketio
from flask import render_template,url_for,redirect,flash,abort,request,session
from flask_login import current_user,login_user,login_required,logout_user
from flaskblog.models import User,Post,Room
from flaskblog.forms import RegisterForm,LoginForm,CreateRoom,PickRoom,UpdateAccount,CreatePost,UpdPost,SearchForm
from flask_socketio import join_room,leave_room,emit
import secrets
import os
from  PIL import Image





@app.route("/")
def home():
    page = request.args.get('page', 1, type=int)
    posts = Post.query.order_by(Post.date_posted.desc()).paginate(per_page=5, page=page)
    return render_template('home.html',posts=posts)


@app.route("/about")
def about():
    return render_template('about.html')


@app.route("/register",methods=['GET','POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form=RegisterForm()
    if form.validate_on_submit():
        hashed_pw = bcrypt.generate_password_hash(form.password.data)
        user=User(username=form.username.data,email=form.email.data,password=hashed_pw)
        db.session.add(user)
        db.session.commit()
        token=user.generate_confirmation_token()
        return redirect(url_for('login'))
    return render_template('register.html',form=form,title='Register')


@app.route('/login',methods=['GET','POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form=LoginForm()
    if form.validate_on_submit():
        user=User.query.filter_by(email=form.email.data).first()
        if user and bcrypt.check_password_hash(user.password,form.password.data):
            login_user(user)
            flash('You are successful registered','success')
            return redirect(url_for('home'))
        else:
            flash('Please check your email and password body','danger')
            return redirect(url_for('login'))
    return render_template('login.html',form=LoginForm(),title='Log in page')


@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for('home'))


@app.route("/new_chat",methods=['GET','POST'])
@login_required
def new_chat():
    form=CreateRoom()
    if form.validate_on_submit():
        room=Room(title=form.title.data)
        db.session.add(room)
        db.session.commit()
        flash('Your room was created','success')
        return redirect(url_for('pick_room'))
    return render_template('new_chat.html',form=form)


@app.route("/pick_room",methods=['GET','POST'])
@login_required
def pick_room():
    form = PickRoom()
    rooms = Room.query.all()
    form.room.choices = [('Pick room', 'Pick room')] + [(room.id, room.title) for room in rooms]
    if form.validate_on_submit():
        selected_room_id = form.room.data
        selected_room = Room.query.get(selected_room_id)
        if not selected_room:
            return abort(404)
        return redirect(url_for('chat', room_id=selected_room_id))

    return render_template('pick_room.html', form=form)


@app.route("/chat<int:room_id>",methods=['GET','POST'])
@login_required
def chat(room_id):
    room=Room.query.get(room_id)
    session['room_name']=room.title
    if not room:
        abort(404)
    return render_template('chat.html',room=room)


@socketio.on("joined",namespace='/chat')
def joined(message):
    room = session.get('room_name')
    if room:
        join_room(room)
        emit('status', {'msg': f'{current_user.username} has entered the room.'}, room=room)

@socketio.on('text',namespace='/chat')
def text(message):
    room = session.get('room_name')
    if room:
        emit('message', {'msg': f'{current_user.username}: {message["msg"]}'}, room=room)

@socketio.on('left', namespace='/chat')
def left(message):
    room = session.get('room_name')
    if room:
        leave_room(room)
        emit('status', {'msg': f'{current_user.username} has left the room.'}, room=room)


def save_pic(pic):
    random_hex = secrets.token_hex(8)
    _, f_ext = os.path.splitext(pic.filename)
    picture_fn = random_hex + f_ext
    picture_path = os.path.join(app.root_path, 'static/pictures', picture_fn)
    output_size = (125, 125)
    i = Image.open(pic)
    i.thumbnail(output_size)
    i.save(picture_path)
    return picture_fn


@app.route("/account")
def account():
    image_file = url_for('static', filename='pictures/' + current_user.image_file)
    return render_template('account.html', title='Account', image_file=image_file)


@app.route("/update_account", methods=['GET', 'POST'])
@login_required
def update_account():
    form = UpdateAccount()
    if form.validate_on_submit():
        if form.picture.data:
            picture_file = save_pic(form.picture.data)
            current_user.image_file = picture_file
        current_user.username = form.username.data
        current_user.email = form.email.data
        db.session.commit()
        flash('Your account has been updated!', 'success')
        return redirect(url_for('account'))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.email.data = current_user.email
    image_file = url_for('static', filename='pictures/' + current_user.image_file)
    return render_template('update_account.html', title='Account', image_file=image_file, form=form)


@app.route("/create_post",methods=['Get','Post'])
@login_required
def create_post():
    form=CreatePost()
    if form.validate_on_submit():
        post=Post(title=form.title.data,content=form.content.data,author=current_user)
        db.session.add(post)
        db.session.commit()
        flash('Your post was created','success')
        return redirect(url_for('home'))
    return render_template('create_post.html',form=form)



@app.route("/post/<int:post_id>",methods=['GET','POST'])
def post(post_id):
    post=Post.query.get_or_404(post_id)
    return render_template('post.html',post=post)



@app.route("/updatePost/<int:post_id>",methods=['GET','POST'])
@login_required
def updatePost(post_id):
    post=Post.query.get_or_404(post_id)
    form=UpdPost()
    if post.author!=current_user:
        abort(403)
    if form.validate_on_submit():
        post.title=form.title.data
        post.content=form.content.data
        db.session.commit()
        flash('Your account was updated','success')
        return redirect(url_for('post',post_id=post.id))
    return render_template('update_post.html',form=form)



@app.route("/post/<int:post_id>/delete", methods=['GET','POST'])
@login_required
def deletePost(post_id):
    post = Post.query.get_or_404(post_id)
    if post.author != current_user:
        abort(403)
    db.session.delete(post)
    db.session.commit()
    flash('Your post has been deleted!', 'success')
    return redirect(url_for('home'))





@app.route("/user_info/<username>")
def user_info(username):
    user = User.query.filter_by(username=username).first_or_404()
    page = request.args.get('page', 1, type=int)
    posts = Post.query.filter_by(author=user).order_by(Post.date_posted.desc()).paginate(page=page, per_page=5)
    return render_template('user_info.html', user=user, posts=posts)



@app.route("/follow/<username>")
@login_required
def follow(username):
    user=User.query.filter_by(username=username).first()
    if not user:
        flash('User is not exist','danger')
        return redirect(url_for('home'))
    if current_user==user:
        flash('You cant follow yourself bro')
        return redirect(url_for('home'))
    current_user.follow(user)
    db.session.commit()
    flash(f'You are now following {user.username}!', 'success')
    return redirect(url_for('user_info',username=username))

@app.route("/unfollow/<username>")
@login_required
def unfollow(username):
    user = User.query.filter_by(username=username).first()
    if not user:
        flash('User is not exist', 'danger')
        return redirect(url_for('home'))
    if current_user == user:
        flash('You cant unfollow yourself bro','danger')
        return redirect(url_for('home'))
    current_user.unfollow(user)
    db.session.commit()
    flash(f'You are  unfollowed {user.username}!', 'success')
    return redirect(url_for('user_info', username=username))


@app.route("/search",methods=['GET','POST'])
@login_required
def search():
    form=SearchForm()

    if form.validate_on_submit():
        user=User.query.filter_by(username=form.username.data).first()
        if user:
            flash('Here is guy that you searched','success')
            return redirect(url_for('user_info',username=user.username))
        else:
            flash('This user is not exist')
            return redirect(url_for('search'))
    return render_template('search.html',form=form)