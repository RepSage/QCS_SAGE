"""Update check against the project's GitHub releases, with one-click install.

Lives behind QCS_QtApp (the shipped GUI shell): headless and batch paths never import
this module, so no corpus run ever touches the network. The startup check runs
in a background thread and FAILS SILENTLY on any network problem - a field
notebook is offline most of its life, and an update notice is exactly the thing
that must never block or crash qualification work.

Flow: GET releases/latest (anonymous - the repository is public), compare the
tag with the running QCS_VERSION, and when newer offer to download the
QCS_Setup_*.exe asset and run it. The installer (Inno Setup, same AppId)
upgrades in place; the app exits as the installer starts.
"""
import json
import os
import re
import ssl
import subprocess
import tempfile
import threading
import urllib.request

RELEASES_API = 'https://api.github.com/repos/RepSage/QCS_SAGE/releases/latest'
RELEASES_PAGE = 'https://github.com/RepSage/QCS_SAGE/releases/latest'
# 15 s, not 6: a cold TLS handshake over a slow field link can eat several
# seconds before the first byte, and a too-short timeout is indistinguishable
# from "no internet" to the user.
TIMEOUT_S = 15
# GitHub's API rejects requests without a User-Agent
_HEADERS = {'User-Agent': 'QCS-SAGE-update-check',
            'Accept': 'application/vnd.github+json'}

_TAG = re.compile(r'^v(\d+)\.(\d+)(?:\.(\d+))?$')


def ssl_context():
    """The certificates the app CARRIES, not the ones the machine happens to
    have (v11.2.2).

    On Windows, Python validates against the certificates already installed in
    the system store - it cannot fetch a missing root on demand the way the
    browser and PowerShell do. api.github.com currently chains to 'Sectigo
    Public Server Authentication Root E46', a recent root: a notebook that is
    rarely online can simply not have it, and then the update check fails on a
    machine whose internet works perfectly - which is exactly what happened on
    the field notebook. Shipping the CA bundle removes the dependency.

    Falls back to the system context when certifi is absent (running from
    source without it), so nothing breaks - it just goes back to relying on
    the machine.
    """
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        return ssl.create_default_context()


def describe_error(exc):
    """A one-line, human explanation of a failed check. The generic 'could not
    be reached' told the user nothing and told the maintainer less; these name
    the cause and, where there is one, the fix."""
    import socket
    import urllib.error
    if isinstance(exc, ssl.SSLCertVerificationError):
        return ('the security certificate could not be verified - this machine '
                'is missing a recent root certificate. Installing the pending '
                'Windows updates usually fixes it.')
    if isinstance(exc, urllib.error.HTTPError):
        return 'GitHub answered HTTP %s (%s).' % (exc.code, exc.reason)
    if isinstance(exc, socket.timeout) or isinstance(exc, TimeoutError):
        return 'the connection timed out after %d s.' % TIMEOUT_S
    if isinstance(exc, urllib.error.URLError):
        reason = getattr(exc, 'reason', exc)
        if isinstance(reason, ssl.SSLCertVerificationError):
            return ('the security certificate could not be verified - this '
                    'machine is missing a recent root certificate. Installing '
                    'the pending Windows updates usually fixes it.')
        if isinstance(reason, socket.gaierror):
            return 'the address api.github.com could not be resolved (no DNS).'
        return 'the connection failed (%s).' % reason
    return '%s: %s' % (type(exc).__name__, exc)


def parse_tag(tag):
    """'v11.1' -> (11, 1, 0); 'v3.2.1' -> (3, 2, 1); None when not a version
    tag (a malformed remote tag must never crash the checker)."""
    m = _TAG.match(str(tag).strip())
    if not m:
        return None
    return (int(m.group(1)), int(m.group(2)), int(m.group(3) or 0))


def is_newer(remote_tag, current_tag):
    """True when remote_tag is a strictly newer version than current_tag."""
    r, c = parse_tag(remote_tag), parse_tag(current_tag)
    if r is None or c is None:
        return False
    return r > c


def fetch_latest():
    """The latest release as {'tag', 'setup_url', 'setup_name', 'size_mb'};
    None when the release carries no usable version tag. 'setup_url' is None
    when it has no QCS_Setup_*.exe asset (then the browser fallback is used).

    RAISES on any network/TLS/HTTP failure (v11.2.2). It used to swallow every
    exception and return None, which left both the user and the maintainer with
    'could not be reached' and no way to tell DNS from a proxy from an expired
    certificate. The silent-on-startup policy now lives at the CALL SITE, where
    it can be chosen per caller, instead of being welded into the fetch.
    """
    req = urllib.request.Request(RELEASES_API, headers=_HEADERS)
    with urllib.request.urlopen(req, timeout=TIMEOUT_S, context=ssl_context()) as resp:
        info = json.load(resp)
    tag = info.get('tag_name')
    if not parse_tag(tag):
        return None
    out = {'tag': tag, 'setup_url': None, 'setup_name': None, 'size_mb': None}
    for asset in info.get('assets') or []:
        name = str(asset.get('name') or '')
        if name.startswith('QCS_Setup_') and name.lower().endswith('.exe'):
            out['setup_url'] = asset.get('browser_download_url')
            out['setup_name'] = name
            out['size_mb'] = round((asset.get('size') or 0) / 1e6, 1)
            break
    return out


