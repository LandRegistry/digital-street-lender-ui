from datetime import datetime

import requests
from flask import (Blueprint, current_app, redirect, render_template, request,
                   url_for)

from babel import numbers
from lender_ui.views.login import login_required

# This is the blueprint object that gets registered into the app in blueprints.py.
admin = Blueprint('lender_admin', __name__)


@admin.route("/list")
@login_required
def list():
    titles_res = requests.get(current_app.config['LENDER_API_URL'] + '/titles',
                              headers={'Accept': 'application/json'})
    if not titles_res.status_code == 200:
        titles = None
        if titles_res.text:
            error_message = titles_res.text
        else:
            error_message = "Error: Lender API failed. Could not return a response."
    else:
        titles = titles_res.json()
        error_message = None

        for title in titles:
            if title['status'] == 'land_title_issued':
                title['status_display'] = 'discharge_not_proposed'
            else:
                title['status_display'] = None
                # compute status column value
                if title['proposed_title']:
                    if title['proposed_title']['restrictions']:
                        for val in title['proposed_title']['restrictions']:
                            signed_actions = val['signed_actions']
                        if signed_actions is not None:
                            if signed_actions == "remove":
                                title['status_display'] = 'discharge_consented'
                        else:
                            title['status_display'] = 'agree_to_discharge'

            # check if new charge has been added
            # get current node lender object
            lender_res = requests.get(current_app.config['LENDER_API_URL'] + '/me',
                                      headers={'Accept': 'application/json'})
            if not lender_res.status_code == 200:
                if lender_res.text:
                    error_message = lender_res.text
                else:
                    error_message = "Error: Lender API failed. Could not return a response."
            else:
                lender = lender_res.json()
                lender = lender['me']['x500']
                current_lender = {
                    "organisation": lender['organisation'],
                    "locality": lender['locality'],
                    "country": lender['country'],
                    "state": lender['state'],
                    "organisational_unit": lender['organisational_unit'],
                    "common_name": lender['common_name']
                }
                # if new charge is added then proposed_title would be empty
                if not title['proposed_title']:
                    proposed_charges = title['title']['charges']
                    proposed_restrictions = title['title']['restrictions']
                    if proposed_charges:
                        for charge in proposed_charges:
                            # check if current node lender equals lender in the charge
                            if charge['lender'] == current_lender:
                                title['status_display'] = "new_charge_added"
                                break
                    # else check if logged in lender equals lender in the charge of type restriction
                    else:
                        for restriction in proposed_restrictions:
                            if "charge" in restriction and restriction['charge']['lender'] == current_lender:
                                title['status_display'] = "new_charge_added"
                                break

    return render_template('app/admin/list.html', titles=titles, error_message=error_message)


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

    # fetch title address
    titles_res = requests.get(current_app.config['LENDER_API_URL'] + '/titles/' + title_number,
                              headers={'Accept': 'application/json'})
    title_address = ""
    if titles_res.status_code == 200:
        title = titles_res.json()
        title_address = title['title']['address']
    # CBCR is of type charge and ORES is type generic
    url = current_app.config['LENDER_API_URL'] + '/titles/' + title_number + '/restrictions'
    title_restriction_res = requests.get(url, params={'type': 'CBCR'}, headers={'Accept': 'application/json'})
    error_message = None
    if not title_restriction_res.status_code == 200:
        title_restrictions = None

        if title_restriction_res.text:
            error_message = title_restriction_res.text
        else:
            error_message = "Error: Lender API failed. Could not return a response."
    else:
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
            title_restriction['lender'] = title_restriction['consenting_party']['organisation']

            # change date format
            date_obj = datetime.strptime(title_restriction['charge']['date'], '%Y-%m-%dT%H:%M:%S.%f')
            title_restriction['date'] = datetime.strftime(date_obj, '%d %B %Y')

            # change amount format if exists
            if 'charge' in title_restriction:
                title_restriction['charge']['amount'] = numbers.format_currency(
                    title_restriction['charge']['amount'],
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
                           title_number=title_number, title_address=title_address,
                           error_message=error_message)
