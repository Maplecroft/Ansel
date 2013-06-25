#!/usr/bin/env python
# -*- coding: iso-8859-15 -*-
import os
import tempfile
import subprocess
from ctypes import c_char_p, c_int
from multiprocessing import Pipe, Process, Value
from unidecode import unidecode

try:
    import local_settings as settings
except ImportError:
    import default_settings as settings

from flask import Flask, abort, make_response, request, Response

import utils

app = Flask(__name__)
DEBUG = True


@app.route('/snap')
def snap():
    """Given details via GET, return a PNG of the requested URL.

    Various GET parameters are accepted::

        `url`: the URL of the page to snapshot
        `name`: the name of the file to return to the client
        `selector`: the element to capture (default: body)
        `hides`: comma-delimited list of selectors to .hide()
        `loaded`: the element to wait for before capturing
        `cookie_name`: preserve the named cookie from the incoming request
        `width`: the width of the view port to capture
        `height`: the height of the view port to capture

    All parameters apart from `path` are optional and have sensible defaults.
    The `loaded` parameter is useful if the page is javascript-heavy (just
    insert an empty DOM element with the given selector after the page has
    settled).

    All parameters should be encoded before inserting into the query string.

    Example usage::

        var name = 'Some_Page';
        var url = someElt.getAttribute('href');
        var selector = '#some_div';
        var hides = ['.nav-thing', '.useless-button'];
        var loaded = '#page_ready';

        window.location = 'http://snap.example.com' +
            '?name=' + encodeURIComponent(name) +
            '&selector=' + encodeURIComponent(selector) +
            '&hides=' + encodeURIComponent(hides) +
            '&loaded=' + encodeURIComponent(loaded) +
            '&url=' + encodeURIComponent(url);

    """
    name = request.args.get('name', 'page')
    url = request.args.get('url')
    selector = request.args.get('selector', 'body')
    hides = request.args.get('hides', '')
    loaded = request.args.get('loaded', 'body')
    cookie_name = request.args.get('cookie_name')
    width = request.args.get('width', 1280)
    height = request.args.get('height', 1024)

    if not url:
        abort(400)

    name = unidecode(name).replace(' ', '_')

    try:
        url = Value(c_char_p, url)
        cookie_value = Value(c_char_p, request.cookies.get(cookie_name))
        cookie_name = Value(c_char_p, cookie_name)
        loaded = Value(c_char_p, loaded)
        selector = Value(c_char_p, selector)
        hides = Value(c_char_p, hides)
        width = Value(c_int, width)
        height = Value(c_int, height)

        parent_conn, child_conn = Pipe()
        proc = Process(
            target=utils.snap,
            args=(
                child_conn,
                url,
                cookie_name,
                cookie_value,
                width,
                height,
                loaded,
                hides,
                selector,
            ),
        )
        proc.start()
        proc.join()

        file_path = parent_conn.recv()

        with open(file_path) as f:
            response = make_response(f.read())
            response.headers['Content-Type'] = 'image/png'
            return response
    except:
        abort(500)


@app.route('/export_svg', methods=['POST'])
def export_svg():
    """Export POSTed SVG data as an image or pdf file.

    POST parameters are accepted::

        `svg`: the SVG graphic string
        `filename`: the name of the file to return to the client
        `bg`: the background colour of the export specified as r.g.b.a values
        `type`: the type of export: image/png, image/jpeg or application/pdf
        `dpi`: the resolution of the output in dots per inch (default 96)
    """

    export_type = request.form.get('type')
    svg = request.form.get('svg', "")
    dpi = request.form.get('dpi', "96")
    fname = request.form.get('filename', 'export')
    background = request.form.get('bg', '255.255.255.255')

    if "<!ENTITY" in svg:
        return Response("Execution is topped, the posted SVG could "
                            "contain code for a malicious attack", 500)

    # allow no other than predefined types
    type_option = ""
    ext = "svg"
    if export_type == 'image/png':
        type_option = '-m image/png'
        ext = 'png'
    elif export_type == 'image/jpeg':
        type_option = '-m image/jpeg'
        ext = 'jpg'
    elif export_type == 'application/pdf':
        type_option = '-m application/pdf'
        ext = 'pdf'
    elif export_type == 'image/svg+xml':
        ext = 'svg'
    else:
        return Response("Invalid export type", 500)

    width = ""
    if request.form.get('width') and request.form.get('width') != u"0":
        width = "-w %s" % request.form.get('width')

    # Write the SVG to file
    temp_svg = tempfile.NamedTemporaryFile(suffix=".svg")

    tsvg = open(temp_svg.name, 'w')
    tsvg.write(svg)
    tsvg.close()

    if ext == 'svg':
        # Use the original svg file.
        out_file = temp_svg
    else:
        # Create output path
        out_file = tempfile.NamedTemporaryFile(suffix="." + ext)

        cmd = settings.java_cmd_format.format(
            batik_path=settings.batik_path,
            type_option=type_option,
            out_filename=out_file.name,
            width_option=width,
            background=background,
            dpi=dpi,
            temp_svg_name=temp_svg.name,
        )

        proc = subprocess.Popen(cmd, shell=True)
        proc.wait()
        if proc.returncode != 0:
            return Response("Error: Export to %s failed" % export_type, 500)

    if not fname.endswith('.%s' % ext):
        fname = '%s.%s' % (fname, ext)

    response = Response(file(out_file.name), direct_passthrough=True)
    response.headers['Content-Length'] = os.path.getsize(out_file.name)
    response.headers['Content-Type'] = export_type
    response.headers['Content-Disposition'] = 'attachment; filename=%s' % fname
    return response


@app.errorhandler(400)
def bad_request(error):
    resp = make_response('bad request', 400)
    resp.headers['Content-Type'] = 'text/plain'
    return resp


@app.errorhandler(500)
def server_error(error):
    resp = make_response('server error', 500)
    resp.headers['Content-Type'] = 'text/plain'
    return resp


if __name__ == '__main__':
    app.debug = DEBUG
    app.run()
