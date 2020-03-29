
from flask import g, render_template, Blueprint

from .lib import auth_required


blueprint = Blueprint('exchange', __name__)


@blueprint.route('/activity')
@auth_required
def activity():
    return render_template('exchange-activity.html')
