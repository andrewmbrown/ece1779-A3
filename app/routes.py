import os
import time
import shutil
import requests
import ast 
import json 
import base64
from flask import Flask, flash, redirect, url_for, render_template, session
from config import Config
from app.forms import LoginForm, RegistrationForm, PictureForm, URLPictureForm
from app.imagetransform import image_transform
from app.apputilities import extension_dict, check_img_url
from werkzeug.utils import secure_filename
from app.aws import AwsSession 
from PIL import Image 

app = Flask(__name__)  # create app of instance Flask
app.config['SECRET_KEY'] = 'c7e22c3ba14bd20390e19e9954796d8b'
app.config.from_object(Config)
aws = AwsSession()
bucket = aws.bucket 
bucket_url_base = aws.bucket_url_base
s3_client = aws.s3
# login = LoginManager(app)
# login.login_view = 'login'
# Zappa build

MAX_HEIGHT = 800
MAX_WIDTH = 800

# comment test for merge of branch

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
    if form.validate_on_submit():
        if form.picture.data:
            filename = secure_filename(form.picture.data.filename)
            filename_without_extension = (filename.split('.'))[0]
            img_folder_name = str(filename_without_extension+str(int(time.time())))
            username = str(session['current_user'])
            root_dir = str(os.path.abspath(os.sep))
            user_image_path = os.path.join(root_dir, 'tmp') # Zappa/Lambda only has write permissions to this dir
            # if not os.path.exists(user_image_path):
            #     os.makedirs(user_image_path)

            picture_path = user_image_path # FOLDER for ALL IMAGES
            http_path = bucket_url_base + "static/images/" + username + "/" + img_folder_name + "/"
            s3_path = "/".join(['static','images', username, img_folder_name])

            path_dict = {
                'rootdir': picture_path,
                'normal': os.path.join(picture_path, 'normal'),
                'thumbnail': os.path.join(picture_path, 'thumbnail')
            }

            s3_dict = {
            'rootdir': s3_path,
            'normal': "/".join([s3_path, 'normal']),
            'thumbnail': "/".join([s3_path, 'thumbnail'])
            }

            pic_path = {
                "username": username,
                "filename_currtime": img_folder_name, #img_folder_name 
                "filename": filename,
                "location": picture_path,
                "httppath": http_path,
                "s3path": s3_path,
                "text_english": "none",
                "text_french": "none",
                "text_spanish": "none"
            }

            # save the image file itself on the local machine
            # os.mkdir(picture_path) # already exists
            os.mkdir(path_dict['normal'])
            os.mkdir(path_dict['thumbnail'])

            main_path = os.path.join(path_dict['normal'], filename)
            thumbnail_path = os.path.join(path_dict['thumbnail'], filename)

            main_path_s3 = "/".join([s3_dict['normal'], filename])
            thumbnail_path_s3 = "/".join([s3_dict['thumbnail'], filename])

            form.picture.data.save(main_path)
            im = Image.open(main_path)
            width, height = im.size
            ratio = min(MAX_WIDTH/width, MAX_HEIGHT/height)
            if (ratio < 1):
                new_width = int(width*ratio)
                new_height = int(height*ratio)
                im = im.resize((new_width, new_height), Image.ANTIALIAS)
                im.save(main_path)
            thumbnail_test = image_transform(main_path, thumbnail_path, 3)

            s3_client.upload_file(thumbnail_path, bucket, thumbnail_path_s3)
            s3_client.upload_file(main_path, bucket, main_path_s3)

            path_file, filename_ext = os.path.splitext(main_path)
            filext = (filename_ext.replace('.', '').upper())

            b64string = ""

            with open(main_path, "rb") as image:
                b64string = base64.b64encode(image.read())

            test_payload = {
                "image_b64": b64string.decode('utf-8'),
                "AWS_ACC_KEY": aws.AWS_ACC_KEY,
                "AWS_SEC_KEY": aws.AWS_SEC_KEY,
                "true_extension": filename_ext,
                "type_extension": filext
            }

            json_payload = json.dumps(test_payload)

            resp = aws.lamb.invoke(
                FunctionName="extract-and-translate",
                InvocationType="RequestResponse",
                Payload=json_payload
            )

            trans = resp["Payload"].read().decode('utf-8')
            str_trans = json.loads(trans)
            trans_list = ast.literal_eval(str_trans['body'])

            en_trans = trans_list['english']
            fr_trans = trans_list['french']
            es_trans = trans_list['spanish']

            if len(en_trans) > 0:
                en_trans = list(dict.fromkeys(en_trans))
                pic_path['text_english'] = "|".join(en_trans)
            if len(fr_trans) > 0:
                fr_trans = list(dict.fromkeys(fr_trans))
                pic_path['text_french'] = "|".join(fr_trans)
            if len(es_trans) > 0:
                es_trans = list(dict.fromkeys(es_trans))
                pic_path['text_spanish'] = "|".join(es_trans)      

            # remove files in lambda function tmp folder
            for file_object in os.listdir(picture_path):
                file_object_path = os.path.join(picture_path, file_object)
                if os.path.isfile(file_object_path) or os.path.islink(file_object_path):
                    os.unlink(file_object_path)
                else:
                    shutil.rmtree(file_object_path)

            aws.DDB_upload_image(pic_path)

    return render_template('upload.html', title='Upload Image', form=form)


