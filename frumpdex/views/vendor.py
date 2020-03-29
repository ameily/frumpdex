import os
from flask import Blueprint, send_from_directory

blueprint = Blueprint('vendor', __name__, static_folder='../../node_modules', url_prefix='/vendor')

NODE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'node_modules'))

@blueprint.route('/<path:filename>')
def vendor_file(filename: str):
    return send_from_directory(NODE_DIR, filename)
