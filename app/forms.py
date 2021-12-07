from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed, FileRequired
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import ValidationError, DataRequired, Email, EqualTo
from app.models import User
from app.apputilities import *

from app.aws import AwsSession 

aws = AwsSession()

"""
File to create different types of form fillers for the web application
"""

class LoginForm(FlaskForm):
    '''
    Login form specifies data input when logging into the site
    '''
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Sign In')


class RegistrationForm(FlaskForm):
    '''
    Registration form specifies data innput for registering new users,
    Only accessed by admin
    '''
    username = StringField('Username', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    password2 = PasswordField(
        'Repeat Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Register')

    # check to see if username is valid and is unique
    def validate_username(self, username):
        '''
        user = User.query.filter_by(username=username.data).first()
        if user is not None:
            raise ValidationError('Please use a different username.')
        '''
        user = aws.DDB_get_user(username.data)
        if user != -1:
            raise ValidationError('Please use a different username.')

    # check to see if email is valid and is unique
    def validate_email(self, email):
        user = aws.DDB_get_user_by_email(email.data)
        if user != -1:
            raise ValidationError('Please use a different email address.')

    # a command the admin can run to see all userids and usernames
    def print_users(self):
        users = aws.DDB_get_all_users()
        for u in users:
            print(u.username, u.email)

class RecoveryForm(FlaskForm):
    '''
    Used for password recovery
    '''
    username = StringField('Username', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired()])
    newpassword = PasswordField('New Password', validators=[DataRequired()])
    submit = SubmitField('Reset Account')


class PictureForm(FlaskForm):
    '''
    Used to upload a picture directly as a file
    '''
    picture = FileField('Upload picture', validators=[FileRequired(), 
                                    FileAllowed(['jpg', 'jpeg', 'png'], "You can upload only JPG, JPEG and PNG") ])
    submit = SubmitField('Upload')

class URLPictureForm(FlaskForm):
    '''
    Used to upload a picture via a URL
    '''
    urlpicture = StringField('URL to Upload Picture', validators=[DataRequired()])
    submit = SubmitField('Upload')

    def validate_urlpicture(self, urlpicture):
        new_url = urlpicture.data
        if urlpicture.data[:8] != "https://" and urlpicture.data[:7] != "http://":
            new_url = "https://" + urlpicture.data # ensures the URL starts with http:// or https://
        viable_image = check_img_url(new_url) # check if URL actually points to image, fail otherwise
        viable_image_truth = viable_image[0]
        if not viable_image_truth:
            raise ValidationError("The image URL you entered was not viable: either it has a typo, is not a png, jpg, or jpeg, is not accessible for security reasons, or is not registered as one of these image types in its file header. Please try another URL.")
        
