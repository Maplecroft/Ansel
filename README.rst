Ansel: URL to PNG as a service
==============================

Ansel is a simple Flask-based service provider for exporting arbitrary
web content as a downloadable image or pdf.  Currently Ansel wraps
Ghost.py to provide URL snapshotting based on GET parameters and 
an svg export service based on Apache Batik.

See ``app.py`` for information on allowed parameters.
