"""Prepare operator feedback without GitHub credentials or a web service.

The graphical shells collect the report locally and ask Windows to open the
default email application with a pre-filled ``mailto:`` URI.  Nothing is sent
by QCS: the operator reviews the message and selects Send in the email client.
"""
import os
from urllib.parse import quote, urlencode


SUPPORT_EMAIL = 'fccardoso@sage.coppe.ufrj.br'
MAX_NAME_LENGTH = 120
MAX_TITLE_LENGTH = 200
MAX_DESCRIPTION_LENGTH = 4000


class FeedbackError(ValueError):
    """A report cannot be prepared or its email application cannot open."""


def validate_report(name, title, description):
    """Return normalized fields, requiring a title and description."""
    fields = tuple(str(value or '').strip()
                   for value in (name, title, description))
    clean_name, clean_title, clean_description = fields
    if not clean_title:
        raise FeedbackError('Enter a title for the report.')
    if not clean_description:
        raise FeedbackError('Describe the problem or suggestion.')
    limits = (
        ('Name', clean_name, MAX_NAME_LENGTH),
        ('Title', clean_title, MAX_TITLE_LENGTH),
        ('Description', clean_description, MAX_DESCRIPTION_LENGTH),
    )
    for label, value, maximum in limits:
        if len(value) > maximum:
            raise FeedbackError(
                '%s is too long (%d characters; maximum %d).'
                % (label, len(value), maximum))
    return clean_name, clean_title, clean_description


def build_report_text(name, title, description, qcs_version):
    """Build the complete plain-text report used by email and clipboard."""
    clean_name, clean_title, clean_description = validate_report(
        name, title, description)
    return (
        'Name: %s\n'
        'QCS version: %s\n\n'
        'Title: %s\n\n'
        'Description:\n%s'
        % (clean_name or 'Not provided', str(qcs_version).strip(),
           clean_title, clean_description))


def build_mailto_uri(name, title, description, qcs_version):
    """Return a standards-encoded mailto URI for the support address."""
    clean_name, clean_title, clean_description = validate_report(
        name, title, description)
    version = str(qcs_version).strip()
    subject = '[QCS %s] %s' % (version, clean_title)
    body = build_report_text(
        clean_name, clean_title, clean_description, version)
    query = urlencode(
        {'subject': subject, 'body': body}, quote_via=quote)
    return 'mailto:%s?%s' % (SUPPORT_EMAIL, query)


def open_feedback_email(name, title, description, qcs_version, opener=None):
    """Open the default mail client and return the URI used.

    ``opener`` is injectable so the self-test can prove the exact request
    without launching a real application.
    """
    uri = build_mailto_uri(name, title, description, qcs_version)
    launch = opener or os.startfile
    try:
        launch(uri)
    except OSError as exc:
        raise FeedbackError(
            'Windows could not open an email application. Use Copy report '
            'and paste it into your preferred email service.') from exc
    return uri
