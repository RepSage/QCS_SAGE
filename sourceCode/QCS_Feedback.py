"""Submit operator feedback without exposing a GitHub credential in QCS.

The released application sends a small JSON report to a Cloudflare Worker.
Only that Worker holds the repository credential. If submission fails, the
form stays open so the operator can retry or copy individual fields normally.
"""
import json
import socket
import ssl
import urllib.error
import urllib.request


# Public Worker route; the GitHub credential remains only in Cloudflare.
FEEDBACK_ENDPOINT = (
    'https://qcs-sage-feedback.qcs-sage.workers.dev/feedback')
TIMEOUT_S = 15
MAX_NAME_LENGTH = 120
MAX_TITLE_LENGTH = 200
MAX_DESCRIPTION_LENGTH = 4000
MAX_RESPONSE_BYTES = 64 * 1024
_HEADERS = {
    'Accept': 'application/json',
    'Content-Type': 'application/json; charset=utf-8',
    'User-Agent': 'QCS-SAGE-feedback',
}


class FeedbackError(ValueError):
    """A report is invalid or could not be submitted safely."""


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


def _ssl_context():
    """Use the CA bundle shipped with QCS when it is available."""
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        return ssl.create_default_context()


def _service_error(payload, fallback):
    """Return a short service-provided error without exposing response details."""
    try:
        message = json.loads(payload.decode('utf-8')).get('error')
    except (UnicodeDecodeError, json.JSONDecodeError, AttributeError):
        message = None
    return str(message).strip() if message else fallback


def submit_feedback(name, title, description, qcs_version, *, endpoint=None,
                    urlopen=None):
    """Submit one report and return its public issue number and URL.

    ``endpoint`` and ``urlopen`` are injectable so the self-test proves the
    exact outbound request without touching the live service.
    """
    clean_name, clean_title, clean_description = validate_report(
        name, title, description)
    target = str(endpoint if endpoint is not None else FEEDBACK_ENDPOINT).strip()
    if not target.startswith('https://'):
        raise FeedbackError(
            'The feedback service is not configured in this QCS build. '
            'Copy your text before closing the window.')
    payload = json.dumps({
        'name': clean_name,
        'title': clean_title,
        'description': clean_description,
        'qcs_version': str(qcs_version).strip(),
        # Hidden honeypot understood by the Worker; QCS never fills it.
        'website': '',
    }, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
    request = urllib.request.Request(
        target, data=payload, headers=_HEADERS, method='POST')
    open_request = urlopen or urllib.request.urlopen
    try:
        with open_request(
                request, timeout=TIMEOUT_S, context=_ssl_context()) as response:
            raw = response.read(MAX_RESPONSE_BYTES + 1)
    except urllib.error.HTTPError as exc:
        raw = exc.read(MAX_RESPONSE_BYTES + 1)
        if exc.code == 429:
            fallback = ('Too many reports were submitted from this connection. '
                        'Wait one minute and try again.')
        elif 400 <= exc.code < 500:
            fallback = 'The feedback service refused this report.'
        else:
            fallback = ('The feedback service is temporarily unavailable. '
                        'Your text is still in the form; try again later.')
        raise FeedbackError(_service_error(raw, fallback)) from exc
    except (urllib.error.URLError, socket.timeout, TimeoutError) as exc:
        raise FeedbackError(
            'The feedback service could not be reached. Check the internet '
            'connection. Your text is still in the form.') from exc
    except OSError as exc:
        raise FeedbackError(
            'The feedback report could not be sent. Your text is still in '
            'the form.') \
            from exc
    if len(raw) > MAX_RESPONSE_BYTES:
        raise FeedbackError('The feedback service returned an invalid response.')
    try:
        result = json.loads(raw.decode('utf-8'))
        issue_number = int(result['issue_number'])
        issue_url = str(result['issue_url'])
    except (UnicodeDecodeError, json.JSONDecodeError, KeyError, TypeError,
            ValueError) as exc:
        raise FeedbackError(
            'The feedback service returned an invalid response.') from exc
    expected_url = (
        'https://github.com/RepSage/QCS_SAGE/issues/%d' % issue_number)
    if issue_number < 1 or issue_url != expected_url:
        raise FeedbackError('The feedback service returned an invalid response.')
    return {'issue_number': issue_number, 'issue_url': issue_url}
