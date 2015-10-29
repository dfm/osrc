The Open Source Report Card (v3)
================================

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

The Open Source Report Card was created by [Dan Foreman-Mackey](http://dan.iel.fm) and it is
made available under the [MIT License](https://github.com/dfm/osrc/blob/master/LICENSE).
