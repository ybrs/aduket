import os
from example_api import app
import unittest
import json
import datetime
import pymongo
from mongomodels import connections

class FlaskrTestCase(unittest.TestCase):

    def setUp(self):
        client = pymongo.MongoClient()
        client.drop_database('aduket_test')
        connections.add(client.aduket_test)
        app.config['TESTING'] = True
        self.client = app.test_client()

    def test_register(self):
        r = self.client.post('/api/register',
            headers = [('Content-Type', 'application/json')],
            data=json.dumps({
                'name': 'ybrs',
                'email': 'aybars.badur@gmail.com',
                'password': '12345',
                'timezone': 'Europe/Istanbul'
            })
        )
        self.assertEqual(r.status_code, 200)

        r = self.client.post('/api/login',
            headers = [('Content-Type', 'application/json')],
            data=json.dumps({
                'name': 'ybrs',
                'password': '12345',
            })
        )
        self.assertEqual(r.status_code, 200, "login")

        token = json.loads(r.data)['resp']['token']
        assert token

        r = self.client.get('/api/users?token=%s' % token,
            headers = [('Content-Type', 'application/json')]
        )


        users = json.loads(r.data)['resp']
        assert len(users) == 1
        assert users[0]['name'] == 'ybrs'

        self.assertEqual(r.status_code, 200, "/api/users")

        r = self.client.get('/api/users/%s?token=%s' % (users[0]['id'], token),
            headers = [('Content-Type', 'application/json')]
        )

        self.assertEqual(r.status_code, 200, "GET /api/user/:id:")
        user = json.loads(r.data)['resp']
        assert user['name'] == 'ybrs'






    def tearDown(self):
        pass

if __name__ == '__main__':
    unittest.main()