from base_ovr_form import BaseOVRForm, OVRError
from form_utils import split_date, ValidationError, get_address_from_freeform, options_dict, get_party_from_list
import sys, traceback

class Arizona(BaseOVRForm):

    def __init__(self):
        super(Arizona, self).__init__('https://servicearizona.com/webapp/evoter/selectLanguage')
        self.add_required_fields(['will_be_18', 'legal_resident', 'incompetent', 'disenfranchised', 'ssn_last4', 'has_separate_mailing_address', 'political_party'])

    def submit(self, user, error_callback_url = None):

        self.error_callback_url = error_callback_url

        try:
            self.language(user)
            self.init_voter_registration(user)
            self.eligibility(user)
            self.personal_information(user)
            self.change_of_address(user)
            self.update_address(user)
            self.confirm_address(user)
            self.register_to_vote(user)

            return {'status': 'failure', 'note': 'JL NOTE ~ Not sure what to do...'}
        
        except ValidationError, e:
            raise OVRError(self, message=e.message, payload=e.payload, error_callback_url=self.error_callback_url)

        except Exception, e:
            ex_type, ex, tb = sys.exc_info()
            raise OVRError(self, message="%s %s" % (ex_type, ex), payload=traceback.format_tb(tb), error_callback_url=self.error_callback_url)

    def get_default_submit_headers(self):
        # AZ does a validation check on referer, so fill it in with the current URL
        return {'Referer': self.browser.url}

    def language(self, user):
        language_form = self.browser.get_form()
        language_form['lang'].value = 'en'
        self.browser.submit_form(language_form, headers=self.get_default_submit_headers())

    def init_voter_registration(self, user):
        # a functional no-op; just click submit.
        voter_reg_form = self.browser.get_form()
        self.browser.submit_form(voter_reg_form, headers=self.get_default_submit_headers())

    def eligibility(self, user):
        eligibility_form = self.browser.get_form()
        
        # they have some Dojo trickery, and server-side validation to go with it?
        # it needs both checked and a value set. :shrug:
        eligibility_form['resident'].checked = 'checked' if user['legal_resident'] else ''
        eligibility_form['resident'].value = 'true' if user['legal_resident'] else 'false'
        
        eligibility_form['felon'].checked = 'checked' if not user['disenfranchised'] else ''
        eligibility_form['felon'].value = 'true' if not user['disenfranchised'] else 'false'
        
        eligibility_form['competent'].checked = 'checked' if not user['incompetent'] else ''
        eligibility_form['competent'].value = 'true' if not user['incompetent'] else 'false'
        
        # these are more straightforward
        eligibility_form['citizenCheck'].value = 'on' if user['us_citizen'] else 'no'
        eligibility_form['ageCheck'].value = 'on' if user['will_be_18'] else 'no'
        
        self.browser.submit_form(eligibility_form, headers=self.get_default_submit_headers())

    def personal_information(self, user):
        personal_info_form = self.browser.get_form()
        personal_info_form['firstname'].value = user['first_name']
        personal_info_form['lastname'].value = user['last_name']

        year, month, day = split_date(user['date_of_birth'])
        personal_info_form['dob'].value = '/'.join([month, day, year])

        personal_info_form['ssn3'].value = user['ssn_last4']
        personal_info_form['dln'].value = user['state_id_number']

        # specify the Continue button, not the "what if I don't know my DL number?" button, also a submit
        self.browser.submit_form(personal_info_form, submit=personal_info_form['_eventId_continue'], headers=self.get_default_submit_headers())

    def change_of_address(self, user):
        frm = self.browser.get_form()

        frm['resChange'].value = 'C'

        # user has different residential and mailing addresses on file with MVD
        if "C" in frm['mailChange'].options:
            if user['has_separate_mailing_address']:
                frm['mailChange'].value = 'C'
            else:
                frm['mailChange'].value = 'D'
        else:
            if user['has_separate_mailing_address']:
                frm['mailChange'].value = 'A'
            else:
                frm['mailChange'].value = 'N'

        self.browser.submit_form(frm, submit=frm['_eventId_continue'], headers=self.get_default_submit_headers())
    
    def update_address(self, user):
        frm = self.browser.get_form()

        frm['resAddr'].value = user['address']
        frm['resCity'].value = user['city']
        frm['resState'].value = "AZ"
        frm['resZip1'].value = user['zip']

        if user['has_separate_mailing_address']:
            address = get_address_from_freeform(user['separate_mailing_address'])
            address_components = address['components']

            mailing_address = "%s " % address_components['primary_number']

            if 'street_predirection' in address_components:
                mailing_address += "%s " % address_components['street_predirection']

            mailing_address += "%s" % address_components['street_name']

            if 'street_suffix' in address_components:
                mailing_address += " %s" % address_components["street_suffix"]

            if 'street_postdirection' in address_components:
                mailing_address += " %s" % address_components["street_postdirection"]

            frm['mailAddr'].value = mailing_address
            frm['mailCity'].value = address_components['city_name']
            frm['mailState'].value = address_components['state_abbreviation']
            frm['mailZip1'].value = address_components['zipcode']

        self.browser.submit_form(frm, submit=frm['_eventId_update'], headers=self.get_default_submit_headers())

    def confirm_address(self, user):
        frm = self.browser.get_form()

        self.browser.submit_form(frm, submit=frm['_eventId_continue'], headers=self.get_default_submit_headers())

    def register_to_vote(self, user):
        frm = self.browser.get_form()

        user["political_party"] = user["political_party"].strip()

        if user['political_party'].lower() == 'independent' or user['political_party'].lower() == "none":
            frm['partyPreference'].value = "No Party Preference"

        else:
            party_options = options_dict(frm['partyPreference'])
            # do fuzzy match to political party options
            party_choice = get_party_from_list(user['political_party'], party_options.keys())

            if party_choice in party_options.keys():
                frm['partyPreference'].value = party_options[party_choice]
            else:
                frm['otherPartyPreference'].value = user['political_party']

        frm['email'].value = user['email']

        self.browser.submit_form(frm, submit=frm['_eventId_register'], headers=self.get_default_submit_headers())


