from flask import request, make_response
import json
from bson import json_util
from mongomodels import MongoModel
from functools import wraps
from bson import ObjectId
import inflection

class ApiError(Exception):
    def __init__(self, message, status_code=400):
        self.message = message
        self.status_code = status_code
        super(ApiError, self).__init__(self)


def assert_api(condition, message, status_code=400):
    if not condition:
        raise ApiError(message, status_code)

class Serializer(object):

    def __init__(self, column_mapping):
        self.column_mapping = column_mapping

    def serialize(self, obj):
        if isinstance(obj, ObjectId):
            return str(obj)

        if isinstance(obj, MongoModel):
            ret = {}
            for k in obj.__columns__.keys():
                ret_k = self.column_mapping.get(k, k)
                if getattr(obj.__class__, 'visible_columns', None):
                    if k in obj.visible_columns:
                        ret[ret_k] = getattr(obj, k)
                else:
                    ret[ret_k] = getattr(obj, k)

            if getattr(obj, 'serialize', None):
                for k in obj.serialize:
                    ret[k] = getattr(obj, k)
            return ret
        return json_util.default(obj)


class Resource(object):
    def __init__(self, model, access_control):
        self.model = model
        self.access_control = access_control or self.default_access_control

    def list(self, limit=None, offset=None):
        return self.model.query.all()

    def get(self, id):
        return self.model.get_by_id(id)

    def delete(self, id):
        o = self.model.get_by_id(id).first()
        o.delete()
        return o

    def put(self, id, data):
        o = self.model(**data)
        o.save()
        return o

    def patch(self, id, data):
        o = self.model.get_by_id(id)
        for k, v in data.iteritems():
            setattr(o, k, v)
        o.save()
        return o

    def post(self, id, data):
        o = self.model.get_by_id(id).first()
        for k, v in data.iteritems():
            setattr(o, k, v)
        o.save()
        return o

    def default_access_control(self, user, *args, **kwargs):
        assert_api(user, "requires authentication", 403)

    def list_(self, user, data):
        self.access_control(user, data)
        return self.list()

    def get_(self, user, data, id):
        self.access_control(user, data, id)
        return self.get(id)

    def delete_(self, user, data, id):
        self.access_control(user, data, id)
        return self.delete(id)

    def put_(self, user, data, id):
        self.access_control(user, data, id)
        return self.put(id, data)

    def patch_(self, user, data, id):
        self.access_control(user, data, id)
        return self.patch(id, data)

    def post_(self, user, data, id):
        self.access_control(user, data, id)
        return self.post(id, data)

class Api(object):

    def __init__(self, app, user_class=None, serializer=None):
        self.app = app
        self.serializer = serializer
        self.user_class = user_class
        self.api_methods = {}

    def gen_doc(self):
        for i, k in self.api_methods.iteritems():
            print i, '  '
            print "=" * 50
            doc = k['fn'].__doc__ or ""
            doc = map(lambda x: x.strip(), doc.split('\n'))
            doc = '\n'.join(doc)
            print k['kwargs']['methods'], k['rule']
            requires = k['requires']
            if requires:
                requires = requires.keys()
            print 'requires', requires, '  '
            print 'public', k['public'], '  '
            print doc.strip(), '  '
            print '  '
            print '  '

    def add_method(self, fn, path, methods, requires=None, public=False):
        @wraps(fn)
        def decorated(*args, **kwargs):
            if not public:
                token = request.args.get('token', None)
                user = self.user_class.query.filter_by(token=token).first()
                if not user:
                    return make_response(json.dumps({'err': 'api token is wrong'}), 403)

            args = list(args)
            if request.method in ['POST', 'PUT']:
                try:
                    data = request.get_json(force=True)
                except:
                    reason = ""
                    try:
                        json.loads(request.data)
                    except Exception as e:
                        reason = e.message
                    return json.dumps({'resp': "", 'err': "post body is not json [ %s ]" % reason}, default=self.serializer)
            else:
                data = {}

            if requires:
                for k, v in requires.iteritems():
                    if not k in data:
                        if callable(v):
                            is_ok = v(data)
                        else:
                            is_ok = k in data

                        if not is_ok:
                            return make_response(json.dumps({'err': 'required parameter '
                                                                'is missing "%s"' % k}), 403)
            args.insert(0, data)
            if not public:
                args.insert(0, user)
            try:
                print ">>>>", args, kwargs
                ret = fn(*args, **kwargs)
            except ApiError as err:
                return make_response(json.dumps({'err': err.message}), err.status_code)

            return json.dumps({'resp': ret, 'err': None}, default=self.serializer)
        return decorated

    def route(self, rule, *args, **kwargs):
        def decorator(fn):
            requires = kwargs.pop('requires', None)
            public = kwargs.pop('public', False)
            self.api_methods[fn.__name__] = {'rule': rule, 'kwargs': kwargs,
                                             'fn': fn,
                                             'requires': requires,
                                             'public': public}
            callback_fn = self.add_method(fn, path=None, methods=None, requires=requires, public=public)

            # now we add this path to flask
            endpoint = kwargs.pop('endpoint', None)
            self.app.add_url_rule(rule, endpoint, callback_fn, **kwargs)
            return callback_fn
        return decorator

    def method(self, requires=None, public=False):
        def decorator(fn):
            return self.add_method(fn, path=None, methods=None, requires=requires, public=public)
        return decorator

    def _add_api_method(self, rule, fn, **kwargs):
        requires = kwargs.pop('requires', None)
        public = kwargs.pop('public', False)
        self.api_methods[fn.__name__] = {'rule': rule, 'kwargs': kwargs, 'fn': fn, 'requires': requires, 'public': public}
        callback_fn = self.add_method(fn, path=None, methods=None, requires=requires, public=public)

        # now we add this path to flask
        endpoint = kwargs.pop('endpoint', None)
        self.app.add_url_rule(rule, endpoint, callback_fn, **kwargs)
        return callback_fn


    def expose(self, model, route='/api', access_control=None, resource_class=Resource, **kwargs):
        """
        this adds methods for updating/adding the objects defined by model

        eg: if you expose User(MongoModel) class this will add

            POST /api/users => create
            PUT /api/users/:id: => update
            PATCH /api/user/:id: => update
            DELETE /api/user/:id: => delete
            GET /api/user/:id: => returns user
            GET /api/users => returns all users (you can use ?limit=... )

        """
        endpoint_name = route + '/' + inflection.pluralize(inflection.underscore(model.__name__))

        resource = Resource(model=model, access_control=access_control)
        self._add_api_method(endpoint_name, resource.list_, methods=['GET'])
        self._add_api_method('%s/<id>' % endpoint_name, resource.get_, methods=['GET'])

        self._add_api_method(endpoint_name, resource.put_, methods=['PUT'])

        self._add_api_method('%s/<id>' % endpoint_name, resource.delete_, methods=['DELETE'])
        self._add_api_method('%s/<id>' % endpoint_name, resource.post_, methods=['POST'])
        self._add_api_method('%s/<id>' % endpoint_name, resource.patch_, methods=['PATCH'])
