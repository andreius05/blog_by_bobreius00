import datetime
import time
from .easy_lvl import minimax
from . import app,db,bcrypt,login_manager,socketio,mail,cache
from flask import render_template,url_for,redirect,flash,abort,request,session,jsonify
from flask_login import current_user,login_user,login_required,logout_user
from .models import User,Post,Message,Comment,Group,Game
from .forms import (RegisterForm,LoginForm,UpdateAccount,CreatePost,UpdPost,SearchForm,MessageForm,ResetPasswordFormRequest
,ResetPasswordForm,CommentForm,CommentUpdateForm,CreateGroupForm)
from flask_socketio import join_room,leave_room,emit
import secrets
import os
from  PIL import Image
from sqlalchemy import or_,and_
import requests


api_key = 'd7dfed5410094f82a4a4e91abf4c8572'


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
    current_page=request.path
    print(f"THIS IS CURRENT PAGE:{current_page}")
    page = request.args.get('page', 1, type=int)
    posts = Post.query.order_by(Post.date_posted.desc()).paginate(per_page=5, page=page)
    users=User.query.all()
    print(users)
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
        user=User.query.filter(
            or_(
                User.username==form.login.data,
                User.email==form.login.data
            )
        ).first()
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
    user_chats=[]
    if users:
        for user in users:
            room_name = get_room_name(current_user.username,user.username)
            messages = Message.query.filter(
                or_(
                    and_(Message.sender_id == current_user.id, Message.recipient_id == user.id),
                    and_(Message.sender_id == user.id, Message.recipient_id == current_user.id)
                )
            ).order_by(Message.timestamp.asc()).all()
            messages_data=[]
            for message in messages:
                sender = User.query.get(message.sender_id)
                sender_username = sender.username if sender else "Unknown"
                messages_data.append({
                    'id': message.id,
                    'sender': sender.username,
                    'body': message.body,
                    'timestamp': message.timestamp.strftime('%Y-%m-%d %H:%M:%S')
                })
            

            if messages_data:
                last_message_data=messages_data[-1]
                user_chat_info={
                    'user':user,
                    'room_name':room_name,
                    'last_message':last_message_data['body'],
                    'last_message_time':last_message_data['timestamp'],
                    'last_message_sender':last_message_data['sender']

                }
                user_chats.append(user_chat_info)
        return render_template('chats.html',user_chats=user_chats)


            
            
            
        return render_template('chats.html',users=users,room=room,last_message=last_message,
                            timing_last_messages=timing_last_messages,last_sender=last_sender)
    else:
        flash('You have no friends hahahaha','danger')
        return redirect(url_for('search'))


@app.route("/chat/<recipient_username>", methods=['GET', 'POST'])
@login_required
def chat(recipient_username):
    current_page=request.path
    print(f"CURRENT PAGE:{current_page}")
    recipient = User.query.filter_by(username=recipient_username).first()
    return render_template('chat.html', recipient=recipient)


def get_room_name(user1,user2):
    return f"{min(user1,user2)}_{max(user1,user2)}"


@socketio.on('join', namespace='/chat')
def join(message):
    recipient = User.query.filter_by(username=message['recipient']).first()
    room = get_room_name(current_user.username, message['recipient'])
    print(f"ROOM:{room}")
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
    current_page=request.path
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
    form=CommentForm()
    post=Post.query.get_or_404(post_id)
    if form.validate_on_submit():
        if current_user.is_authenticated:
            comment=Comment(author_id=current_user.id,content=form.content.data,post_id=post_id)
            db.session.add(comment)
            db.session.commit()
            return redirect(url_for('post',post_id=post_id))
        flash('You need to be logged to comment','danger')
    comments = post.comments.order_by(Comment.timestamp.asc()).all()
    return render_template('post.html',post=post,comments=comments,form=form)




#



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
        search_tag=form.guy_searched.data
        users=User.query.filter(User.username.ilike(f"%{search_tag}%")).all()
        if users:
            flash('Here is guys that you searched','success')
            return render_template('searched.html',users=users)
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


@app.route("/like_post_home/<int:post_id>")
@login_required
def like_post_home(post_id):
    post=Post.query.get(post_id)
    post.like(current_user)
    return redirect(url_for('home'))

@app.route("/like_post/<int:post_id>")
@login_required
def like_post(post_id):
    post=Post.query.get_or_404(post_id)
    post.like(current_user)
    return redirect(url_for('post',post_id=post_id))




@app.route("/unlike_post_home/<int:post_id>",methods=['GET','POST'])
@login_required
def unlike_post_home(post_id):
    post = Post.query.get_or_404(post_id)
    post.unlike(current_user)
    return redirect(url_for('home'))


@app.route("/unlike_post/<int:post_id>")
@login_required
def unlike_post(post_id):
    post=Post.query.get_or_404(post_id)
    post.unlike(current_user)
    return redirect(url_for('post',post_id=post_id))





@app.route("/post_likes/<int:post_id>")
@login_required
def post_likes(post_id):
    post=Post.query.get_or_404(post_id)
    likers=post.get_likers()
    return render_template('post_likes.html',likers=likers,post=post)