@app.route('/uploadurl', methods=['GET', 'POST'])
def uploadurl():
    if session['logged_in'] == False:  # cant upload if not logged in
        flash('Please login to upload images', category='danger')
        return redirect(url_for('index'))

    form = URLPictureForm()
    if form.validate_on_submit():
        if form.urlpicture.data:
            # Uploading images depends on the machine

            # check file size from URL by checking the header using request library
            # header settings give full uncompressed fizesize
            try:
                r = requests.head(str(form.urlpicture.data),headers={'Accept-Encoding': 'identity'})
                size = int(r.headers['content-length'])
            except:
                flash('Image URL was improperly entered or not a viable image URL, please try another upload', category='danger')
                return redirect(url_for('uploadurl'))
            if size > 10000000:  # larger than 10MB, server side check
                flash("File is too large! Please only upload images below 10MB in filesize")
                return redirect(url_for('uploadurl'))

            viable_img = check_img_url(str(form.urlpicture.data))
            viable_img_truth = viable_img[0]
            if not viable_img_truth:
                flash('Image URL was improperly entered or not a viable image URL, please try another upload', category='danger')
                return redirect(url_for('uploadurl'))

            processed_filename = secure_filename(str(form.urlpicture.data)).replace(".", "_").lower()
            filename_ext = extension_dict[viable_img[1]] # png, jpg, or jpeg 
            filename_without_extension = str(processed_filename[-32:]) # just use the last 256 chars of it 
            filename = filename_without_extension + str(filename_ext)

            try: 
                img_data = requests.get(str(form.urlpicture.data)).content
                with open(filename, 'wb') as handler:
                    handler.write(img_data)
            except:
                flash("Error in downloading image from URL. Please try another.", category='danger')
                return redirect(url_for('uploadurl'))
            

            img_folder_name = str(filename_without_extension+str(int(time.time())))
            username = str(session['current_user'])
            root_dir = str(os.path.abspath(os.sep))
            user_image_path = os.path.join(root_dir, 'tmp') # Zappa/Lambda only has write permissions to this dir
            picture_path = user_image_path
            html_path = os.path.join('static', 'images', username, img_folder_name)
            html_path_old = os.path.join('static', 'images', username, img_folder_name)
            http_path = bucket_url_base + "static/images/" + username + "/" + img_folder_name + "/"
            s3_path = "/".join(['static','images', username, img_folder_name])

            path_dict = {
                'rootdir': picture_path,
                'normal': os.path.join(picture_path, 'normal'),
                'thumbnail': os.path.join(picture_path, 'thumbnail'),
                'blur': os.path.join(picture_path, 'blur'),
                'shade': os.path.join(picture_path, 'shade'),
                'spread': os.path.join(picture_path, 'spread')
            }

            s3_dict = {
                'rootdir': s3_path,
                'normal': "/".join([s3_path, 'normal']),
                'thumbnail': "/".join([s3_path, 'thumbnail']),
                'blur': "/".join([s3_path, 'blur']),
                'shade': "/".join([s3_path, 'shade']),
                'spread': "/".join([s3_path, 'spread'])
            }
        
            # pic_path = ImageLocation(location=picture_path, httppath=html_path, s3path=s3_path, filename=filename, user_id=current_user.id)
            # pic_path = ImageLocation(location=picture_path, httppath=http_path, s3path=s3_path, filename=filename, user_id=current_user.id)

            pic_path = {
                "username": username,
                "filename_currtime": img_folder_name, #img_folder_name 
                "filename": filename,
                "location": picture_path,
                "httppath": http_path,
                "s3path": s3_path
            }

            # save the image file itself on the local machine
            # os.mkdir(picture_path)
            os.mkdir(path_dict['normal'])
            os.mkdir(path_dict['thumbnail'])
            os.mkdir(path_dict['blur'])
            os.mkdir(path_dict['shade'])
            os.mkdir(path_dict['spread'])

            # form.picture.data.save(main_path)
            shutil.copy(filename, path_dict['normal'])

            main_path = os.path.join(path_dict['normal'], filename)
            thumbnail_path = os.path.join(path_dict['thumbnail'], filename)
            blur_path = os.path.join(path_dict['blur'], filename)
            shade_path = os.path.join(path_dict['shade'], filename)
            spread_path = os.path.join(path_dict['spread'], filename)

            main_path_s3 = "/".join([s3_dict['normal'], filename])
            thumbnail_path_s3 = "/".join([s3_dict['thumbnail'], filename])
            blur_path_s3 = "/".join([s3_dict['blur'], filename])
            shade_path_s3 = "/".join([s3_dict['shade'], filename])
            spread_path_s3 = "/".join([s3_dict['spread'], filename])

            blur_test = image_transform(main_path, blur_path, 0) # add errors if didn't work
            shade_test = image_transform(main_path, shade_path, 1)
            spread_test = image_transform(main_path, spread_path, 2)
            thumbnail_test = image_transform(main_path, thumbnail_path, 3)

            if blur_test == -1 or shade_test == -1 or spread_test == -1 or thumbnail_test == -1:
                flash('Image could not be transformed! Please try again or another', category='danger')
                return redirect(url_for('uploadurl'))

            s3_client.upload_file(main_path, bucket, main_path_s3)
            s3_client.upload_file(blur_path, bucket, blur_path_s3)
            s3_client.upload_file(shade_path, bucket, shade_path_s3)
            s3_client.upload_file(spread_path, bucket, spread_path_s3)
            s3_client.upload_file(thumbnail_path, bucket, thumbnail_path_s3)

            # add picture path to the database
            '''
            db.session.add(pic_path)
            db.session.commit()
            '''
            aws.DDB_upload_image(pic_path)

            # remove the temp file
            os.remove(filename)
            # remove files in lambda function tmp folder
            for file_object in os.listdir(picture_path):
                file_object_path = os.path.join(picture_path, file_object)
                if os.path.isfile(file_object_path) or os.path.islink(file_object_path):
                    os.unlink(file_object_path)
                else:
                    shutil.rmtree(file_object_path)

            flash('Upload successful.')
    return render_template('uploadurl.html', title='Upload Image via URL', form=form)


