#!/usr/bin/env python3

# wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | sudo apt-key add -
# sudo sh -c 'echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list'
# apt update; apt install google-chrome-beta

import re
import os
import sys
import json

from datetime import datetime
import time

from subprocess import run, PIPE, DEVNULL


### SETTINGS

INDEX_TEMPLATE = 'index_template.html'

FETCH_WGET = True
FETCH_PDF = True
FETCH_SCREENSHOT = True
RESOLUTION = '1440,900'          # screenshot resolution
FETCH_FAVICON = True
SUBMIT_ARCHIVE_DOT_ORG = True

CHROME_BINARY = 'google-chrome'  # change to chromium browser if using chromium
WGET_BINARY = 'wget'


def check_dependencies():
    print('[*] Checking Dependencies:')
    if FETCH_PDF or FETCH_SCREENSHOT:
        if run(['which', CHROME_BINARY]).returncode:
            print('[X] Missing dependency: {}'.format(CHROME_BINARY))
            print('    See https://github.com/pirate/pocket-archive-stream for help.')
            raise SystemExit(1)

        # parse chrome --version e.g. Google Chrome 61.0.3114.0 canary / Chromium 59.0.3029.110 built on Ubuntu, running on Ubuntu 16.04
        result = run([CHROME_BINARY, '--version'], stdout=PIPE)
        version = result.stdout.decode('utf-8').replace('Google Chrome ', '').replace('Chromium ', '').split(' ', 1)[0].split('.', 1)[0]  # TODO: regex might be better
        if int(version) < 59:
            print('[X] Chrome version must be 59 or greater for headless PDF and screenshot saving')
            print('    See https://github.com/pirate/pocket-archive-stream for help.')
            raise SystemExit(1)

    if FETCH_WGET:
        if run(['which', 'wget']).returncode:
            print('[X] Missing dependency: wget')
            print('    See https://github.com/pirate/pocket-archive-stream for help.')
            raise SystemExit(1)

    if FETCH_FAVICON or SUBMIT_ARCHIVE_DOT_ORG:
        if run(['which', 'curl']).returncode:
            print('[X] Missing dependency: curl')
            print('    See https://github.com/pirate/pocket-archive-stream for help.')
            raise SystemExit(1)


### PARSING READER LIST EXPORTS

def get_link_type(link):
    if link['base_url'].endswith('.pdf'):
        return 'PDF'
    elif link['base_url'].rsplit('.', 1) in ('pdf', 'png', 'jpg', 'jpeg', 'svg', 'bmp', 'gif', 'tiff', 'webp'):
        return 'image'
    elif 'wikipedia.org' in link['domain']:
        return 'wiki'
    elif 'youtube.com' in link['domain']:
        return 'youtube'
    return None

def parse_pocket_export(html):
    pattern = re.compile("^\\s*<li><a href=\"(.+)\" time_added=\"(\\d+)\" tags=\"(.*)\">(.+)</a></li>", re.UNICODE)   # see sample input in ./example_ril_export.html
    for line in html:
        match = pattern.search(line)
        if match:
            fixed_url = match.group(1).replace('http://www.readability.com/read?url=', '')           # remove old readability prefixes to get original url
            without_scheme = fixed_url.replace('http://', '').replace('https://', '')
            info = {
                'url': fixed_url,
                'domain': without_scheme.split('/')[0],    # without pathname
                'base_url': without_scheme.split('?')[0],  # without query args
                'time': datetime.fromtimestamp(int(match.group(2))).strftime('%Y-%m-%d %H:%M'),
                'timestamp': match.group(2),
                'tags': match.group(3),
                'title': match.group(4).replace(' — Readability', '').replace('http://www.readability.com/read?url=', '') or without_scheme,
            }
            info['type'] = get_link_type(info)
            yield info

def parse_pinboard_export(html):
    json_content = json.load(html)
    for line in json_content:
        if line:
            erg = line
            info = {
                'url': erg['href'],
                'domain': erg['href'].replace('http://', '').replace('https://', '').split('/')[0],
                'base_url': erg['href'].replace('https://', '').replace('http://', '').split('?')[0],
                'time': datetime.fromtimestamp(time.mktime(time.strptime(erg['time'].split(',')[0],'%Y-%m-%dT%H:%M:%SZ'))),
                'timestamp': time.mktime(time.strptime(erg['time'].split(',')[0],'%Y-%m-%dT%H:%M:%SZ')),
                'tags': erg['tags'],
                'title': erg['description'].replace(' — Readability', ''),
            }
            info['type'] = get_link_type(info)
            yield info