def check_in_background(current_version, on_newer):
    """Startup path: queries the API in a daemon thread and, ONLY when a newer
    release exists, calls on_newer(latest_dict) - the caller marshals it onto
    the Tk main thread. Silent in EVERY other outcome, failures included: the
    startup check must never interrupt work on an offline field notebook. The
    reason is still printed to the Execution log, so a puzzled user has
    something to read without being interrupted."""
    def _worker():
        try:
            latest = fetch_latest()
        except Exception as exc:
            print('Info: update check skipped - %s' % describe_error(exc))
            return
        if latest and is_newer(latest['tag'], current_version):
            on_newer(latest)
    threading.Thread(target=_worker, daemon=True).start()


def install_log_path():
    """Where the silent installer writes its log. Fixed name in the temp
    folder: the next update overwrites it, and a support request only has to
    ask for one file."""
    return os.path.join(tempfile.gettempdir(), 'QCS_update_install.log')

def download_and_run(latest, parent):
    """Downloads the setup asset with a small progress window, launches it
    silently and asks the app to close. Returns True when the installer was
    started (the caller should then destroy the root window).

    The installer runs with /SILENT: same-mode upgrades need no clicks, and the
    .iss relaunches the app when the silent install finishes. An install made
    for all users (Program Files) triggers the normal UAC prompt first.
    """
    from tkinter import Toplevel, messagebox, ttk
    if not latest.get('setup_url'):
        # release exists but carries no installer asset: hand over to the browser
        import webbrowser
        webbrowser.open(RELEASES_PAGE)
        return False

    dest = os.path.join(tempfile.gettempdir(), latest['setup_name'])
    win = Toplevel(parent)
    win.title('Downloading %s' % latest['tag'])
    win.resizable(False, False)
    win.transient(parent)
    ttk.Label(win, text='Downloading %s (%.0f MB)...'
              % (latest['setup_name'], latest['size_mb'] or 0)).pack(padx=16, pady=(14, 6))
    bar = ttk.Progressbar(win, length=320, mode='determinate', maximum=100)
    bar.pack(padx=16, pady=(0, 14))
    win.update_idletasks()

    def _hook(blocks, block_size, total):
        if total > 0:
            bar['value'] = min(100.0, 100.0 * blocks * block_size / total)
            win.update()

    try:
        req = urllib.request.Request(latest['setup_url'], headers=_HEADERS)
        with urllib.request.urlopen(req, timeout=30, context=ssl_context()) as resp, \
                open(dest, 'wb') as f:
            total = int(resp.headers.get('Content-Length') or 0)
            got = 0
            while True:
                chunk = resp.read(1 << 16)
                if not chunk:
                    break
                f.write(chunk)
                got += len(chunk)
                _hook(1, got, total)
        if total and got != total:
            raise OSError('incomplete download: %d of %d bytes' % (got, total))
    except Exception as exc:
        win.destroy()
        messagebox.showwarning(
            'Update download failed',
            'The installer could not be downloaded: %s\n\nThe release page '
            'will open in the browser instead.' % describe_error(exc))
        import webbrowser
        webbrowser.open(RELEASES_PAGE)
        return False

    win.destroy()
    # The wizard runs VISIBLY (it used to be /SILENT). A silent install has no
    # finish page, so the only way back into the app was the [Run] entry gated
    # on WizardSilent - and that relaunch never happened on the owner's
    # machine, twice in a row, with nothing to show why. The wizard ends on a
    # finish page carrying 'Launch QCS after installation', ticked by default:
    # the reopening becomes something the operator can see and control
    # (owner, 2026-08-19). /LOG keeps the evidence either way.
    subprocess.Popen([dest, '/NORESTART', '/LOG=%s' % install_log_path()])
    return True


def offer_update(latest, root):
    """The dialog shown when a newer release is found. On accept, starts the
    download/install and closes the app."""
    from tkinter import messagebox
    from QCS_DataHandler import QCS_VERSION
    size = (' (~%.0f MB)' % latest['size_mb']) if latest.get('size_mb') else ''
    if not messagebox.askyesno(
            'Update available',
            'QCS %s is available - you are running %s.\n\n'
            'Download and install it now%s? The program closes and the '
            'installer opens; keep "Launch QCS after installation" ticked on '
            'its last page to come back updated. Your settings and '
            'preferences are kept.'
            % (latest['tag'], QCS_VERSION, size)):
        return
    if download_and_run(latest, root):
        root.destroy()
