The Open Source Report Card (v2)
================================

New in version 2:

* real time stats (updated daily),
* server-side rendering,
* JSON endpoint to access all the data,
* repository recommendations based on a social graphof GitHub activity.

Running the analysis
--------------------

To run the analysis, you'll need [Redis](http://redis.io) and a running
`redis-server`. You'll also need
[FLANN](http://www.cs.ubc.ca/~mariusm/index.php/FLANN/FLANN) including
the Python bindings installed on your Python path. Then, install the other
requirements using:

```
pip install -r requirements.txt
```

Version 2 of the OSRC comes with a daemon `osrcd` designed to be run once a day to update the
stats. To initialize the database with the event stream starting at the beinning of 2013, run:

```
./osrcd --since 2013-01-01
```

After this finishes, all you need to do is rerun `osrcd` (using a cronjob or similar) once a
day (some time after 1am PST) to update the stats.

The web app is a [Flask](http://flask.pocoo.org/) app that is defined in `osrc/__init__.py`.

License & Credits
-----------------

The Open Source Report Card was created by [Dan Foreman-Mackey](http://dan.iel.fm) and it is
made available under the [MIT License](https://github.com/dfm/osrc/blob/master/LICENSE).
