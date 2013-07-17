#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import (division, print_function, absolute_import,
                        unicode_literals)

__all__ = ["app"]

import os
import re
import json
import flask
import redis
import logging
import requests
import numpy as np

from ghdata.build_index import get_neighbors


app = flask.Flask(__name__)
app.config.from_object("ghdata.config")

ghapi_url = "https://api.github.com"
mqapi_url = "http://open.mapquestapi.com/geocoding/v1/address"
tzapi_url = "http://www.earthtools.org/timezone-1.1/{lat}/{lng}"
tz_re = re.compile(r"<offset>([\-0-9]+)</offset>")

fh = logging.FileHandler(app.config["LOG_FILENAME"])
fh.setLevel(logging.WARNING)
fh.setFormatter(logging.Formatter(
    "%(asctime)s %(levelname)s: %(message)s "
    "[in %(pathname)s:%(lineno)d]"
))
app.logger.addHandler(fh)

_basepath = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
week_means = json.load(open(os.path.join(_basepath, "week_means.json")))
mean_desc, means = zip(*(week_means.items()))
means = np.array(means)
week_reps = json.load(open(os.path.join(_basepath, "week_reps.json")))

evttypes = {
    "PushEvent": "{user} is {more} of a pusher",
    "CreateEvent": "{user} spends {more} of their time creating new "
                   "repositories and branches",
    "CommitCommentEvent": "{user} is far {more} likely to comment on your "
                          "commits",
    "FollowEvent": "{user} is {more} of a follower",
    "ForkEvent": "{user} is a {more} serious forker",
    "IssueCommentEvent": "{user} spends {more} of their time commenting on "
                         "issues",
    "PublicEvent": "{user} is {more} likely to open source a new project",
    "PullRequestEvent": "{user} submits pull requests {more} frequently",
}

evtactions = {
    "CreateEvent": "creating new repositories and branches",
    "CommitCommentEvent": "commenting on your commits",
    "FollowEvent": "following other users",
    "ForkEvent": "forking other people's code",
    "IssuesEvent": "creating issues",
    "IssueCommentEvent": "commenting on issues",
    "PublicEvent": "open sourcing new projects",
    "PullRequestEvent": "submitting pull requests",
}

evtverbs = {
    "CommitCommentEvent": "commit comments",
    "CreateEvent": "new repos or branches",
    "DeleteEvent": "deletion of branches",
    "DownloadEvent": "creation of downloads",
    "FollowEvent": "following",
    "ForkEvent": "forking",
    "ForkApplyEvent": "fork merges",
    "GistEvent": "gist creation",
    "GollumEvent": "wiki edits",
    "IssueCommentEvent": "issue comments",
    "IssuesEvent": "new issues",
    "MemberEvent": "new collaborations",
    "PublicEvent": "open-sourcing",
    "PullRequestEvent": "pull requests",
    "PullRequestReviewCommentEvent": "pull request comments",
    "PushEvent": "pushes",
    "TeamAddEvent": "teams",
    "WatchEvent": "watching"
}

languages = {
    "Python": "{user} is {more} of a Pythonista",
    "Ruby": "{user} is {more} of a Rubyist",
    "Go": "{user} is {more} of a Gopher",
    "Java": "{user} is {more} a Javavore",
    "C": "{user} is {more} a sysadmin",
    "FORTRAN": "{user} is way {more} old school",
    "JavaScript": "{user} is probably {more} of a Javascripter",
    "C++": "{user} spends {more} time working for the man",
    "R": "{user} is {more} of a useR",
}

language_users = {
    "Python": "Pythonista",
    "Ruby": "Rubyist",
    "Go": "Gopher",
    "Java": "Javavore",
    "C": "sysadmin",
    "FORTRAN": "old-school hacker",
    "JavaScript": "Javascripter",
    "C++": "corporate slave",
    "R": "useR",
}


@app.before_request
def before_request():
    flask.g.redis = redis.Redis()
    flask.g.ghauth = {"client_id": app.config["GITHUB_ID"],
                      "client_secret": app.config["GITHUB_SECRET"]}


@app.route("/")
def index():
    return flask.render_template("index.html")


