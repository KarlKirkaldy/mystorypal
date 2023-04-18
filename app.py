from flask import *
from flask_login import UserMixin, login_user, LoginManager, login_required, logout_user, current_user
from flask_cors import CORS
import sqlite3
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import InputRequired, Length, ValidationError
from datetime import datetime
import pandas as pd
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from json import dumps
import io
import json
import os
import openai
from flask_pymongo import PyMongo
from bson import ObjectId



DEBUG = True
global dbfilename
dbfilename = 'instance/database.db'
global RESULTS_TABLE
RESULTS_TABLE = "results_table"
global JOBDESCS_TABLE
JOBDESCS_TABLE = "jobdescs_table"
global TEMPLATES_TABLE
TEMPLATES_TABLE = "templates_table"
global PROMPTS

app = Flask(__name__)
CORS(app, resources={r'/*': {'origins': '*'}})


app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SECRET_KEY'] = 'thisisasecretkey'

app.config['MONGO_URI'] = 'mongodb+srv://kbkirkaldy:<Fy8CdQjZ9DKve4TV>@cluster0.fsnfxtf.mongodb.net/?retryWrites=true&w=majority'
app.config['CORS_Headers'] = 'Content-Type'

mongo = PyMongo(app)
mongodb = mongo.db

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)




login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'signin'


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


#source: official flask_login documentation

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(36), nullable=False, unique=True)
    password = db.Column(db.String(14), nullable=False)
    first_name = db.Column(db.String(20), nullable=False)
    last_name = db.Column(db.String(20), nullable=False)


class RegisterForm(FlaskForm):
    username = StringField(validators=[InputRequired(), Length(min=8, max=36)], render_kw={"placeholder": "Email"})
    first_name = StringField(validators=[InputRequired(), Length(min=1, max=20)], render_kw={"placeholder": "First Name"})
    last_name = StringField(validators=[InputRequired(), Length(min=1, max=20)], render_kw={"placeholder": "Last Name"})
    password = PasswordField(validators=[InputRequired(), Length(min=8, max=14)], render_kw={"placeholder": "Password"})
    submit = SubmitField('Sign up')
    def validate_username(self, username):
        if User.query.filter_by(username=username.data).first():
            raise ValidationError(
                'Username already exists!')


class LoginForm(FlaskForm):
    username = StringField(validators=[InputRequired(), Length(min=8, max=36)], render_kw={"placeholder": "Email"})
    password = PasswordField(validators=[InputRequired(), Length(min=8, max=14)], render_kw={"placeholder": "Password"})
    submit = SubmitField('Sign in')


@app.route('/')
def home():
    return render_template('home.html')


@app.route('/signin', methods=['GET', 'POST'])
def signin():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user:
            if bcrypt.check_password_hash(user.password, form.password.data):
                login_user(user)
                print("logged in as", user.username)
                global username
                username = user.username
                return redirect(url_for('kanbanhome', username=user.username))
    return render_template('signin.html', form=form)


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    form = RegisterForm()
    if form.validate_on_submit():
        db.session.add(User(username=form.username.data, first_name=form.first_name.data, last_name=form.last_name.data, password=bcrypt.generate_password_hash(form.password.data)))
        db.session.commit()
        return redirect(url_for('signin'))
    return render_template('signup.html', form=form)


@app.route('/logout', methods=['GET', 'POST'])
@login_required
def logout():
    logout_user()
    return redirect(url_for('signin'))



def generate_image(prompt):
    openai.api_key = os.environ['OPENAI_KEY']
    preprompt = "A children's storybook illustration for the following: "

    response = openai.Image.create(
        prompt=preprompt+prompt,
        model="image-alpha-001",
        size="256x256",
        response_format="url"
    )

    return response["data"][0]["url"]



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
    except:
        return "There was a problem connecting to OpenAI. Check your key."



@app.route('/kanban/<username>')
@login_required
def kanbanhome(username):
    with sqlite3.connect(dbfilename) as conn:
        cur = conn.cursor()
        cur.execute(f"select * from {RESULTS_TABLE} where username='{username}';")
        taskslist = cur.fetchall()
        templateslist = cur.fetchall()
        return render_template("index.html")#, status='success', tasksjin=taskslist, listsjin=listslist)

def get_name(username):
    with sqlite3.connect(dbfilename) as conn:
        cur = conn.cursor()
        cur.execute(f"select first_name, last_name from user where username='{username}'")
        row = cur.fetchall()
        first_name, last_name = row[0][0], row[0][1]
        return first_name, last_name

@app.route('/write_intro_email/<username>', methods=['POST'])
@login_required
def write_intro_email(username):
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


@app.route('/save/<username>', methods=['GET', 'POST'])
@login_required
def save(username):
    response_object = {'status': 'success'}
    if request.method == 'POST':
        post_data = request.get_json(silent=True)
        book_title = post_data.get('book_title')
        pages = post_data.get('pages')


        result = mongodb.storybooks_collection.insert_one({'username' : username,
                                                           'book_title' : book_title,
                                                           'pages' : pages})

        '''with sqlite3.connect(dbfilename) as conn:
            cur = conn.cursor()
            print("TYPE", type(result))
            print("RESULT", result)
            cur.execute(f'insert into {RESULTS_TABLE} (type, result, created_at, username) values ("{stype}", "{result}", CURRENT_TIMESTAMP, "{username}")')
            conn.commit()'''
        print('saved successfully')
        response_object['message'] = "Successfully Added"
    return jsonify(response_object)


@app.route('/history/<username>', methods=['GET', 'POST'])
@login_required
def history(username):
    return render_template("history.html")




