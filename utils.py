#!/usr/bin/env python 
# -*- coding: iso-8859-15 -*-
from tempfile import mkstemp
from ghost import Ghost

def snap(conn, url, cookie_name, cookie_value, width, height, loaded, hides, selector):
    """Handle all the work of taking the page snapshot.

    The first parameter is a connection object for a `multiprocessing.Pipe`
    that we use to send back the file name written to. The remaining parameters
    are `multiprocessing.Value`s.
    
    """
    ghost = None
    try:
        ghost = Ghost(viewport_size=(width.value, height.value))
        ghost.wait_timeout = 20

        headers = {}
        if cookie_name.value and cookie_value.value:
            headers = {
                'Cookie': str('%s=%s' % (cookie_name.value, cookie_value.value)),
            }

        ghost.open(url.value, headers=headers)

        if loaded.value:
            try:
                ghost.wait_for_selector('%s' % loaded.value)
            except:
                pass

        selectors = hides.value.split(',')
        if len(selectors):
            hide_js = r'''
                if (jQuery) {
                    $(document).ready(function() {
                        %s
                    });
                }
            ''' % '\n'.join([r"$('%s').hide();" % sel for sel in selectors])
            ghost.evaluate(hide_js)

        handle, file_path = mkstemp(prefix='map_image', suffix='.png')
        ghost.capture_to(file_path, selector=selector.value)

        conn.send(file_path)
    finally:
        del ghost
        conn.close()
