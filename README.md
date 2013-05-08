The Open Source Report Card
===========================

This is my submission to the
[GitHub data challenge](https://github.com/blog/1450-the-github-data-challenge-ii).
Take a look at the [live demo](http://osrc.dfm.io) for a description of the project
and a view of what the results look like.

Running the analysis yourself
-----------------------------

To run the analysis, you'll need [Redis](http://redis.io) and a running `redis-server`.
You'll also need [FLANN](http://www.cs.ubc.ca/~mariusm/index.php/FLANN/FLANN) including
the Python bindings installed on your Python path. Then, install the other requirements
using:

```
pip install -r requirements.txt
```

Download all the data by running:

```
python fetch.py
```

And then analyse the data by running:

```
python process.py data/*.json.gz
```

This will accumulate stats in the redis database.

Finally, you can build the K-nearest neighbors index by running:

```
python ghdata/build_index.py
```

The web app is a [Flask](http://flask.pocoo.org/) app that is defined in `ghdata/__init__.py`.

License & Credits
-----------------

The Open Source Report Card was created by [Dan Foreman-Mackey](http://dan.iel.fm) and it is 
made available under the [MIT License](https://github.com/dfm/osrc/blob/master/LICENSE).