@app.route("/commentUpdate/<int:comment_id>/<int:post_id>",methods=['GET','POST'])
@login_required
def commentUpdate(comment_id,post_id):
    form=CommentUpdateForm()
    comment = Comment.query.get_or_404(comment_id)
    if form.validate_on_submit():
        comment.content=form.content.data
        db.session.commit()
        flash('Your comment was updated','success')
        return redirect(url_for('post',post_id=post_id))
    form.content.data=comment.content
    return render_template('commentUpdate.html',post_id=post_id,form=form,comment=comment)


@app.route("/commentDelete/<int:post_id>/<int:comment_id>")
@login_required
def commentDelete(post_id,comment_id):
    comment=Comment.query.get(comment_id)
    if comment:
        db.session.delete(comment)
        db.session.commit()
        flash('Your comment was deleted ','success')
    else:
        flash('Comment was not found ','danger')
    return redirect(url_for('post',post_id=post_id))




@app.route('/create_group',methods=['GET','POST'])
@login_required
def create_group():
    user=User.query.filter_by(username=current_user.username).first()
    users=[f.followed for f in user.followed.all()]
    form=CreateGroupForm()
    if form.validate_on_submit():
        print('VALIIIIIIDATEEEED')
        group=Group(name=form.group_name.data)
        db.session.add(group)
        db.session.commit()

        selected_users=User.query.filter(User.id.in_(form.add_members.data)).all()
        print(f"SELECTEEED USERSSS:{selected_users}")

        for sl_user in selected_users:
            print(f"IM SELECTEEED :{sl_user}")
            group.members.append(sl_user)
        db.session.commit()
        flash('You are successfully created group','success')
        return redirect(url_for('chat_group',id=group.id))
    else:
        print("VALIDATION FAILED", form.errors, request.form)
    return render_template('create_group.html',form=form,users=users)



@app.route("/chat_group/<int:id>")
@login_required
def chat_group(id):
    group=Group.query.get_or_404(id)
    print(group)
    users=group.members
    print(f"USERS:{users}")
    return render_template('chat_group.html',users=users)


@app.route("/all_post_comments/<int:post_id>",methods=['GET','POST'])
def all_post_comments(post_id):
    post=Post.query.get(post_id)
    form=CommentForm()
    if form.validate_on_submit():
        if current_user.is_authenticated:
            comment=Comment(author_id=current_user.id,content=form.content.data,post_id=post_id)
            db.session.add(comment)
            db.session.commit()
            return redirect(url_for('post',post_id=post_id))
        flash('You need to be logged to comment','danger')
    comments = post.comments.order_by(Comment.timestamp.asc()).all()
    print(comments)
    return render_template('all_post_comments.html',comments=comments,form=form)

@app.route("/create_game",methods=['GET','POST'])
def create_game():
    game=Game(name='chess')
    db.session.add(game)
    db.session.commit()

    return "Created"


@app.route("/delete_game",methods=['GET','POST'])
def delete_game():
    game=Game.query.filter_by(name='chess').first()
    db.session.delete(game)
    db.session.commit()
    return f"{game.name} was deleted"

@app.route("/games/<username>")
def games(username):
    print(f"GAMES:{Game.query.all()}")
    games_obj=Game.query.all()
    games=[names.name for names in games_obj]
    print(games)
    return render_template('games.html',games=games_obj)


@app.route("/game/<name>",methods=['GET','POST'])
def game(name):
    return render_template('choose.html',name=name)


@app.route("/easy_lvl")
def easy_lvl():
    return render_template('easy_tictactoe.html')


@app.route("/mid_lvl")
def mid_lvl():
    return render_template('mid_tictactoe.html')


@app.route("/hard_lvl")
def hard_lvl():
    return render_template('hard_tictactoe.html')


@app.route("/game/ai_move_noob", methods=["POST"])
def ai_move_noob():
    data = request.get_json()  # Ensure JSON is parsed
    board = data.get("board")

    # Call the minimax function or other AI logic here
    ai_action = minimax(board,easy=True)

    # Return the AI's move as JSON
    return jsonify({"row": ai_action[0], "col": ai_action[1]})


@app.route("/game/ai_move_mid", methods=["POST"])
def ai_move_mid():
    data = request.get_json()  # Ensure JSON is parsed
    board = data.get("board")

    # Call the minimax function or other AI logic here
    ai_action = minimax(board,mid=True)

    # Return the AI's move as JSON
    return jsonify({"row": ai_action[0], "col": ai_action[1]})


@app.route("/game/ai_move_hard", methods=["POST"])
def ai_move_hard():
    data = request.get_json()  # Ensure JSON is parsed
    board = data.get("board")

    # Call the minimax function or other AI logic here
    ai_action = minimax(board,hard=True)

    # Return the AI's move as JSON
    return jsonify({"row": ai_action[0], "col": ai_action[1]})


@app.route("/get_ip")
@login_required
def get_ip():
    url = f'https://api.ipgeolocation.io/ipgeo?apiKey={api_key}'
    response = requests.get(url)
    ip_info  =response.json()
    ip = ip_info.get('ip')
    country = ip_info.get('country_name')
    return f"THIS YOUR IP:{ip},AND YOUR COUNTRY IS:{country}"