The Open Source Report Card (v3)
================================

A work in progress... hopefully we'll have the OSRC back up soon!

Installation (docker-compose)
-----------------------------
If you have docker-compose installed just use:

> docker-compose up

to run on a different port than 5000 set environment variable WEB_RUNSERVER_PORT

> WEB_RUNSERVER_PORT=8000 docker-compose up

More details check docker-compose.yml and Dockerfile



Installation
------------
Set up the environment:

```
conda env create -f environment.yml
source activate osrc
```

Create the tables:

```
createdb osrc
python manage.py create
```

These tables can also be dropped using:

```
python manage.py drop
```


License & Credits
-----------------

The Open Source Report Card was created by [Dan
Foreman-Mackey](http://dan.iel.fm) and it is made available under the [MIT
License](https://github.com/dfm/osrc/blob/master/LICENSE).