@app.route('/fetch_stories/<username>', methods=['GET'])
@login_required
def fetchdiscussion(username):
    print("FETCHING SQL DATA")
    '''with sqlite3.connect(dbfilename) as conn:
        cur = conn.cursor()
        cur.execute(f"select * from {APPLICATIONS_TABLE} where username='{username}';")
        taskslist = cur.fetchall()
        cur.execute(f"select * from {MISSIONS_TABLE} where username='{username}';")
        listslist = cur.fetchall()
        '''

    try:
        print("FETCHING MONGODB DATA")
        storybooks = []
        storybooks1 = mongodb.storybooks_collection.find({"username" : username})
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



@app.route('/edit_task/<string:type>/<string:id>/<username>', methods=['GET', 'POST'])
@login_required
def edit(id, type, username):
    with sqlite3.connect(dbfilename) as conn:
        print("editing task with id: ", id)
        cur = conn.cursor()
        if type == "email": cur.execute(f"select * from {EMAILS_TABLE} WHERE id = '{id}' and username = '{username}'")
        elif type == "jobdesc": cur.execute(f"select * from {JOBDESCS_TABLE} WHERE id = '{id}' and username = '{username}'")
        elif type == "template": cur.execute(f"select * from {TEMPLATES_TABLE} WHERE id = '{id}' and username = '{username}'")
        row = cur.fetchone()
        print('fetching task complete')
    return jsonify({
        'status': 'success',
        'editmember': row
    })


@app.route('/update_task/<string:type>/<username>', methods=['GET', 'POST'])
@login_required
def update(username, type):
    response_object = {'status': 'success'}
    if request.method == 'POST':
        with sqlite3.connect(dbfilename) as conn:
            cur = conn.cursor()
            post_data = request.get_json(silent=True)

            if type == "email":
                new_id = post_data.get('new_id')
                new_name = post_data.get('new_name')
                new_subject = post_data.get('new_subject')
                new_email_prompt = post_data.get('new_email_prompt')
                new_result = post_data.get('new_result')
                print(new_id, new_name, new_subject, new_email_prompt, new_result)
                cur.execute(f"update {EMAILS_TABLE} set name='{new_name}', subject='{new_subject}', email_prompt='{new_email_prompt}', result='{new_result}' where id='{new_id}'")

            elif type == "jobdesc":
                new_id = post_data.get('new_id')
                new_job_title = post_data.get('new_job_title')
                new_job_responsibilities = post_data.get('new_job_responsibilities')
                new_job_requirements = post_data.get('new_job_requirements')
                new_result = post_data.get('new_result')
                print(new_id, new_job_title, new_job_responsibilities, new_job_requirements, new_result)
                cur.execute(f"update {JOBDESCS_TABLE} set job_title='{new_job_title}', job_responsibilities='{new_job_responsibilities}', job_requirements='{new_job_requirements}', result='{new_result}' where id='{new_id}'")

            elif type == "template":
                new_id = post_data.get('new_id')
                new_template_content = post_data.get('new_template_content')
                print(new_id, new_template_content)
                cur.execute(f"update {TEMPLATES_TABLE} set template_content='{new_template_content}' where id='{new_id}'")

            conn.commit()
            cur.close()
            print("updated task")

        response_object['message'] = "Successfully Updated"
    return jsonify(response_object)


@app.route('/delete_task/<string:id>/<username>', methods=['GET', 'POST'])
@login_required
def delete(id, username):
    with sqlite3.connect(dbfilename) as conn:
        print("deleting task with id", id)
        cur = conn.cursor()
        response_object = {'status': 'success'}
        cur.execute(f"delete from {RESULTS_TABLE} where id='{id}'")
        conn.commit()
        cur.close()
        print("deleted task", id)

    response_object['message'] = "Successfully Deleted"
    return jsonify(response_object)

'''
def export_a_task(type, id):
    with sqlite3.connect(dbfilename) as conn:
        print("exporting task with id", id)
        cur = conn.cursor()
        if type == "email":
            cur.execute(f"select *  from {EMAILS_TABLE} where id='{id}'")
            columns = ['id', 'name', 'subject', 'email_prompt', 'task_type', 'result', 'created_at', 'username']
        row = cur.fetchall()
        print("exported row is ", row)
        df = pd.DataFrame(row, columns=columns)
        taskexportfilename = str(row[0][1])+'.csv'
        df.to_csv(taskexportfilename, index=False)
        conn.commit()
        cur.close()
        print("exported task")

        send_file("/"+taskexportfilename, as_attachment=True)
'''


@app.route('/export_task/<string:type>/<string:id>', methods=['GET', 'POST'])
@login_required
def export(type, id):
    export_a_task(type, id)
    response_object = {'status': 'success'}
    response_object['message'] = "Successfully Exported"
    return jsonify(response_object)


@app.route('/fetch/<username>', methods=['GET'])
def fetchkanban(username):
    with sqlite3.connect(dbfilename) as conn:
        cur = conn.cursor()
        cur.execute(f"select * from {RESULTS_TABLE} where username='{username}';")
        resultslist = cur.fetchall()
        resultslist.reverse()
    result = jsonify({
        'status': 'success',
        'results': resultslist,
        'username': username
    })
    print(result)
    return result


@app.route('/user', methods=['GET'])
def usern():
    result = jsonify({
        'status': 'success',
        'username': username
    })
    return result


@app.route('/privacypolicypage', methods=['GET', 'POST'])
def privacypolicypage():
    return render_template('privacy-policy.html')

@app.route('/tospage', methods=['GET', 'POST'])
def tospage():
    return render_template('terms-of-service.html')

if __name__ == '__main__':
    app.run(debug=True)
