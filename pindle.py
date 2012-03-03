#!/usr/bin/env python

import argparse
import datetime
import decruft
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from email import Charset
# Charset.add_charset('utf-8', Charset.QP, Charset.QP, 'utf-8')
import json
import pinboard
import readability
import smtplib
import httplib2
import re

HTML_HEAD = '<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN"><html><head><META http-equiv="Content-Type" content="text/html; charset=utf-8"></head><body>'
HTML_TAIL = '</body></html>'

def send_via_smtp(conf, toaddr, subj, body='', attach=None):
    smtp = conf['smtp']

    if attach:
        # Turn the subject into a safe filename
        filename = re.sub('[^a-zA-Z0-9_.() -]+', '', subj)

        # Amazon requires us to attach a document
        msg = MIMEMultipart()
        msg.attach(MIMEText(body))
        part = MIMEApplication(HTML_HEAD + attach.encode('utf-8') + HTML_TAIL)
        part.add_header('Content-Disposition', 'attachment', filename=filename + '.html')
        msg.attach(part)
    else:
        msg = MIMEText(body)

    msg['Subject'] = subj
    msg['From'] = smtp['from']
    msg['To'] = toaddr

    server = smtplib.SMTP('%s:%s' % (smtp['server'], smtp['port']))
    server.starttls()
    server.login(smtp['user'], smtp['password'])
    server.sendmail(smtp['from'], [toaddr], msg.as_string())
    server.quit()

def send_to_kindle(conf, b, doc):
    send_via_smtp(conf, conf['kindle']['email'], doc.title(), attach=doc.summary())

def main(args):
    config = json.load(open(args.config))

    p = pinboard.open(config['pinboard']['user'], config['pinboard']['password'])
    # Get today's posts to read
    bookmarks = [b for b in p.posts(date=datetime.datetime.now()) if b.get('toread', 'no') == 'yes']
    for b in bookmarks:
        h = httplib2.Http()
        resp, content = h.request(b['href'])
        doc = decruft.Document(content)

        # Send that mail
        send_to_kindle(config, b, doc)

        # Mark it sent
        keys = ['description', 'extended', 'tags']
        updated = {}
        for key in keys:
            updated[key] = b[key]
        updated['replace'] = 'yes'
        updated['toread'] = 'no'
        updated['url'] = b['href']
        p.add(**updated)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Propogate Pinboard bookmarks.')
    a = parser.add_argument

    a('config', help='JSON file of usernames, passwords and state')

    args = parser.parse_args()
    main(args)
