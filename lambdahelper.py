import psutil
import time
import json
import boto3
import ast
import math
from datetime import datetime
from access import access_keys
"""
This file will be on the zappa function and invoke a lambda function that is separate to the zappa instance
The lambda function call will be scheduled and thus the lambda function is the background process

Give to Lambda: cpu, memory, and disk statistics, return data analytics on the data
"""

lambda_client = boto3.client('lambda',
            # aws_access_key_id = access_keys['AWS_ACC_KEY'],
            # aws_secret_access_key = access_keys['AWS_SECRET_KEY'],
            aws_access_key_id = access_keys['AWS_ACC_KEY_LAMBDA'],
            aws_secret_access_key = access_keys['AWS_SECRET_KEY_LAMBDA'],			
            region_name = 'us-east-1')


#convert mins to datetime obj - not working as expected 
def convert_unix_to_utc(unix_in_min):
	ts = int(unix_in_min * 60)
	return datetime.utcfromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')


# data collection
# cpu_util, mem_util, disk_util, all in percentage
while True:
	time_stamp = math.floor(time.time() / 60)
	data = {}
	cpu_util = psutil.cpu_percent(interval=None)
	mem_util = psutil.virtual_memory()
	mem_util = mem_util.percent
	disk_util = psutil.disk_usage('/')
	disk_util = disk_util.percent
	data['timestamp'] = time_stamp
	data['cpu_util'] = cpu_util
	data['mem_util'] = mem_util
	data['disk_util'] = disk_util
	data['time_date'] = convert_unix_to_utc(time_stamp)
	json_data = json.dumps(data, sort_keys=True, default=str)

	print(json_data)

	# invoke lambda
	response = lambda_client.invoke(FunctionName='arn:aws:lambda:us-east-1:962907337984:function:DataAnalytics', Payload=json_data)
	# Parse return
	response_string = response['Payload'].read()  # decode to bytes
	response_decoded = response_string.decode()  # bytes to string
	response_dict = ast.literal_eval(response_decoded)  # string to dict
	message = response_dict['status']  # parse dict into proper messages
	code = response_dict['code']
	print(message)
	print(code)
	time.sleep(60)