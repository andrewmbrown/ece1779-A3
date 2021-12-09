import boto3 
from boto3.dynamodb.conditions import Key, Attr
from app.models import User 

from access import access_keys

from werkzeug.security import check_password_hash, generate_password_hash

class AwsSession:

    def __init__(self):

        self.AWS_ACC_KEY = access_keys['AWS_ACC_KEY']
        self.AWS_SEC_KEY = access_keys['AWS_SECRET_KEY']

        self.user_table_name = 'user-table-01'
        self.image_table_name = 'image-location-table-01'

        session = boto3.Session(
                aws_access_key_id=self.AWS_ACC_KEY,
                aws_secret_access_key=self.AWS_SEC_KEY,
                region_name='us-east-1')
        self.s3 = boto3.client('s3', 
            aws_access_key_id=self.AWS_ACC_KEY, 
            aws_secret_access_key=self.AWS_SEC_KEY, 
            region_name="us-east-1")
        self.ddb = session.resource('dynamodb')
        
        self.user_table = self.ddb.Table(self.user_table_name)
        self.image_table = self.ddb.Table(self.image_table_name)

        self.bucket = 'ece1779a3g82'
        self.bucket_url_base = 'https://ece1779a3g82.s3.amazonaws.com/'

    def DDB_get_user(self, username):

        response = self.user_table.query(
            KeyConditionExpression=Key('username').eq(username)
        )
        if len(response["Items"]) < 1:
            # no users found with that username
            return -1
        raw_user = response["Items"][0]
        user = User(
                username=raw_user["username"],
                email=raw_user["email"],
                password_hash=raw_user["password_hash"]
            )
        return user

    def DDB_add_user(self, username, email, password):
        password_hash = generate_password_hash(password)

        new_user = {
            'username': username,
            'email': email,
            'password_hash': password_hash
        }

        put_response = self.user_table.put_item(Item=new_user)
        return put_response

    def DDB_get_user_by_email(self, email):
        response = self.user_table.scan(
            FilterExpression=Attr('email').eq(email)
        )
        if len(response["Items"]) < 1:
            return -1
        raw_user = response["Items"][0]
        user = User(
                username=raw_user["username"],
                email=raw_user["email"],
                password_hash=raw_user["password_hash"]
            )
        return user

    def DDB_get_all_users(self):
        response = self.user_table.scan()
        if len(response["Items"]) < 1:
            return -1
        user_list = []
        for user_json in response["Items"]:
            printing_user = User(
                username=user_json["username"], 
                email=user_json["email"],
                password_hash=user_json["password_hash"]
            )
            user_list.append(printing_user)
        return user_list

    def DDB_upload_image(self, image_json):
        put_response = self.image_table.put_item(Item=image_json)
        return put_response 

    def DDB_get_images_by_user(self, username):
        response = self.image_table.query(
            KeyConditionExpression=Key("username").eq(username)
        )
        return response["Items"]
