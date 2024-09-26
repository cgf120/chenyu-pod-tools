from flask import Blueprint, request, jsonify

from utils.util import huggingface_repo_info
from . import db
from .models import Model

api_bp = Blueprint('api', __name__)


@api_bp.route('/models', methods=['POST'])
def create_model():
    data = request.get_json()
    new_model = Model()
    identity = data['name'] # huggingface就是repoId c站就是sha256
    new_model.model_type = data['model_type']
    if Model.query.get(identity) is not None:
        return jsonify({'message': '模型已存在'}), 400
    new_model.sha256 = identity
    if new_model.model_type == "1":
        new_model.sha256 = huggingface_repo_info(identity).sha
    new_model.name = identity
    db.session.add(new_model)
    db.session.commit()
    return jsonify({'message': '添加成功'}), 200


@api_bp.route('/models/<string:sha256>', methods=['GET'])
def get_model(sha256):
    model = Model.query.get_or_404(sha256)
    return jsonify(model.to_dict())
