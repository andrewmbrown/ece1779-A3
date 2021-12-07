import requests 
       
extension_dict = {
    'image/png': '.png',
    'image/jpg': '.jpg',
    'image/jpeg': '.jpeg'
} # used to associate request header with appropriate extension
            
def check_img_url(img_url):
    '''
    Utility function that takes an image URL and returns a tuple (True, header) if an image,
    and (False, None) otherwise
    '''
    allowed_headers = ["image/png", "image/jpg", "image/jpeg"] # request header types
    try:
        req_attempt = requests.head(img_url)
        req_header = req_attempt.headers["content-type"]
        if req_header in allowed_headers:
            return (True, req_header)
        else:
            return (False, None)
    except:
        return (False, None) # return false on error or failure 

