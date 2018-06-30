import datetime
from flask import current_app
import json
import psycopg2
from ovr_forms.form_utils import clean_browser_response
from pdf_forms.storage import sign_s3_url
from config import DATABASE_URL


def get_db():
    """Opens a new database connection if there is none yet for the
    current application context.
    """
    db = psycopg2.connect(DATABASE_URL)

    # create table
    cur = db.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS logged_forms (id serial PRIMARY KEY, uid varchar(255), ts timestamp, state varchar, status json, failed boolean default false, parsed text); ")
    cur.execute("CREATE INDEX IF NOT EXISTS logged_forms_uid on logged_forms (uid);")
    db.commit()

    return db


def log_response(form, status):
    if current_app.config.get('TESTING'):
        return False

    db = get_db()
    cur = db.cursor()
    sql = "INSERT INTO logged_forms (ts, uid, state, status, failed, parsed) VALUES (NOW(), %s, %s, %s, %s, %s) RETURNING id;"
    parsed = "OMG"
    
    if form.__class__.__name__ == "NVRA":
        parsed = str(form.pdf_url)
    elif form and form.browser._cursor > 0:
        parsed = str(form.browser.parsed)
    else:
        parsed = "unable to log form response"

    cur.execute(sql, (
        str(form.get_uid()),
        form.__class__.__name__,
        json.dumps(status),
        True if "status" not in status or not status["status"] == "success" else False,
        parsed
    ))
    id_of_new_row = cur.fetchone()[0]

    db.commit()
    db.close()

    return id_of_new_row


def update_form_urls():
    db = get_db()
    cur = db.cursor()

    query = "SELECT id, settings from users where settings->>'nvra_pdf_url' not LIKE %s"
    s3_bucket_url = "https://{0}.s3.amazonaws.com".format(current_app.config.BUCKET_NAME)
    s3_form_path = "/forms/%/hellovote-registration-print-me.pdf?Signature=%"
    cur.execute(query, (s3_bucket_url + s3_form_path,))
    ids = cur.fetchall()

    print len(ids), "forms without signed urls"

    for (user_id, settings) in ids:
        pdf_filename = settings['nvra_pdf_url'].replace(s3_bucket_url, '')
        signed_url = sign_s3_url(current_app.config.BUCKET_NAME, pdf_filename)
        settings['nvra_pdf_url'] = signed_url

        update_sql = "UPDATE users SET settings=%s WHERE id = %s"
        cur.execute(update_sql, (json.dumps(settings), user_id))
        db.commit()
    db.close()
