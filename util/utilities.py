import os
import configparser

def getEmtpDirectory():
    current = os.path.dirname(__file__)
    while current != '':
        if 'emtp' in os.listdir(current):
            break
        current = os.path.dirname(current)
        if current == '':
             raise FileNotFoundError("Project root (with 'emtp' folder) not found")
    path = os.path.join(current, 'emtp')
    return path
    
def getConfig(config_name='config.ini'):
    config = configparser.ConfigParser()
    config_path = os.path.join(getEmtpDirectory(), config_name)
    config.read(config_path)
    return config    