from flask import Blueprint, request
from apikit import obj_or_404, jsonify, request_data, arg_bool
from apikit import get_limit, get_offset

from aleph import authz
from aleph.model import Entity, Collection, db
from aleph.entities import update_entity
from aleph.views.cache import enable_cache
from aleph.search import entities_query, execute_entities_query
from aleph.search import suggest_entities

blueprint = Blueprint('entities_api', __name__)


def check_authz(entity, permission):
    permissions = authz.collections(permission)
    for collection in entity.collections:
        if collection.id in permissions:
            return
    authz.require(False)


def get_collections(data):
    collections = []
    for coll_id in data.get('collections'):
        if isinstance(coll_id, dict):
            coll_id = coll_id.get('id')
        collections.append(coll_id)
    return Collection.all_by_ids(collections).all()


@blueprint.route('/api/1/entities', methods=['GET'])
def index():
    q = entities_query(request.args)
    q['size'] = get_limit(default=50)
    q['from'] = get_offset()
    res = execute_entities_query(request.args, q,
                                 doc_counts=arg_bool('doc_counts'))
    return jsonify(res)


@blueprint.route('/api/1/entities', methods=['POST', 'PUT'])
def create():
    data = request_data()
    data.pop('id', None)
    data['collections'] = get_collections(data)
    for collection in data['collections']:
        authz.require(authz.collection_write(collection.id))
    entity = Entity.save(data)
    db.session.commit()
    update_entity(entity)
    return view(entity.id)


@blueprint.route('/api/1/entities/_suggest', methods=['GET'])
def suggest():
    collections = authz.collections(authz.READ)
    enable_cache(vary=collections, server_side=False)
    return jsonify(suggest_entities(request.args))


@blueprint.route('/api/1/entities/<id>', methods=['GET'])
def view(id):
    entity = obj_or_404(Entity.by_id(id))
    check_authz(entity, authz.READ)
    return jsonify(entity)


@blueprint.route('/api/1/entities/_lookup', methods=['GET'])
def lookup():
    entity = obj_or_404(Entity.by_identifier(request.args.get('scheme'),
                                             request.args.get('identifier')))
    check_authz(entity, authz.READ)
    return jsonify(entity)


@blueprint.route('/api/1/entities/<id>', methods=['POST', 'PUT'])
def update(id):
    entity = obj_or_404(Entity.by_id(id))
    check_authz(entity, authz.WRITE)
    data = request_data()
    data['id'] = entity.id
    possible_collections = authz.collections(authz.WRITE)
    possible_collections.extend([c.id for c in entity.collections])
    data['collections'] = [c for c in get_collections(data)
                           if c.id in possible_collections]
    entity = Entity.save(data, merge=arg_bool('merge'))
    db.session.commit()
    update_entity(entity)
    return view(entity.id)


@blueprint.route('/api/1/entities/<id>/merge/<other_id>', methods=['DELETE'])
def merge(id, other_id):
    entity = obj_or_404(Entity.by_id(id))
    check_authz(entity, authz.WRITE)
    other = obj_or_404(Entity.by_id(other_id))
    check_authz(other, authz.WRITE)
    entity.merge(other)
    db.session.commit()
    update_entity(entity)
    update_entity(other)
    return view(entity.id)


@blueprint.route('/api/1/entities/<id>', methods=['DELETE'])
def delete(id):
    entity = obj_or_404(Entity.by_id(id))
    check_authz(entity, authz.WRITE)
    entity.delete()
    db.session.commit()
    update_entity(entity)
    return jsonify({'status': 'ok'})
