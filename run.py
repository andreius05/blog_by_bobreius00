from flaskblog import app,db,socketio
from flaskblog.models import Message



if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    socketio.run(app,debug=True)