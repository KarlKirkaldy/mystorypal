from flask_session import Session
from flask import *
from flask_login import UserMixin, login_user, LoginManager, login_required, logout_user, current_user
#from flask_cors import CORS
import sqlite3
from datetime import datetime
import pandas as pd
from flask_sqlalchemy import SQLAlchemy
from json import dumps
import io
import json
import os
import pytz
from dateutil import parser
from langchain import OpenAI, ConversationChain, LLMChain, PromptTemplate
from langchain.memory import ConversationBufferWindowMemory
from bson import ObjectId
from werkzeug.security import generate_password_hash, check_password_hash
from flask import Flask, render_template, redirect, url_for, request
from flask_sqlalchemy import SQLAlchemy
from flask_security import UserMixin, RoleMixin, roles_accepted, Security, SQLAlchemySessionUserDatastore, auth_required
import string
import random
from flask_login import LoginManager, login_manager, login_user
from flask_pymongo import PyMongo
from flask_bcrypt import Bcrypt

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///database.sqlite3"
app.config['SECRET_KEY'] = 'MY_SECRET'
app.config['SECURITY_PASSWORD_SALT'] = "MY_SECRET"
app.config['SECURITY_REGISTERABLE'] = True
app.config['SECURITY_SEND_REGISTER_EMAIL'] = False

app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

#CORS(app, resources={r'/*': {'origins': '*'}})


db = SQLAlchemy()
db.init_app(app)
app.app_context().push()

bcrypt = Bcrypt(app)

app.config['MONGO_URI'] = "mongodb+srv://kbkirkaldy35:zonolite35@cluster0.fsnfxtf.mongodb.net/kbkirkaldydb?retryWrites=true&w=majority"
app.config['CORS_Headers'] = 'Content-Type'

mongo = PyMongo(app)
mongodb = mongo.db
#CORS(app, resources={r'/*': {'origins': '*'}})

roles_users = db.Table('roles_users',
        db.Column('user_id', db.Integer(), db.ForeignKey('user.id')),
        db.Column('role_id', db.Integer(), db.ForeignKey('role.id')))

class User(db.Model, UserMixin):
    __tablename__ = 'user'
    id = db.Column(db.Integer, autoincrement=True, primary_key=True)
    email = db.Column(db.String, unique=True)
    password = db.Column(db.String(255), nullable=False, server_default='')
    active = db.Column(db.Boolean())
    # backreferences the user_id from roles_users table
    #roles = db.relationship('Role', secondary=roles_users, backref='roled')
    fs_uniquifier = db.Column(db.String(255), unique=True, nullable=False)

class Role(db.Model, RoleMixin):
    __tablename__ = 'role'
    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String(80), unique=True)

# creates all database tables
#@app.before_first_request
if False:#def create_tables():
    db.create_all()

user_datastore = SQLAlchemySessionUserDatastore(db.session, User, Role)
security = Security(app, user_datastore)

@app.route('/')
# defining function index which returns the rendered html code
# for our home page
def home():
    return render_template("home.html")



@app.route('/signup', methods=['GET', 'POST'])
def signup():
    msg=""
    logout_user()
    if request.method == 'POST':
        user = User.query.filter_by(email=request.form['email']).first()
        msg=""
        if user:
            msg="User already exists"
            return render_template('signup.html', msg=msg)

        random_string = ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(16))
        user = User(name=request.form['name'], email=request.form['email'], interest=request.form['interest'], language=request.form['language'], fs_uniquifier=random_string, active=1, password=bcrypt.generate_password_hash(request.form['password']))

        # store the role
        #role = Role.query.filter_by(id=request.form['options']).first()
        #user.roles.append(role)

        # commit the changes to database
        db.session.add(user)
        db.session.commit()


        session['username'] = user.email

        login_user(user)
        return redirect(url_for('kanbanhome'))

    else:
        return render_template("signup.html", msg=msg)


@app.route('/signin', methods=['GET', 'POST'])
def signin():
    msg=""
    logout_user()
    if request.method == 'POST':
        user = User.query.filter_by(email=request.form['email']).first()
        if user:
            if bcrypt.check_password_hash(user.password, request.form['password']):#user.password == request.form['password']:
                session['username'] = user.email
                login_user(user)
                return redirect(url_for('kanbanhome'))
            else:
                msg="Wrong password"

        else:
            msg="User doesn't exist"
        return render_template('signin.html', msg=msg)

    else:
        return render_template("signin.html", msg=msg)


@app.route('/logout', methods=['GET', 'POST'])
@auth_required()
def logout():
    logout_user()
    return redirect(url_for('signin'))


def generate_image(prompt):
    openai.api_key = os.environ['OPENAI_KEY']
    preprompt = "A children's storybook illustration for the following: "

    try:
        response = openai.Image.create(
            prompt=preprompt+prompt,
            model="image-alpha-001",
            size="256x256",
            response_format="url"
        )["data"][0]["url"]
    except:
        response = "https://images.app.goo.gl/9Dxu5L5LHm9k5ajf7"
    return response



