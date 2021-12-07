import os
import time
from flask import Flask, flash, redirect, url_for, render_template, session
from config import Config
from app.forms import LoginForm, RegistrationForm, PictureForm
from werkzeug.utils import secure_filename
from app.aws import AwsSession 

app = Flask(__name__)  # create app of instance Flask
app.config['SECRET_KEY'] = 'c7e22c3ba14bd20390e19e9954796d8b'
app.config.from_object(Config)
aws = AwsSession()
bucket = aws.bucket 
bucket_url_base = aws.bucket_url_base
s3_client = aws.s3
# login = LoginManager(app)
# login.login_view = 'login'

@app.route('/', methods=['GET', 'POST'])
@app.route('/index', methods=['GET', 'POST'])
def index():
    try:
        if session['logged_in'] == True:
            flash("Currently logged in")
        else:
            session['logged_in'] = False
            return redirect(url_for('login'))
    except:
        session['logged_in'] = False
        return redirect(url_for('login'))
    return render_template('index.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    try:
        if session['logged_in'] == True:
            flash('Already logged in. Please logout first!')
            return redirect(url_for('index'))
    except:
        pass
    session["logged_in"] = False
    form = LoginForm()
    if form.validate_on_submit():
        username = form.username.data
        print(username)

        user = aws.DDB_get_user(username)
        if user == -1:
            flash('Invalid username or password')  # user doesn't exist
            return redirect(url_for('login'))
        if user is None or not user.check_password(form.password.data):  # check password
            flash('Invalid username or password')
            return redirect(url_for('login'))
        # Username and password are valid
        session['current_user'] = username  # should be from user class, fix later
        session['logged_in'] = True
        print('loggin in:')
        print(session['current_user'])
        print(session['logged_in'])
        return redirect(url_for('index'))
    return render_template('login.html', form=form)


# Method to logout authenticated user
@app.route('/logout')
def logout():
    try:
        session.pop('current_user', None)
        session['logged_in'] = False
        flash("You are logged out")
    except:
        pass
    return redirect(url_for('index'))


# method to register user who has administrator priveleges
@app.route('/register', methods=['GET', 'POST'])
def register():
    try:
        if session['logged_in'] == True:
            if str(session['current_user']) == 'root':  # first account or root name
                flash("You have admin permissions")
            else:
                flash("Sorry, only administrators can register accounts")
                return redirect(url_for('index'))
        else:
            flash("Please login, only administrators can register accounts")
            return redirect(url_for('index'))
        # if here, user is logged in and also admin
        form = RegistrationForm()
        if form.validate_on_submit():
            response = aws.DDB_add_user(username=form.username.data, email=form.email.data, password=form.password.data)
            flash('Congratulations, you are now a registered user!')
    except:
        return redirect(url_for('index'))
    return render_template('register.html', title='Register', form=form)

# Upload method for users 
@app.route('/upload', methods=['GET', 'POST'])
def upload():
    
    if session['logged_in'] == False:  # cant upload if not logged in
        flash('Please login to upload images', category='danger')
        return redirect(url_for('index'))
    
    form = PictureForm()
    """ TODO: LEFT HERE, MAKE THIS PATHING FOR S3 SAVE PROPERLY
    if form.validate_on_submit():
        if form.picture.data:
            filename = secure_filename(form.picture.data.filename)
            filename_without_extension = (filename.split('.'))[0]
            img_folder_name = str(filename_without_extension+str(int(time.time())))
            username = str(session['current_user'])
            s3_path = "/".join(['static','images', username, img_folder_name])
            
            s3_dict = {
            'rootdir': s3_path,
            'normal': "/".join([s3_path, 'normal']),
            'thumbnail': "/".join([s3_path, 'thumbnail']),
            'blur': "/".join([s3_path, 'blur']),
            'shade': "/".join([s3_path, 'shade']),
            'spread': "/".join([s3_path, 'spread'])
            }

            main_path = os.path.join(path_dict['normal'], filename)
            main_path_s3 = "/".join([s3_dict['normal'], filename])

            s3_client.upload_file(main_path, bucket, main_path_s3)

            aws.DDB_upload_image(pic_path)
    """
    return render_template('upload.html', title='Upload Image', form=form)

@app.route('/api')
def api():
    return {'hello' : 'world'}