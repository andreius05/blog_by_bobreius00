from datetime import datetime, timedelta
from authlib.jose import jwt
from flaskblog import db, login_manager, app
from flask_login import UserMixin
from itsdangerous import URLSafeTimedSerializer as Serializer
import jwt
from time import time


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))



class Follow(db.Model):
    follower_id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)
    followed_id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    follower = db.relationship('User', foreign_keys=[follower_id], back_populates='followed')
    followed = db.relationship('User', foreign_keys=[followed_id], back_populates='followers')


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    image_file = db.Column(db.String(20), nullable=False, default='default.jpg')
    password = db.Column(db.String(60), nullable=False)
    posts = db.relationship('Post', backref='author', lazy=True)

    # Use back_populates to refer to the properties defined in Follow
    followed = db.relationship('Follow', foreign_keys='Follow.follower_id',
                               back_populates='follower', lazy='dynamic',
                               cascade='all, delete-orphan')
    followers = db.relationship('Follow', foreign_keys='Follow.followed_id',
                                back_populates='followed', lazy='dynamic',
                                cascade='all, delete-orphan')

    sent_messages = db.relationship('Message', foreign_keys='Message.sender_id',
                                    back_populates='sender', lazy=True)
    received_messages = db.relationship('Message', foreign_keys='Message.recipient_id',
                                        back_populates='recipient', lazy=True)
    groups=db.relationship('Group', secondary='user_groups', back_populates='members')
    def follow(self, user):
        if not self.is_following(user):
            f = Follow(follower=self, followed=user)
            db.session.add(f)
            db.session.commit()

    def unfollow(self, user):
        f = self.followed.filter_by(followed_id=user.id).first()
        if f:
            db.session.delete(f)
            db.session.commit()

    def is_following(self, user):
        return self.followed.filter_by(followed_id=user.id).first() is not None

    def is_followed_by(self, user):
        return self.followers.filter_by(follower_id=user.id).first() is not None

    def get_reset_password_token(self, expires_in=600):
        return jwt.encode(
            {'reset_password': self.id, 'exp': time() + expires_in},
            app.config['SECRET_KEY'], algorithm='HS256')

    @staticmethod
    def verify_reset_password_token(token):
        try:
            id = jwt.decode(token, app.config['SECRET_KEY'],
                            algorithms=['HS256'])['reset_password']
        except:
            return
        return db.session.get(User, id)

    
    def __repr__(self):
        return f"User('{self.username}', '{self.email}', '{self.image_file}')"


class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    recipient_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    is_read=db.Column(db.Boolean,default=False)


    sender = db.relationship('User', foreign_keys=[sender_id], back_populates='sent_messages')
    recipient = db.relationship('User', foreign_keys=[recipient_id], back_populates='received_messages')

    def __repr__(self):
        return f"Message('{self.body}', '{self.timestamp}')"


class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    date_posted = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    content = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    comments = db.relationship('Comment', backref='post', lazy='dynamic')
    post_likes = db.relationship('Like', back_populates='post', lazy='dynamic')

    def is_liking(self, user):
        if user.is_authenticated:
            return Like.query.filter_by(post_id=self.id, man_that_likes_id=user.id).first() is not None
        return False
    def like(self, user):
        if user.is_authenticated:
            if not self.is_liking(user):
                like = Like(man_that_likes=user, post=self)
                db.session.add(like)
                db.session.commit()
        else:
            pass

    def unlike(self, user):
        if user.is_authenticated:
            like = Like.query.filter_by(post_id=self.id, man_that_likes_id=user.id).first()
            if like:
                db.session.delete(like)
                db.session.commit()
        else:
            pass

    def get_likers(self):
        likes = Like.query.filter_by(post_id=self.id).all()
        likers = [User.query.get(like.man_that_likes_id) for like in likes]
        return likers

    def __repr__(self):
        return f"Post('{self.title}', '{self.date_posted}')"

class Comment(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    content=db.Column(db.Text)
    timestamp=db.Column(db.DateTime,index=True,default=datetime.utcnow())
    author_id=db.Column(db.Integer,db.ForeignKey('user.id'))
    post_id=db.Column(db.Integer,db.ForeignKey('post.id'))
    author = db.relationship('User', backref='comments')


class Like(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    man_that_likes_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'))
    man_that_likes = db.relationship('User', backref='user_likes')
    post = db.relationship('Post', back_populates='post_likes')
    is_liking = db.Column(db.Boolean, default=False)

    def __repr__(self):
        return f"Like('{self.man_that_likes_id}', '{self.post_id}')"


class Group(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    name=db.Column(db.String(80),nullable=False)
    members=db.relationship('User',secondary='user_groups',back_populates='groups')



user_groups=db.Table('user_groups',
                     db.Column('user_id',db.Integer,db.ForeignKey('user.id'),primary_key=True)
                     ,db.Column('group_id',db.Integer,db.ForeignKey('group.id'),primary_key=True))

