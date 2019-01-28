from flask import Blueprint, render_template, url_for, request, redirect, current_app, session
import requests
from lender_ui.views.login import login_required
from datetime import datetime
from babel import numbers
import json

# This is the blueprint object that gets registered into the app in blueprints.py.
admin = Blueprint('lender_admin', __name__)


@admin.route("/list")
@login_required
def list():
    titles_res = requests.get(current_app.config['LENDER_API_URL'] + '/titles',
                              headers={'Accept': 'application/json'})
    if titles_res.status_code == 200:
        titles = titles_res.json()

    for title in titles:
        if title['proposed_title']:
            title['status'] = 'agree_to_discharge'
            if title['proposed_title']['restrictions']:
                signed_actions = [d['signed_actions'] for d in title['proposed_title']['restrictions']]
                if signed_actions:
                    if any(value == "remove" for value in signed_actions):
                        title['status'] = 'discharge_consented'

    return render_template('app/admin/list.html', titles=titles)


@admin.route("/discharge-consent/<string:title_number>", methods=['GET', 'POST'])
@login_required
def charge_removal_consent(title_number):
    # Form posted
    if request.method == 'POST':
        url = current_app.config['LENDER_API_URL'] + '/titles/' + title_number + '/restrictions'
        title_restriction_res = requests.delete(url, headers={'Accept': 'application/json'})
        if title_restriction_res.status_code == 200:
            return redirect(url_for('lender_admin.list'))
        else:
            return redirect(url_for('lender_admin.charge_removal_consent', title_number=title_number,
                                    error_message='Error: ' + title_restriction_res.text))

    # CBCR is of type charge and ORES is type generic
    url = current_app.config['LENDER_API_URL'] + '/titles/' + title_number + '/restrictions'
    title_restriction_res = requests.get(url, params={'type': 'CBCR'}, headers={'Accept': 'application/json'})
    if title_restriction_res.status_code == 200:
        title_restrictions = title_restriction_res.json()

    placeholders = [

                      {"placeholder_str": "**RT**", "field": "restriction_type"},
                      {"placeholder_str": "**RD**", "field": "date"},
                      {"placeholder_str": "**RA**", "field": "charge/amount"},
                      {"placeholder_str": "**RO**", "field": "lender"},
                      {"placeholder_str": "*CD*", "field": "date"},
                      {"placeholder_str": "*CP*", "field": "lender"}
    ]

    # loop over titles to replace placeholders in the restriction text
    for title_restriction in title_restrictions:
        # hard code seller's lender in the restriction object
        title_restriction['lender'] = 'Loans4homes'

        # change date format if exists
        if 'date' in title_restriction:
            # assign the format the input date is in
            date_obj = datetime.strptime(title_restriction['date'], '%Y-%m-%dT%H:%M:%S')
            title_restriction['date'] = datetime.strftime(date_obj, '%d %B %Y')

        # change amount format if exists
        if 'charge' in title_restriction:
            title_restriction['charge']['amount'] = numbers.format_currency(title_restriction['charge']['amount'],
                                                                            title_restriction['charge']['amount_currency_code'])

        # loop over placeholders to replace them
        for placeholder in placeholders:
            fields = placeholder['field'].split("/")

            # store in temp variable to avoid overriding
            restriction_temp = title_restriction

            # loop over fields if it is an object
            for value in fields:
                if value in restriction_temp:
                    restriction_temp = restriction_temp[value]
                else:
                    restriction_temp = None
                    # if first element of fields isn't in the restrictions then the rest would'nt be either,
                    # so break
                    break

            if restriction_temp:
                restriction_text = title_restriction['restriction_text']
                title_restriction['restriction_text'] = restriction_text.replace(placeholder['placeholder_str'],
                                                                                 str(restriction_temp))
    return render_template('app/admin/discharge_consent.html', title_restrictions=title_restrictions,
                           title_number=title_number)
