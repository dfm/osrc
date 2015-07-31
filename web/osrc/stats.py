# -*- coding: utf-8 -*-

__all__ = ["user_stats", "repo_stats"]

import flask
from sqlalchemy import func, desc
from collections import defaultdict

from . import github
from .models import db, Event, Repo, User


def user_stats(username):
    user = github.get_user(username)
    if not user.active:
        return flask.abort(404)

    # Get the repo stats.
    repo_counts = db.session.query(Repo, func.count()) \
        .select_from(Event) \
        .filter(Event.user_id == user.id) \
        .join(Repo) \
        .group_by(Repo.id) \
        .order_by(desc(func.count())) \
        .all()
    langs = defaultdict(int)
    for r, c in repo_counts:
        if r.language is None:
            continue
        langs[r.language.name] += c

    # Get the week histogram.
    week_hist = defaultdict(lambda: list([0 for _ in range(7)]))
    for _, k, t, v in db.session.query(
        Event.user_id, Event.day, Event.event_type, func.count(),
    ).filter_by(user_id=user.id).group_by(
            Event.user_id, Event.event_type, Event.day):
        week_hist[t][k] = v

    # Get the data histogram.
    day_hist = defaultdict(lambda: list([0 for _ in range(24)]))
    for _, k, t, v in db.session.query(
        Event.user_id, Event.hour, Event.event_type, func.count(),
    ).filter_by(user_id=user.id).group_by(
            Event.user_id, Event.event_type, Event.hour).all():
        day_hist[t][k] = v

    # Build the results dictionary.
    return dict(
        user.basic_dict(),
        week=dict(week_hist),
        day=dict(day_hist),
        languages=dict(langs),
        repos=[{"name": r.fullname, "count": c} for r, c in repo_counts[:5]],
    )


def repo_stats(username, reponame):
    repo = github.get_repo("{0}/{1}".format(username, reponame))
    if not repo.active or not repo.owner.active:
        return flask.abort(404)

    # Get the user stats.
    user_counts = db.session.query(User, func.count()) \
        .select_from(Event) \
        .filter(Event.repo_id == repo.id) \
        .join(User) \
        .group_by(User.id) \
        .order_by(desc(func.count())) \
        .limit(5) \
        .all()

    # Get the week histogram.
    week_hist = defaultdict(lambda: list([0 for _ in range(7)]))
    for _, k, t, v in db.session.query(
        Event.repo_id, Event.day, Event.event_type, func.count(),
    ).filter_by(repo_id=repo.id).group_by(
            Event.repo_id, Event.event_type, Event.day):
        week_hist[t][k] = v

    # Get the data histogram.
    day_hist = defaultdict(lambda: list([0 for _ in range(24)]))
    for _, k, t, v in db.session.query(
        Event.repo_id, Event.hour, Event.event_type, func.count(),
    ).filter_by(repo_id=repo.id).group_by(
            Event.repo_id, Event.event_type, Event.hour).all():
        day_hist[t][k] = v

    # Build the results dictionary.
    return dict(
        repo.basic_dict(),
        owner=None if repo.owner is None else repo.owner.basic_dict(),
        week=dict(week_hist),
        day=dict(day_hist),
        contributors=[{"login": u.login, "name": u.name, "count": c}
                      for u, c in user_counts],
    )
