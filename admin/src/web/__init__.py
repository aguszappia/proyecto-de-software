from flask import Flask
from flask import render_template

def create_app(env="development", static_folder="../../static"):
    app = Flask(__name__, static_folder=static_folder)

    @app.route('/')
    def home():
        return render_template("home.html")
    
    @app.route('/about')
    def about():
        return render_template("about.html")
    
    return app