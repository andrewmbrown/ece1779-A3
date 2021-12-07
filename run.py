#!venv/bin/python
from app import routes
#webapp.run()
if __name__=="__main__":
    routes.app.run(host='0.0.0.0')