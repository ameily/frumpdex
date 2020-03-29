
from flask import session, render_template, request, g, redirect, url_for, Blueprint


blueprint = Blueprint('auth', __name__)


@blueprint.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        token = request.form.get('token')
        user = g.db.login(token)
        if user:
            session['token'] = user['token']
            # TODO handle next GET param
            return redirect(url_for('exchange.activity'))
        else:
            error = 'Incorrect API token'
    else:
        error = None

    return render_template('login.html', error=error)
