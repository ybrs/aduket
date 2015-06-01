from flask import Flask
from flask.ext.cors import CORS

import logging
logger = logging.getLogger(__name__)

from mongomodels import MongoModel, Column, String
from mongomodels.validators import in_, notnull
import requests
import json
import redis
import hashlib

from aduket.api_server import Api, ApiError, assert_api, Serializer

from pymongo import MongoClient
client = MongoClient()

from mongomodels import connections, MongoModel, belongs_to

connections.add(client.timetracker)


api_column_mapping = {
    '_id': 'id'
}

class User(MongoModel):
    __collection__ = 'users'
    token = Column(String)
    name = Column(String)
    email = Column(String)
    password = Column(String)
    timezone = Column(String)

    @classmethod
    def hash_password(self, password):
        h = hashlib.new('sha1')
        h.update("Nobody inspects the spammish repetition %s" % password)
        return h.hexdigest()

class Todo(MongoModel):
    belongs_to(User)
    title = Column(String)
    description = Column(String)


app = Flask(__name__)
cors = CORS(app, allow_headers='Content-Type')

serializer = Serializer(column_mapping=api_column_mapping)
api = Api(app,
          user_class=User,
          serializer=serializer.serialize)


@api.route(
    '/api/register', methods=['POST'],
    public=True, requires={'name': True, 'email': True,
                                   'password': True, 'timezone': True})
def register(data):
    """
    this registers user

    """
    assert_api(not User.query.filter_by(name=data['name']).first(), 'name not unique')
    assert_api(not User.query.filter_by(email=data['email']).first(), 'email not unique')
    assert_api(not len(data['password'])<5, 'password too short')
    assert_api(not len(data['password'])>50, 'password too long - %s' % len(data['password']))

    user = User()
    user.name = data['name']
    user.email = data['email']
    user.timezone = data['timezone']
    user.save()
    user.password = User.hash_password(data['password'])
    user.token = User.hash_password(str(user._id))
    user.save()
    return user

@api.route(
    '/api/login', methods=['POST'],
    requires={'name': True, 'password': True}, public=True)
def login(data):
    """
    logins user, returns a token
    """
    p = User.hash_password(data['password'])
    user = User.query.filter_by(name=data['name'], password=p).first()
    assert_api(user, 'user not found')
    return user

from aduket.api_server import Resource

# this adds these methods
# GET /users - returns users list
# POST /users - create a user

# GET /users/<id> - returns user
# PUT /users/<id> - update a user
# DELETE /users/<id> - delete a user
# PATCH /users/<id> - update a user (now it does the same thing as put)
api.expose(User)

def is_owner(user, data):
    if data:
        assert_api(str(user._id) == data['user_id'], "wrong user", 403)

class TodoResource(Resource):

    def list(self, limit=None, offset=None):
        return Todo.query.filter_by(user_id=api.current_user.id).all()

api.expose(Todo, access_control=is_owner)

if __name__ == '__main__':

    app.run(debug=True, host="0.0.0.0", port=8194)