# gallery will go here 
@app.route('/gallery', methods=['GET'])
def gallery():
    if session['logged_in'] == False:  # cant upload if not logged in
        flash('Please login to upload images', category='danger')
        return redirect(url_for('index'))
    title = "{}'s Image Gallery".format(str(session['current_user']))
    # image_path_rows = ImageLocation.query.filter_by(user_id=current_user.id).all()
    image_path_rows = aws.DDB_get_images_by_user(str(session['current_user']))

    image_paths = [{
        'filename': str(img['filename']),
        'filename_url': str(str(img['filename']).replace(".", "$")),
        'dirname': str(os.path.basename(os.path.normpath(str(img['s3path'])))),
        'root': str(img['s3path']),
        'thumbnail': str(str(img['httppath']) + "thumbnail/" + str(img['filename']))
    } for img in image_path_rows]
    return render_template('gallery.html', title=title, image_paths=image_paths)


@app.route('/image/<imagefolder>/<imgname>', methods=['GET'])
def image(imagefolder, imgname):
    if session['logged_in'] == False:  # cant upload if not logged in
        flash('Please login to upload images', category='danger')
        return redirect(url_for('index'))
    username = str(session['current_user'])
    filename = str(imgname).replace("$", ".")
    # USE imagefolder as the sort key to get the AWS get image to get trans
    out_data = aws.DDB_get_image_by_filename(username, imagefolder)
    img_data = out_data[0]

    en_list = ["none"]
    fr_list = ["none"]
    es_list = ["none"]

    if img_data["text_english"] != "none":
        en_list = img_data["text_english"].split("|")

    if img_data["text_french"] != "none":
        fr_list = img_data["text_french"].split("|")

    if img_data["text_spanish"] != "none":
        es_list = img_data["text_spanish"].split("|")


    path_components = {
        'username': username,
        'dirname': imagefolder,
        'filename': filename,
        'normal': bucket_url_base+'static/images/'+username+"/"+imagefolder+"/normal/"+filename,
        'trans_en': en_list,
        'trans_fr': fr_list,
        'trans_es': es_list
    }
    # print(path_components)
    return render_template('image.html', title=imagefolder, pathcomp=path_components)


# Various error handling functions, each serving an individual purpose
# handle error if file is too large, redirect to uplod
@app.errorhandler(413)
def too_large(e):
    flash("File is too large! Please only upload images below 10MB in filesize")
    return redirect(url_for('upload'))

# handle if file not found error, 404
@app.errorhandler(404)
def not_found_error(e):
    return render_template('404.html'), 404


@app.route('/api')
def api():
    return {'hello' : 'world'}