### ACHIVING FUNCTIONS

def fetch_wget(out_dir, link, overwrite=False):
    # download full site
    if not os.path.exists('{}/{}'.format(out_dir, link, overwrite=link['domain'])) or overwrite:
        print('    - Downloading Full Site')
        CMD = [
            *'wget --no-clobber --page-requisites --adjust-extension --convert-links --no-parent'.split(' '),
            link['url'],
        ]
        try:
            run(CMD, stdout=DEVNULL, stderr=DEVNULL, cwd=out_dir, timeout=20)  # dom.html
        except Exception as e:
            print('      Exception: {}'.format(e.__class__.__name__))
    else:
        print('    √ Skipping site download')

def fetch_pdf(out_dir, link, overwrite=False):
    # download PDF
    if (not os.path.exists('{}/output.pdf'.format(out_dir)) or overwrite) and not link['base_url'].endswith('.pdf'):
        print('    - Printing PDF')
        chrome_args = '--headless --disable-gpu --print-to-pdf'.split(' ')
        try:
            run([CHROME_BINARY, *chrome_args, link['url']], stdout=DEVNULL, stderr=DEVNULL, cwd=out_dir, timeout=20)  # output.pdf
        except Exception as e:
            print('      Exception: {}'.format(e.__class__.__name__))
    else:
        print('    √ Skipping PDF print')

def fetch_screenshot(out_dir, link, overwrite=False):
    # take screenshot
    if (not os.path.exists('{}/screenshot.png'.format(out_dir)) or overwrite) and not link['base_url'].endswith('.pdf'):
        print('    - Snapping Screenshot')
        chrome_args = '--headless --disable-gpu --screenshot'.split(' ')
        try:
            run([CHROME_BINARY, *chrome_args, '--window-size={}'.format(RESOLUTION), link['url']], stdout=DEVNULL, stderr=DEVNULL, cwd=out_dir, timeout=20)  # sreenshot.png
        except Exception as e:
            print('      Exception: {}'.format(e.__class__.__name__))
    else:
        print('    √ Skipping screenshot')

def archive_dot_org(out_dir, link, overwrite=False):
    # submit to archive.org
    if (not os.path.exists('{}/archive.org.txt'.format(out_dir)) or overwrite):
        print('    - Submitting to archive.org')
        submit_url = 'https://web.archive.org/save/{}'.format(link['base_url'])

        success = False
        try:
            result = run(['curl', '-I', submit_url], stdout=PIPE, stderr=DEVNULL, cwd=out_dir, timeout=20)  # archive.org
            headers = result.stdout.splitlines()
            content_location = [h for h in headers if b'Content-Location: ' in h]
            if content_location:
                archive_path = content_location[0].split(b'Content-Location: ', 1)[-1].decode('utf-8')
                saved_url = 'https://web.archive.org{}'.format(archive_path)
                success = True
            else:
                raise Exception('Failed to find Content-Location URL in Archive.org response headers.')
        except Exception as e:
            print('      Exception: {}'.format(e.__class__.__name__))

        if success:
            with open('{}/archive.org.txt'.format(out_dir), 'w') as f:
                f.write(saved_url)

    else:
        print('    √ Skipping archive.org')

def fetch_favicon(out_dir, link, overwrite=False):
    # download favicon
    if not os.path.exists('{}/favicon.ico'.format(out_dir)) or overwrite:
        print('    - Fetching Favicon')
        CMD = 'curl https://www.google.com/s2/favicons?domain={domain}'.format(**link).split(' ')
        fout = open('{}/favicon.ico'.format(out_dir), 'w')
        try:
            run([*CMD], stdout=fout, stderr=DEVNULL, cwd=out_dir, timeout=20)  # dom.html
        except Exception as e:
            print('      Exception: {}'.format(e.__class__.__name__))
        fout.close()
    else:
        print('    √ Skipping favicon')


### ORCHESTRATION