@app.route("/about/rep/<cls>")
def rep(cls):
    # Get the name of a representative user for a class of weekly schedule.
    nm = week_reps.get(cls, [""])
    p = 1. / np.sqrt(np.arange(1, len(nm) + 1))
    return np.random.choice(nm, p=p / np.sum(p))


def get_tz(location):
    pars = {"location": location,
            "maxResults": 1,
            "thumbMaps": False}
    r = requests.get(mqapi_url, params=pars)
    if r.status_code == requests.codes.ok:
        resp = r.json().get("results", [])
        if len(resp):
            locs = resp[0].get("locations", [])
            if len(locs):
                latlng = locs[0].get("latLng", {})
                if "lat" in latlng and "lng" in latlng:
                    r = requests.get(tzapi_url.format(**latlng))
                    if r.status_code == requests.codes.ok:
                        matches = tz_re.findall(r.text)
                        if len(matches):
                            return int(matches[0])


@app.route("/<username>")
def user(username):
    ghuser = username.lower()

    # Get the name and gravatar from the cache if it exists.
    pipe = flask.g.redis.pipeline()
    pipe.get("gh:user:{0}:name".format(ghuser))
    pipe.get("gh:user:{0}:etag".format(ghuser))
    pipe.get("gh:user:{0}:gravatar".format(ghuser))
    name, etag, gravatar = pipe.execute()

    headers = {}
    if etag is not None:
        headers = {"If-None-Match": etag}

    r = requests.get(ghapi_url + "/users/" + username,
                     params=flask.g.ghauth, headers=headers)

    # If modified, update.
    if r.status_code != 304:
        if r.status_code != requests.codes.ok:
            logging.error("GitHub API failed: {0}".format(r.status_code))
            logging.error(r.text)
        else:
            user = r.json()
            name = user.get("name") or user.get("login") or username
            etag = r.headers["ETag"]
            gravatar = user.get("gravatar_id", "none")

            # Update the cache.
            pipe = flask.g.redis.pipeline()
            pipe.set("gh:user:{0}:name".format(ghuser), name)
            pipe.set("gh:user:{0}:etag".format(ghuser), etag)
            pipe.set("gh:user:{0}:gravatar".format(ghuser), gravatar)
            pipe.execute()

            # Check timezone.
            if not flask.g.redis.exists("gh:user:{0}:tz".format(ghuser)):
                location = user.get("location")
                if location:
                    flask.g.redis.set("gh:user:{0}:tz".format(ghuser),
                                      get_tz(location))

    if name is None:
        name = username
    if gravatar is None:
        gravatar = "none"

    name = name.decode("utf-8")

    return flask.render_template("report.html",
                                 gravatar=gravatar,
                                 name=name,
                                 firstname=name.split()[0],
                                 username=username)


def make_hist(data, size, offset=None):
    if offset is None:
        offset = 0
    result = [0] * size
    for k, v in data:
        val = float(v)
        i = int(k) + offset
        while (i < 0):
            i += size
        result[i % size] = val
    return result


