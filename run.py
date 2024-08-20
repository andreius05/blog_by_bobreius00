from flaskblog import app,db
from flaskblog.models import Room


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)