def dump_index(links, service):
    with open(INDEX_TEMPLATE, 'r') as f:
        index_html = f.read()

    link_html = """\
    <tr>
        <td>{time}</td>
        <td><a href="archive/{timestamp}/{base_url}" style="font-size:1.4em;text-decoration:none;color:black;" title="{title}">
            <img src="archive/{timestamp}/favicon.ico">
            {title} <small style="background-color: #eee;border-radius:4px; float:right">{tags}</small>
        </td>
        <td style="text-align:center"><a href="archive/{timestamp}/" title="Files">📂</a></td>
        <td style="text-align:center"><a href="{pdf_link}" title="PDF">📄</a></td>
        <td style="text-align:center"><a href="{screenshot_link}" title="Screenshot">🖼</a></td>
        <td style="text-align:center"><a href="https://web.archive.org/web/{base_url}" title="Archive.org">🏛</a></td>
        <td>🔗 <img src="https://www.google.com/s2/favicons?domain={domain}" height="16px"> <a href="{url}">{url}</a></td>
    </tr>"""

    def get_template_vars(link):
        # since we dont screenshot or PDF links that are images or PDFs, change those links to point to the wget'ed file
        link_info = {**link}

        if link['type']:
            link_info.update({'title': '{title} ({type})'.format(**link)})

        if link['type'] in ('PDF', 'image'):
            link_info.update({
                'pdf_link': 'archive/{timestamp}/{base_url}'.format(**link),
                'screenshot_link': 'archive/{timestamp}/{base_url}'.format(**link),
            })
        else:
            link_info.update({
                'pdf_link': 'archive/{timestamp}/output.pdf'.format(**link),
                'screenshot_link': 'archive/{timestamp}/screenshot.png'.format(**link)
            })
        return link_info

    with open(''.join((service, '/index.html')), 'w') as f:
        article_rows = '\n'.join(
            link_html.format(**get_template_vars(link)) for link in links
        )
        f.write(index_html.format(datetime.now().strftime('%Y-%m-%d %H:%M'), article_rows))

def dump_website(link, service, overwrite=False):
    """download the DOM, PDF, and a screenshot into a folder named after the link's timestamp"""

    print('[+] [{time}] Archiving "{title}": {base_url}'.format(**link))

    out_dir = ''.join((service, '/archive/{timestamp}')).format(**link)
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)

    if link['type']:
        print('    i Type: {}'.format(link['type']))

    if FETCH_WGET:
        fetch_wget(out_dir, link, overwrite=overwrite)

    if FETCH_PDF:
        fetch_pdf(out_dir, link, overwrite=overwrite)

    if FETCH_SCREENSHOT:
        fetch_screenshot(out_dir, link, overwrite=overwrite)

    if SUBMIT_ARCHIVE_DOT_ORG:
        archive_dot_org(out_dir, link, overwrite=overwrite)

    if FETCH_FAVICON:
        fetch_favicon(out_dir, link, overwrite=overwrite)

def create_archive(export_file, service, resume=None):
    print('[+] [{}] Starting {} archive from {}'.format(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), service, export_file))

    if not os.path.exists(service):
        os.makedirs(service)

    if not os.path.exists(''.join((service, '/archive'))):
        os.makedirs(''.join((service, '/archive')))

    with open(export_file, 'r', encoding='utf-8') as f:
        if service == "pocket":
            links = parse_pocket_export(f)
        elif service == "pinboard":
            links = parse_pinboard_export(f)
        links = list(reversed(sorted(links, key=lambda l: l['timestamp'])))  # most recent first
        if resume:
            links = [link for link in links if link['timestamp'] >= resume]

    if not links:
        if service == 'pocket':
            print('[X] No links found in {}, is it a getpocket.com/export export?'.format(export_file))
        elif service == 'pinboard':
            print('[X] No links found in {}, is it a pinboard.in/export/format:json/ export?'.format(export_file))
        raise SystemExit(1)

    dump_index(links, service)

    run(['chmod', '-R', '755', service], timeout=1)

    print('[*] [{}] Created archive index.'.format(datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

    check_dependencies()

    for link in links:
        dump_website(link, service)

    print('[√] [{}] Archive complete.'.format(datetime.now()))



if __name__ == '__main__':
    argc = len(sys.argv)
    export_file = sys.argv[1] if argc > 1 else "ril_export.html"        # path to export file
    export_type = sys.argv[2] if argc > 2 else "pocket"                 # select export_type for file format select
    resume_from = sys.argv[3] if argc > 3 else None                     # timestamp to resume dowloading from

    create_archive(export_file, export_type, resume=resume_from)