@app.route("/<username>/stats")
def get_stats(username):
    ghuser = username.lower()
    firstname = flask.request.args.get("firstname", username)

    eventscores = flask.g.redis.zrevrangebyscore("gh:user:{0}:event"
                                                 .format(ghuser), "+inf", 5,
                                                 0, 10, withscores=True)
    events = [e[0] for e in eventscores]
    evtcounts = [int(e[1]) for e in eventscores]

    # Get the user histogram.
    pipe = flask.g.redis.pipeline()

    # Get the time zone.
    pipe.get("gh:user:{0}:tz".format(ghuser))

    # Get the total number of events.
    pipe.zscore("gh:user", ghuser)

    # Get full commit schedule.
    pipe.hgetall("gh:user:{0}:date".format(ghuser))

    # Get the daily schedule for each type of event.
    [pipe.hgetall("gh:user:{0}:event:{1}:day".format(ghuser, e))
     for e in events]

    # Get the hourly schedule for each type of event.
    [pipe.hgetall("gh:user:{0}:event:{1}:hour".format(ghuser, e))
     for e in events]

    # Get the distribution of languages contributed to.
    pipe.zrevrange("gh:user:{0}:lang".format(ghuser), 0, -1, withscores=True)

    # Get the vulgarity (and vulgar rank) of the user.
    pipe.zrevrange("gh:user:{0}:curse".format(ghuser), 0, -1, withscores=True)
    pipe.zcount("gh:curse:user", 4, "+inf")
    pipe.zrevrank("gh:curse:user", ghuser)

    # Get connected users.
    pipe.zrevrangebyscore("gh:user:{0}:connection".format(ghuser), "+inf", 5,
                          0, 5)

    # Fetch the data from the database.
    raw = pipe.execute()

    # Get the general stats.
    tz = int(raw[0]) if raw[0] is not None and raw[0] != "None" else None
    total = int(raw[1]) if raw[1] is not None else 0

    if total == 0:
        return json.dumps({"message":
                           "Couldn't find any stats for this user."}), 404

    # Get the schedule histograms.
    n, m = 3, len(events)
    week = zip(*[make_hist(d.iteritems(), 7)
                 for k, d in zip(events, raw[n:n + m])])
    offset = tz + 8 if tz is not None else 0
    day = zip(*[make_hist(d.iteritems(), 24, offset=offset)
                for k, d in zip(events, raw[n + m:n + 2 * m])])

    # If there's no weekly schedule, we don't have enough info.
    if not len(week):
        return json.dumps({"message":
                           "Couldn't find any stats for this user."}), 404

    # Get the language proportions.
    n = n + 2 * m
    langs = raw[n]
    curses = raw[n + 1]

    # Parse the vulgarity factor.
    vulgarity = None
    try:
        vulgarity = int(100 * float(raw[n + 3]) / float(raw[n + 2])) + 1
    except:
        pass

    # Get the connected users.
    connections = [c for c in raw[n + 4] if c.lower() != ghuser]

    # Get language rank.
    langrank = None
    langname = None
    if len(langs):
        lang = langs[0][0]
        langname = language_users.get(lang, "{0} expert".format(lang))

        # Made up number. How many contributions count as enough? 20? Sure.
        pipe.zcount("gh:lang:{0}:user".format(lang), 50, "+inf")
        pipe.zrevrank("gh:lang:{0}:user".format(lang), ghuser)
        ltot, lrank = pipe.execute()

        # This user is in the top N percent of users of language "lang".
        try:
            langrank = (lang, int(100 * float(lrank) / float(ltot)) + 1)
        except:
            pass

    # Get neighbors.
    neighbors = get_neighbors(ghuser)

    # Figure out the representative weekly schedule.
    hacker_type = "a pretty inconsistent hacker"
    if len(week):
        mu = np.sum(week, axis=1)
        mu /= np.sum(mu)
        hacker_type = mean_desc[np.argmin(np.sum(np.abs(means - mu[None, :]),
                                                 axis=1))]
    # Build a human readable summary.
    summary = "<p>"
    if langname:
        adj = np.random.choice(["a high caliber", "a heavy hitting",
                                "a serious", "an awesome",
                                "a top notch", "a trend setting",
                                "a champion", "an epic",
                                "a language-defining", "a leading"
                                "a prime", "a capital",
                                "an exceptional", "a distinguished",
                                "a premium", "a noteworthy"])

        summary += ("{0} is {2} <a href=\"#languages\">{1}</a>"
                    .format(firstname, langname, adj))
        if langrank and langrank[1] < 50:
            summary += (" (one of the top {0}% most active {1} users)"
                        .format(langrank[1], langrank[0]))

        if len(events):
            if events[0] in evtactions:
                summary += (" who <a href=\"#events\">spends a lot of time "
                            "{0}</a> between pushes").format(
                                evtactions[events[0]])
            elif events[0] == "PushEvent":
                summary += " who <a href=\"#events\">loves pushing code</a>"

        summary += ". "

    summary += "{0} is <a href=\"#week\">{1}</a>".format(firstname,
                                                         hacker_type)
    if len(day):
        best_hour = np.argmax(np.sum(day, axis=1))
        if 0 <= best_hour < 7:
            tod = "wee hours"
        elif 7 <= best_hour < 12:
            tod = "morning"
        elif 12 <= best_hour < 18:
            tod = "mid-afternoon"
        elif 18 <= best_hour < 21:
            tod = "evening"
        else:
            tod = "late evening"
        summary += " who seems to <a href=\"#day\">work best in the {0}</a>" \
                   .format(tod)
    summary += ". "

    if vulgarity:
        if vulgarity < 50:
            summary += ("I hate to say it but {0} does seem&mdash;as one of "
                        "the top {1}% most vulgar users on GitHub&mdash;to "
                        "be a tad foul-mouthed "
                        "(with a particular affinity "
                        "for filthy words like '{2}').").format(firstname,
                                                                vulgarity,
                                                                curses[0][0])
        elif vulgarity < 100:
            summary += ("I hate to say it but {0} is becoming&mdash;as one of "
                        "the top {1}% most vulgar users on GitHub&mdash;"
                        "a tad foul-mouthed "
                        "(with a particular affinity "
                        "for filthy words like '{2}').").format(firstname,
                                                                vulgarity,
                                                                curses[0][0])

    summary += "</p>"

    # Add similar and connected users to summary.
    if len(week) and (len(neighbors) or len(connections)):
        summary += "<p>"

        if len(neighbors):
            ind = np.random.randint(len(neighbors))
            summary += ("{0}'s behavior is quite similar to <a "
                        "href=\"{2}\">{1}</a>'s but <span "
                        "class=\"comparison\" data-url=\"{3}\"></span>. ") \
                .format(firstname, neighbors[ind],
                        flask.url_for(".user", username=neighbors[ind]),
                        flask.url_for(".compare", username=ghuser,
                                      other=neighbors[ind]))

            if len(neighbors) == 2:
                ind = (ind + 1) % 2
                summary += ("<a href=\"{1}\">{0}</a>'s activity stream also "
                            "shows remarkable similarities to {2}'s "
                            "behavior. ").format(neighbors[ind],
                                                 flask.url_for(".user",
                                                               username=
                                                               neighbors[ind]),
                                                 firstname)

            elif len(neighbors) > 2:
                summary += ("It would also be impossible to look at {0}'s "
                            "activity stream and not compare it to those "
                            "of ").format(firstname)

                cus = []
                for i in range(len(neighbors)):
                    if i != ind:
                        cus.append("<a href=\"{1}\">{0}</a>"
                                   .format(neighbors[i],
                                           flask.url_for(".user",
                                                         username=
                                                         neighbors[i])))

                summary += ", ".join(cus[:-1])
                summary += " and " + cus[-1] + ". "

        if len(connections):
            ind = 0
            summary += ("It seems&mdash;from their activity streams&mdash;"
                        "that {0} and <a href=\"{2}\">{1}</a> are probably "
                        "friends or at least virtual friends. With this in "
                        "mind, it's worth noting that <span "
                        "class=\"comparison\" data-url=\"{3}\"></span>. ") \
                .format(firstname, connections[ind],
                        flask.url_for(".user", username=connections[ind]),
                        flask.url_for(".compare", username=ghuser,
                                      other=connections[ind]))

            if len(connections) > 2:
                summary += ("There is also an obvious connection between "
                            "{0} and ").format(firstname)

                cus = []
                for i in range(len(connections)):
                    if i != ind:
                        cus.append("<a href=\"{1}\">{0}</a>"
                                   .format(connections[i],
                                           flask.url_for(".user",
                                                         username=
                                                         connections[i])))

                summary += ", ".join(cus[:-1])
                summary += " and " + cus[-1] + ". "

        summary += "</p>"

    # Summary text for schedule graphs.
    sctxt = ""
    if len(events):
        sctxt = ("<p>The two following graphs show {0}'s average weekly and "
                 "daily schedules. These charts give significant insight "
                 "into {0}'s character as a developer. ").format(firstname)

        if len(events) == 1:
            sctxt += "All of the events in {0}'s activity stream are {1}. " \
                .format(firstname, evtverbs.get(events[0]))

        else:
            sctxt += ("The colors in the charts indicate the fraction of "
                      "events that are ")
            for i, e in enumerate(events):
                if i == len(events) - 1:
                    sctxt += "and "
                sctxt += ("<span class=\"evttype\" data-ind=\"{1}\">{0}"
                          "</span>").format(evtverbs.get(e), i)
                if i < len(events) - 1:
                    sctxt += ", "
            sctxt += ". "

        sctxt += """</p>
<div class="hist-block">
    <div id="week" class="hist"></div>
    <div id="day" class="hist"></div>
</div>
<p>"""

        sctxt += ("Based on this average weekly schedule, we can "
                  "describe {0} as "
                  "<strong>{1}</strong>. ").format(firstname, hacker_type)

        if len(day):
            if best_hour == 0:
                tm = "midnight"
            elif best_hour == 12:
                tm = "noon"
            else:
                tm = "{0}{1}".format(best_hour % 12,
                                     "am" if best_hour < 12 else "pm")
            sctxt += ("Since {0}'s most active time is around {1}, I would "
                      "conclude that {0} works best in the "
                      "<strong>{2}</strong>. ").format(firstname, tm, tod)
            sctxt += ("It is important to note that an attempt has been made "
                      "to show the daily schedule in the correct time zone "
                      "but this procedure is imperfect at best. ")
        sctxt += "</p>"

        if len(events) > 1:
            sctxt += ("<p>The following chart shows number of events of "
                      "different types in {0}'s activity stream. In the "
                      "time frame included in this analysis, {0}'s event "
                      "stream included "
                      "a total of {1} events and they are all ") \
                .format(firstname, sum(evtcounts))

            for i, e in enumerate(events):
                if i == len(events) - 1:
                    sctxt += "or "
                sctxt += ("<span class=\"evttype\" data-ind=\"{1}\">{0}"
                          "</span>").format(evtverbs.get(e), i)
                if i < len(events) - 1:
                    sctxt += ", "
            sctxt += ". "

            sctxt += """</p><div class="hist-block">
    <div id="events"></div>
</div>"""

        if langs and len(langs) > 1:
            sctxt += ("<p>{0} has contributed to repositories in {1} "
                      "different languages. ").format(firstname, len(langs))
            sctxt += ("In particular, {0} is a serious <strong>{1}</strong> "
                      "expert").format(firstname, langs[0][0])
            ls = [float(l[1]) for l in langs]
            if (ls[0] - ls[1]) / sum(ls) < 0.25:
                sctxt += (" with a surprisingly broad knowledge of {0} "
                          "as well").format(langs[1][0])
            sctxt += ". "
            sctxt += ("The following chart shows the number of contributions "
                      "made by {0} to repositories where the main "
                      "language is listed as ").format(firstname)
            for i, l in enumerate(langs):
                if i == len(langs) - 1:
                    sctxt += "or "
                sctxt += ("<span class=\"evttype\" data-ind=\"{1}\">{0}"
                          "</span>").format(l[0], i)
                if i < len(langs) - 1:
                    sctxt += ", "
            sctxt += "."
            sctxt += """</p><div class="hist-block">
    <div id="languages"></div>
</div>"""

        if langs and len(langs) == 1:
            sctxt += ("<p>{0} seems to speak only one programming language: "
                      "<strong>{1}</strong>. Maybe it's about time for {0} to "
                      "branch out a bit.</p>").format(firstname, langs[0][0])

    # Format the results.
    results = {"summary": summary}
    results["events"] = [" ".join(re.findall("([A-Z][a-z]+)", e))
                         for e in events]
    results["event_counts"] = evtcounts
    results["tz"] = tz
    results["total"] = total
    results["week"] = week
    results["hacker_type"] = hacker_type
    results["day"] = day
    results["schedule_text"] = sctxt
    # results["activity"] = raw[2].items()
    results["languages"] = langs
    results["lang_user"] = langname
    results["language_rank"] = langrank
    results["curses"] = curses
    results["vulgarity"] = vulgarity
    results["similar_users"] = neighbors
    results["connected_users"] = connections

    return json.dumps(results)


