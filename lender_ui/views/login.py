from flask import Blueprint, render_template, url_for, request, redirect, current_app, session
from functools import wraps
import requests

# This is the blueprint object that gets registered into the app in blueprints.py.
login = Blueprint('login', __name__)


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_name' in session:
            return f(*args, **kwargs)
        else:
            return redirect(url_for('login.user_login', next=request.full_path))
    return decorated_function


@login.route("/login", methods=['GET', 'POST'])
def user_login():
    if request.method == 'POST':
        user_details_res = requests.get(
            current_app.config['LENDER_MANAGEMENT_API_URL'] + '/users', params={
                "email_address": str(request.form.get('email').lower())
            },
            headers={'Accept': 'application/json'})
        if user_details_res.status_code == 200:
            user_details = user_details_res.json()
            if user_details:
                for user in user_details:
                    session['user_name'] = user['first_name'] + " " + user['last_name']
                    session['user_id'] = user['identity']
                    session['email'] = user['email_address']
                return redirect(request.form.get('redirect_url'))
            else:
                # in case of invalid credentials, the previous redirect url is
                # lost so pass it back to the login form in a new variable
                redirect_url = request.form.get('redirect_url')
                return render_template('app/login.html', redirect_url=redirect_url, error_message="User not found.")

    if request.method == 'GET':
        # if user already logged in then redirect to index
        if session.get('user_name') is not None:
            return redirect(url_for("index.index_page"))

        redirect_url = ""
        # handle any malicious redirects in the login URL
        if request.args.get('next', ''):
            # append the next url to the domain name
            redirect_url = request.url_root.strip("/") + request.args.get('next', '')
        return render_template('app/login.html', redirect_url=redirect_url)


@login.route("/logout/")
@login_required
def logout():
    session.clear()
    return redirect(url_for('index.index_page'))
