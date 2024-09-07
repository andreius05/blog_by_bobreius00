from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from flask_socketio import SocketIO
from flask_socketio import SocketIO
from flask_migrate import Migrate
from flask_mail import Mail,Message
from flask_redis import FlaskRedis
from flask_caching import Cache

app = Flask(__name__)
app.config['SECRET_KEY'] = '5791628bb0b13ce0c676dfde280ba245'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
migrate = Migrate(app, db)
socketio=SocketIO(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'
socketio=SocketIO(app)
mail=Mail(app)
redis=FlaskRedis(app)
app.config['CACHE_TYPE'] = 'redis'
app.config['CACHE_REDIS_URL'] = "redis://localhost:6379/0"
cache = Cache(app)








from flaskblog import routes
