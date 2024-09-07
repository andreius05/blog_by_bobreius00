import datetime

from flaskblog import app,db,bcrypt,login_manager,socketio,mail,cache
from flask import render_template,url_for,redirect,flash,abort,request,session
from flask_login import current_user,login_user,login_required,logout_user
from flaskblog.models import User,Post,Message
from flaskblog.forms import RegisterForm,LoginForm,UpdateAccount,CreatePost,UpdPost,SearchForm,MessageForm,ResetPasswordFormRequest,ResetPasswordForm
from flask_socketio import join_room,leave_room,emit
import secrets
import os
from  PIL import Image
from sqlalchemy import or_,and_
from flaskblog.emails import send_email

#ERRRORS
@app.errorhandler(404)
def not_find_error(error):
    print("SJHDHSJDHJHSD")
    return render_template('404error.html'),404


@app.errorhandler(500)
def server_bug_error(error):
    print("SOSIIIIII")
    return render_template('500error.html'),500



#ERRORS
@app.route("/")
def home():
    page = request.args.get('page', 1, type=int)
    posts = Post.query.order_by(Post.date_posted.desc()).paginate(per_page=5, page=page)
    return render_template('home.html',posts=posts)


@app.route("/about")
def about():
    return render_template('about.html')




@app.route('/reset_password_request',methods=['GET','POST'])
def reset_password_request():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form=ResetPasswordFormRequest()
    if form.validate_on_submit():
       user=User.query.filter_by(email=form.email.data).first()
       if user:
           send_email(user)
           flash('Check the email to reset your password')
           return redirect(url_for('login'))
    return render_template('reset_password_request.html',form=form,user=user)


@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
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
    return render_template('reset_password.html', form=form)



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
        return redirect(url_for('login'))
    return render_template('register.html',form=form,title='Register')


@app.route('/login',methods=['GET','POST'])
#@cache.cached(timeout=60)
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

@app.route("/chats/<username>")
@login_required
def chats(username):
    contacts = db.session.query(Message.sender_id, Message.recipient_id).filter(
        or_(
            Message.sender_id == current_user.id,
            Message.recipient_id == current_user.id
        )
    ).all()
    user_ids=set()
    for sender_id,recipient_id in contacts:
        if sender_id!=current_user.id:
            user_ids.add(sender_id)
        if recipient_id!=current_user.id:
            user_ids.add(recipient_id)
    users = User.query.filter(User.id.in_(user_ids)).all()

    for user in users:
        pass

    return render_template('chats.html',users=users)


@app.route("/chat/<recipient_username>", methods=['GET', 'POST'])
@login_required
def chat(recipient_username):
    recipient = User.query.filter_by(username=recipient_username).first()
    return render_template('chat.html', recipient=recipient)


def get_room_name(user1,user2):
    return f"{min(user1,user2)}_{max(user1,user2)}"


@socketio.on('join', namespace='/chat')
def join(message):
    recipient = User.query.filter_by(username=message['recipient']).first()
    room = get_room_name(current_user.username, message['recipient'])
    if not room:
        abort(403)
    join_room(room)
    messages = Message.query.filter(
        or_(
            and_(Message.sender_id == current_user.id, Message.recipient_id == recipient.id),
            and_(Message.sender_id == recipient.id, Message.recipient_id == current_user.id)
        )
    ).order_by(Message.timestamp.asc()).all()
    messages_data = []
    print(f"{messages_data}")
    for message in messages:
        sender = User.query.get(message.sender_id)
        sender_username = sender.username if sender else "Unknown"
        messages_data.append({
            'id': message.id,
            'sender': sender.username,
            'body': message.body,
            'timestamp': message.timestamp.strftime('%Y-%m-%d %H:%M:%S')
        })

    emit('history', {'messages': messages_data})


@socketio.on('text', namespace='/chat')
def text(message):
    recipient=User.query.filter_by(username=message['recipient']).first()
    room = get_room_name(current_user.username, message['recipient'])

    new_message = Message(
        sender_id=current_user.id,
        recipient_id=User.query.filter_by(username=message['recipient']).first().id,
        body=message['msg']
    )

    db.session.add(new_message)
    db.session.commit()

    emit('message', {'msg': f'{current_user.username}: {message["msg"]}'}, room=room)
    if socketio.server.manager.rooms.get(room):
        print("HE is IN THE FUCKING CHAT")
        emit('message', {'msg': f'{current_user.username}: {message["msg"]}'}, room=room)
    else:
        emit('new_notification', {'msg': f'Новое сообщение от {current_user.username}'}, room=recipient.username)

@socketio.on('leave', namespace='/chat')
def leave(message):
    room = get_room_name(current_user.username, message['recipient'])
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


@app.route("/followers/<username>")
@login_required
def followers(username):
    user = User.query.filter_by(username=username).first_or_404()
    users = [f.follower for f in user.followers.all()]
    return render_template('user_list.html', users=users, user=user)


@app.route("/followed/<username>")
@login_required
def followed(username):
    user = User.query.filter_by(username=username).first_or_404()
    users = [f.followed for f in user.followed.all()]
    return render_template('user_list.html', users=users, user=user)
