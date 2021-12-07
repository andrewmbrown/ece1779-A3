# hashing passwords
from werkzeug.security import check_password_hash, generate_password_hash
# authenticating users, checking active status, anonyimity, id
from flask_login import UserMixin

# TODO: have to fix the imports here 
import boto3 
from boto3.dynamodb.conditions import Key
from access import access_keys
AWS_ACC_KEY = access_keys["AWS_ACC_KEY"]
AWS_SEC_KEY = access_keys["AWS_SECRET_KEY"]

session = boto3.Session(
    aws_access_key_id=AWS_ACC_KEY,
    aws_secret_access_key=AWS_SEC_KEY,
    region_name="us-east-1"
)

dynamodb = session.resource('dynamodb')
user_table = dynamodb.Table('user-test')

# File that specifies the database tables and behaviour
# Each class is a table, with some logic implemented to ensure proper usage
# NOTE: anytime db classes are changed you must: 
# either delete the migrations folder or properly migrate and upgrade database

# https://stackoverflow.com/questions/57095205/connecting-to-mysql-aws-rds-using-sqlalchemy-in-pycharm-with-python ref

class User(UserMixin):
    '''
    Model for User table entry

    id -> user ID 
    username -> unique username
    email -> unique email
    password_hash -> stored hash of provided password
    '''
    def __init__ (self, username, email, password_hash):
        self.id = username
        self.username = username
        self.email = email
        self.password_hash = password_hash
    # id = db.Column(db.Integer, primary_key=True)
    # username = db.Column(db.String(64), index=True, unique=True)
    # email = db.Column(db.String(120), index=True, unique=True)
    # password_hash = db.Column(db.String(128))
    # gallery = db.relationship('ImageLocation', backref='uploader', lazy='dynamic')
    def __repr__(self):
        return '<User {}>'.format(self.username)
    
    # Class now has method to do secure password verification
    # also to check password (hash again and check if they match)
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)



'''
@login.user_loader
def load_user(id):
    return User.query.get(int(id))
'''

# @login.user_loader
def load_user(username):
    response = user_table.query(
        KeyConditionExpression=Key('username').eq(username)
    )
    user = User(
        username=None,
        email=None,
        password_hash=None
    )
    user_list = response["Items"]
    if len(user_list) < 1:
        return user 
    else:
        raw_user = user_list[0]
        user.id = raw_user["username"]
        user.username = raw_user["username"]
        user.email = raw_user["email"]
        user.password_hash = raw_user["password_hash"]
        return user