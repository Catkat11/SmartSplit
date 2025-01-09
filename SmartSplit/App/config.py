import os


class Config:
    SQLALCHEMY_DATABASE_URI = 'postgresql://postgres:tab@localhost:5432/SmartSplit'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = os.urandom(24)
