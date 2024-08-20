from datetime import datetime, timedelta
from authlib.jose import jwt
from flaskblog import db, login_manager, app
from flask_login import UserMixin
from itsdangerous import URLSafeTimedSerializer as Serializer



@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))



class Follow(db.Model):
    follower_id=db.Column(db.Integer,db.ForeignKey('user.id'),primary_key=True)
    followed_id=db.Column(db.Integer,db.ForeignKey('user.id'),primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)


class User( db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    image_file = db.Column(db.String(20), nullable=False, default='default.jpg')
    password = db.Column(db.String(60), nullable=False)
    posts = db.relationship('Post', backref='author', lazy=True)
    followed=db.relationship('Follow',foreign_keys=[Follow.follower_id],backref=db.backref('follower', lazy='joined'),
                             lazy='dynamic',
                             cascade='all, delete-orphan')
    followers=db.relationship('Follow',foreign_keys=[Follow.followed_id],backref=db.backref('followed', lazy='joined'),
                                lazy='dynamic',
                                cascade='all, delete-orphan')

    def follow(self, user):
        if not self.is_following(user):
            f = Follow(follower=self, followed=user)
            db.session.add(f)
    def unfollow(self,user):
        f = self.followed.filter_by(followed_id=user.id).first()
        if f:
            db.session.delete(f)
    def is_following(self,user):
        return self.followed.filter_by(
            followed_id=user.id).first() is not None
    def is_followed_by(self,user):
        return self.followers.filter_by(
            follower_id=user.id).first() is not None



    def __repr__(self):
        return f"User('{self.username}', '{self.email}', '{self.image_file}', '{self.password}')"

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    date_posted = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    content = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    def __repr__(self):
        return f"Post('{self.title}', '{self.date_posted}')"


class Room(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)


    def __repr__(self):
        return f"{self.title}"