@app.route("/<username>/compare/<other>")
def compare(username, other):
    """
    Return a human-readable distinction between 2 GitHub users.

    """
    user1, user2 = username.lower(), other.lower()

    pipe = flask.g.redis.pipeline()

    pipe.zscore("gh:user", user1)
    pipe.zscore("gh:user", user2)

    pipe.zrevrange("gh:user:{0}:event".format(user1), 0, -1, withscores=True)
    pipe.zrevrange("gh:user:{0}:event".format(user2), 0, -1, withscores=True)

    pipe.zrevrange("gh:user:{0}:lang".format(user1), 0, -1, withscores=True)
    pipe.zrevrange("gh:user:{0}:lang".format(user2), 0, -1, withscores=True)

    pipe.zscore("gh:curse:user", user1)
    pipe.zscore("gh:curse:user", user2)

    pipe.hgetall("gh:user:{0}:day".format(user1))
    pipe.hgetall("gh:user:{0}:day".format(user2))

    raw = pipe.execute()

    total1 = float(raw[0]) if raw[0] is not None else 0
    total2 = float(raw[1]) if raw[1] is not None else 0

    if not total1:
        return json.dumps({"message":
                           "No stats for user '{0}'".format(username)}), 404

    if not total2:
        return "we don't have any statistics about {0}".format(other)

    # Compare the fractional event types.
    evts1 = dict(raw[2])
    evts2 = dict(raw[3])
    diffs = []
    for e, desc in evttypes.iteritems():
        if e in evts1 and e in evts2:
            d = float(evts2[e]) / total2 / float(evts1[e]) * total1
            if d != 1:
                more = "more" if d > 1 else "less"
                if d > 1:
                    d = 1.0 / d
                diffs.append((desc.format(more=more, user=user2), d * d))

    # Compare language usage.
    langs1 = dict(raw[4])
    langs2 = dict(raw[5])
    for l in set(langs1.keys()) | set(langs2.keys()):
        n = float(langs1.get(l, 0)) / total1
        d = float(langs2.get(l, 0)) / total2
        if n != d and d > 0:
            if n > 0:
                d = d / n
            else:
                d = 1.0 / d
            more = "more" if d > 1 else "less"
            if l in languages:
                desc = languages[l]
            else:
                desc = "{{user}} is {{more}} of a {0} aficionado".format(l)
            if d > 1:
                d = 1.0 / d
            diffs.append((desc.format(more=more, user=user2), d * d))

    # Number of languages.
    nl1, nl2 = len(raw[4]), len(raw[5])
    if nl1 and nl2:
        desc = "{user} speaks {more} languages"
        if nl1 > nl2:
            diffs.append((desc.format(user=user2, more="fewer"),
                          nl2 * nl2 / nl1 / nl1))
        else:
            diffs.append((desc.format(user=user2, more="more"),
                          nl1 * nl1 / nl2 / nl2))

    # Compare the vulgarity.
    nc1 = float(raw[6]) if raw[6] else 0
    nc2 = float(raw[7]) if raw[7] else 0
    if nc1 or nc2 and nc1 != nc2:
        if nc1 > nc2:
            diffs.append(("{0} is less foul mouthed".format(user2),
                          (nc2 * nc2 + 1) / (nc1 * nc1 + 1)))
        else:
            diffs.append(("{0} is more foul mouthed".format(user2),
                          (nc1 * nc1 + 1) / (nc2 * nc2 + 1)))

    # Compare the average weekly schedules.
    week1 = map(lambda v: int(v[1]), raw[8].iteritems())
    week2 = map(lambda v: int(v[1]), raw[9].iteritems())
    mu1, mu2 = sum(week1) / 7.0, sum(week2) / 7.0
    var1 = np.sqrt(sum(map(lambda v: (v - mu1) ** 2, week1)) / 7.0) / mu1
    var2 = np.sqrt(sum(map(lambda v: (v - mu2) ** 2, week2)) / 7.0) / mu2
    if var1 or var2 and var1 != var2:
        if var1 > var2:
            diffs.append(("{0} has a more consistent weekly schedule"
                          .format(user2), var2 / var1))
        else:
            diffs.append(("{0} has a less consistent weekly schedule"
                          .format(user2), var1 / var2))

    # Compute the relative probabilities of the comparisons and normalize.
    ps = map(lambda v: v[1], diffs)
    norm = sum(ps)

    # Return the full list?
    if flask.request.args.get("full") is not None:
        diffs = zip([d[0] for d in diffs], [p / norm for p in ps])
        diffs = sorted(diffs, key=lambda v: v[1], reverse=True)
        return json.dumps(diffs)

    # Choose a random description weighted by the probabilities.
    return np.random.choice([d[0] for d in diffs], p=[p / norm for p in ps])