def GPT3call(prompt):
    try:
        api_key = os.environ['OPENAI_KEY']
        openai.api_key = api_key

        if api_key:
            a = openai.ChatCompletion.create(
              model="gpt-3.5-turbo",
              messages=[{"role": "user", "content": prompt}],
              #temperature=0.5,
              max_tokens=1048,
              #top_p=1.0,
              #frequency_penalty=0.0,
              #presence_penalty=0.0
            )
            response = a['choices'][0]['message']['content']
        else:
            response = "API key missing"
        return response
    except Exception as e:
        return "Page A: " + str(e) + "There was a problem connecting to OpenAI. Check your key."



@app.route('/kanban')
@auth_required()
def kanbanhome():
    return render_template("index.html")#, status='success', tasksjin=taskslist, listsjin=listslist)


@app.route('/write_intro_email', methods=['POST'])
@auth_required()
def write_intro_email():
    if request.method == 'POST':
        post_data = request.get_json(silent=True)
        book_title = post_data.get('book_title')
        characters = post_data.get('characters')
        storyline = post_data.get('storyline')
        ages = post_data.get('ages')

        prompt = f"Write a story book, titled '{book_title}' about characters {characters}. The book will be for children aged {ages}. The book's storyline will be as follows: {storyline}. The pages of the book should be separated by Page A:, Page B:, and so on. There should be exactly 12 pages. Each page should contain around 36 words. Start the story at Page A:. Story book:"
        print("WRITING", prompt)
        result = GPT3call(prompt)
        print('result fetched:', result)

        pages = result.split("Page ")[1:]  # Split the string by "Page" and ignore the first element

        pages_dict = {}  # Create an empty dictionary

        for page in pages:
            print("PAGE", page)
            page_num, content = page.split(":", 1)  # Split each page into the page number and content
            text = content.strip()
            try:
                image = generate_image(text)
            except:
                image = "https://discussions.apple.com/content/attachment/660042040"
            pages_dict[page_num] = {"image" : image,
                                    "text" : text}  # Add the page number and content to the dictionary, removing leading/trailing whitespace from the content

        print(result)  # Print the resulting dictionary
        print('PAGE_DICT', pages_dict)

        return jsonify({
            'status': 'success',
            'result': result,
            'pages': pages_dict
        })


@app.route('/save', methods=['GET', 'POST'])
@auth_required()
def save():
    response_object = {'status': 'success'}
    if request.method == 'POST':
        post_data = request.get_json(silent=True)
        book_title = post_data.get('book_title')
        pages = post_data.get('pages')


        result = mongodb.storybooks_collection.insert_one({'username' : session['username'],
                                                           'book_title' : book_title,
                                                           'pages' : pages})


        print('saved successfully')
        response_object['message'] = "Successfully Added"
    return jsonify(response_object)


@app.route('/history', methods=['GET', 'POST'])
@auth_required()
def history():
    return render_template("history.html")




@app.route('/fetch_stories', methods=['GET'])
@auth_required()
def fetchdiscussion():
    try:
        print("FETCHING MONGODB DATA")
        storybooks = []
        storybooks1 = mongodb.storybooks_collection.find({"username" : session['username']})
        for storybook in storybooks1:
            storybook['_id'] = str(storybook['_id'])
            storybooks.append(storybook)
    except:
        storybooks = [{'_id' : '',
                       'username' : '',
                       'pages' : {'A': ' ', 'B': ' ', 'C': ' ', 'D': ' ', 'E': ' ', 'F': ' ', 'G': ' ', 'H': ' ', 'I': ' ', 'J': ' ', 'K': ' ', 'L': ' ', 'M': ' ', 'N': ' ', 'O': ' ', 'P': ' ', 'Q': ' ', 'R': ' '},
                       'book_title' : ''}]

    result = jsonify({
        'status': 'success',
        'storybooks': storybooks
    })
    print("FETCHED DISC DATA", storybooks)
    return result


@app.route('/fetch', methods=['GET'])
@auth_required()
def fetchkanban():
    with sqlite3.connect(dbfilename) as conn:
        cur = conn.cursor()
        cur.execute(f"select * from {RESULTS_TABLE} where username='{session['username']}';")
        resultslist = cur.fetchall()
        resultslist.reverse()
    result = jsonify({
        'status': 'success',
        'results': resultslist
    })
    print(result)
    return result


@app.route('/privacypolicypage', methods=['GET', 'POST'])
def privacypolicypage():
    return render_template('privacy-policy.html')

@app.route('/tospage', methods=['GET', 'POST'])
def tospage():
    return render_template('terms-of-service.html')

if __name__ == '__main__':
    app.run()
