from flask_wtf import FlaskForm
from wtforms.validators import DataRequired,Email,equal_to,Length,ValidationError
from wtforms import StringField,IntegerField,SubmitField,BooleanField,PasswordField,SelectField,TextAreaField
from flaskblog.models import User,Room
from flask_wtf.file import FileField,FileAllowed
from flask_login import current_user


class RegisterForm(FlaskForm):
    username=StringField('username',validators=[DataRequired(),Length(min=2,max=60)])
    email=StringField('email',validators=[DataRequired(),Email()])
    password=PasswordField('password',validators=[DataRequired()])
    confirm_password=PasswordField('confirm.txt password',validators=[DataRequired(),equal_to('password')])
    submit=SubmitField('Register')


    def validate_username(self,username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError("Username is already taken")


    def validate_email(self,email):
        user = User.query.filter_by(username=email.data).first()
        if user:
            raise ValidationError("Email is already taken")


class LoginForm(FlaskForm):
    email=StringField('email',validators=[DataRequired()])
    password = PasswordField('password', validators=[DataRequired()])
    submit = SubmitField('Log in')


class CreateRoom(FlaskForm):
    title=StringField("Chat's name",validators=[DataRequired()])
    submit = SubmitField('Create chat')


    def validate_title(self,title):
        user=Room.query.filter_by(title=title.data).first()
        if user:
            raise ValidationError("This room is already exist")

class PickRoom(FlaskForm):
    room=SelectField('Pick room', choices=[], coerce=str)
    submit = SubmitField('Pick')

    def validate_room(self, field):
        if field.data == "Pick room":
            raise ValidationError("Please pick room that exist")

class UpdateAccount(FlaskForm):
    username = StringField('username', validators=[DataRequired(), Length(min=2, max=60)])
    email = StringField('email', validators=[DataRequired(), Email()])
    picture = FileField('Update account image', validators=[FileAllowed(['jpg', 'png', 'jpeg'])])
    submit = SubmitField('Update')


    def validate_username(self,username):
        if username.data!=current_user.username:
            user=User.query.filter_by(username=username.data).first()
            if user:
                raise ValidationError("That username is already taken")

    def validate_email(self,email):
        if email.data!=current_user.email:
            email=User.query.filter_by(email=email.data)
            if email:
                raise ValidationError("That email is already used")


class CreatePost(FlaskForm):
    title=StringField('Title',validators=[DataRequired()])
    content=TextAreaField('Content',validators=[DataRequired()])
    submit=SubmitField('Post')


class UpdPost(FlaskForm):
    title=StringField('Title',validators=[DataRequired()])
    content=TextAreaField('Content',validators=[DataRequired()])
    submit=SubmitField('Update')


class SearchForm(FlaskForm):
    username=StringField('Search someone',validators=[DataRequired()])
    submit=SubmitField('Search')