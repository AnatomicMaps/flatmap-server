Tools
=====

The ``./tools`` directory contains a number of Python scripts to assist with managing
deployed flatmaps in a server environment. Some of these scripts are historical, either
having their functionality replaced by a web application or being one-off programs
to resolve particular issues; however both ``tools/archiver.py`` and ``tools/promote.py``
are intended to be used in a production environment.

Flatmap archiving
-----------------

The ``archiver.py`` tool archives flatmaps by moving them from a flatmap server's
**flatmap** directory to an **archive** directory, which could be then removed to
free disk space. The utility though will not archive flatmaps on a **PRODUCTION**
server as these maps maps are intended to persist after publication.

.. image:: ./_static/archiver.svg


Flatmap promotion
-----------------

The ``promote.py`` tool copies flatmaps from a **STAGING** server to a destination
by copying the entire directory containing the flatmap. A summary of flatmaps
available for promotion is presented to the user for confirmation before actual
promotion.

.. image:: ./_static/promote.svg
