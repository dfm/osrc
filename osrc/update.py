# -*- coding: utf-8 -*-

import time
import json
import gzip
import traceback
from io import BytesIO
from multiprocessing import Pool
from collections import defaultdict
from datetime import date, timedelta

from .models import db
from .asyncdl import Downloader
from .process import parse_datetime


# The URL template for the GitHub Archive.
archive_url = ("http://data.githubarchive.org/"
               "{year}-{month:02d}-{day:02d}-{n}.json.gz")


class Parser(object):

    def __call__(self, args):
        name, fh = args
        try:
            return self.process(name, fh)
        except Exception as e:
            print(e)
            print(name)
            raise

    def process(self, name, fh):
        self.users = defaultdict(dict)
        self.repos = defaultdict(dict)

        c = db.engine.connect()
        c.connection.autocommit = False
        self.cursor = c.connection.cursor()

        # Start by creating the temporary tables that we'll use for these
        # events.
        self.cursor.execute("""
            create temporary table temp_gh_users(like gh_users)
                on commit drop;
            create temporary table temp_gh_repos(like gh_repos)
                on commit drop;
            create temporary table temp_gh_events(like gh_events)
                on commit drop;
        """)

        # Loop over events and fill the temporary tables.
        strt = time.time()
        count = 0
        with gzip.GzipFile(fileobj=BytesIO(fh)) as f:
            for line in f:
                strt = time.time()
                evt = json.loads(line.decode("utf-8"))
                try:
                    self._process_event(evt)
                except:
                    print("failed to process event:")
                    print(evt)
                    print("  exception:")
                    traceback.print_exc()
                    continue
                count += 1

        all_user_keys = set([])
        for user in self.users.values():
            keys = list(user.keys())
            all_user_keys |= set(keys)
            self.cursor.execute(
                """
                insert into temp_gh_users (
                    {0}
                ) values (
                    {1}
                )
                """
                .format(",".join(keys),
                        ",".join(map("%({0})s".format, keys))),
                user
            )

        all_repo_keys = set([])
        for repo in self.repos.values():
            keys = list(repo.keys())
            all_repo_keys |= set(keys)
            self.cursor.execute(
                """
                insert into temp_gh_repos (
                    {0}
                ) values (
                    {1}
                )
                """
                .format(",".join(keys),
                        ",".join(map("%({0})s".format, keys))),
                repo
            )

        # Copy the temporary tables.
        self.cursor.execute("""
            LOCK TABLE gh_users IN EXCLUSIVE MODE;

            UPDATE gh_users
            SET {0}
            FROM temp_gh_users
            where temp_gh_users.id = gh_users.id;

            INSERT INTO gh_users({1}, active)
            SELECT {2}, TRUE
            FROM temp_gh_users
            LEFT OUTER JOIN gh_users ON (gh_users.id = temp_gh_users.id)
            WHERE gh_users.id IS NULL;
        """.format(
            ", ".join(map("{0} = coalesce(temp_gh_users.{0}, gh_users.{0})"
                            .format,
                            all_user_keys)),
            ", ".join(all_user_keys),
            ", ".join(map("temp_gh_users.{0}".format, all_user_keys))
        ))

        self.cursor.execute("""
            LOCK TABLE gh_repos IN EXCLUSIVE MODE;

            UPDATE gh_repos
            SET {0}
            FROM temp_gh_repos
            where temp_gh_repos.id = gh_repos.id;

            INSERT INTO gh_repos({1}, active)
            SELECT {2}, TRUE
            FROM temp_gh_repos
            LEFT OUTER JOIN gh_repos ON (gh_repos.id = temp_gh_repos.id)
            WHERE gh_repos.id IS NULL;
        """.format(
            ", ".join(map("{0} = coalesce(temp_gh_repos.{0}, gh_repos.{0})"
                            .format,
                            all_repo_keys)),
            ", ".join(all_repo_keys),
            ", ".join(map("temp_gh_repos.{0}".format, all_repo_keys))
        ))

        all_event_keys = ["id", "event_type", "datetime", "day", "hour",
                          "user_id", "repo_id"]

        self.cursor.execute("""
            LOCK TABLE gh_events IN EXCLUSIVE MODE;

            UPDATE gh_events
            SET {0}
            FROM temp_gh_events
            where temp_gh_events.id = gh_events.id;

            INSERT INTO gh_events({1})
            SELECT {2}
            FROM temp_gh_events
            LEFT OUTER JOIN gh_events ON (gh_events.id = temp_gh_events.id)
            WHERE gh_events.id IS NULL;
        """.format(
            ", ".join(map("{0} = coalesce(temp_gh_events.{0}, gh_events.{0})"
                          .format,
                          all_event_keys)),
            ", ".join(all_event_keys),
            ", ".join(map("temp_gh_events.{0}".format, all_event_keys))
        ))

        self.cursor.execute("commit;")

        print("... processed {0} events in {1} seconds"
              .format(count, time.time() - strt))

    def _process_event(self, event):
        dt = parse_datetime(event["created_at"])
        self.cursor.execute("""
            insert into temp_gh_events (
                id, event_type, datetime, day, hour, user_id, repo_id
            ) select
                %(id)s, %(event_type)s, %(datetime)s, %(day)s, %(hour)s,
                %(user_id)s, %(repo_id)s
            where not exists (select id from temp_gh_events where id=%(id)s)
        """, dict(
            id=event["id"],
            event_type=event["type"],
            datetime=dt,
            day=dt.weekday(),
            hour=dt.hour,
            user_id=event["actor"]["id"],
            repo_id=event["repo"]["id"],
        ))

        # Process the event's user and repo.
        self._process_user(event["actor"])
        self._process_repo(event["repo"])

        # Parse any event specific elements.
        parser = self.event_types.get(event["type"], None)
        if parser is not None:
            parser(self, event["payload"])

    def _process_user(self, user):
        self.users[user["id"]] = dict(
            self.users[user["id"]],
            id=user["id"],
            login=user["login"],
            avatar_url=user["avatar_url"],
        )

        for a, b in [("user_type", "type"),
                     ("name", "name"),
                     ("location", "location")]:
            if b in user:
                self.users[user["id"]][a] = user[b]

    def _process_repo(self, repo):
        if "organization" in repo:
            self._process_user(repo["organization"])
        if "parent" in repo:
            self._process_repo(repo["parent"])
        if "source" in repo:
            self._process_repo(repo["source"])

        if "owner" in repo:
            name = repo["name"]
            self._process_user(repo["owner"])
            fullname = "{0}/{1}".format(repo["owner"]["login"], name)
            owner = repo["owner"]["id"]
        else:
            fullname = repo["name"]
            name = fullname.split("/")[-1]
            owner = None

        self.repos[repo["id"]] = dict(
            self.repos[repo["id"]],
            id=repo["id"],
            name=name,
            fullname=fullname,
        )

        if owner is not None:
            self.repos[repo["id"]]["owner_id"] = owner
        updated = repo.get("updated_at")
        if updated is not None:
            self.repos[repo["id"]]["last_updated"] = parse_datetime(updated)

        for a, b in [("language", "language"),
                     ("description", "description"),
                     ("fork", "fork"),
                     ("star_count", "stargazers_count"),
                     ("watcher_count", "subscribers_count"),
                     ("fork_count", "forks_count"),
                     ("issues_count", "open_issues_count")]:
            if b in repo:
                self.repos[repo["id"]][a] = repo[b]

    def _process_fork(self, payload):
        self._process_repo(payload["forkee"])

    def _process_pull_request(self, payload):
        self._process_repo(payload["pull_request"]["base"]["repo"])

    def _process_pull_request_comment(self, payload):
        self._process_pull_request(payload)

    event_types = dict(
        ForkEvent=_process_fork,
        PullRequestEvent=_process_pull_request,
        PullRequestReviewCommentEvent=_process_pull_request_comment,
    )


def update(files=None, since=None):
    parser = Parser()
    pool = Pool()
    if files is not None:
        list(pool.map(parser, ((fn, open(fn, "rb").read()) for fn in files)))
    else:
        today = date.today()
        if since is None:
            since = today - timedelta(1)
        else:
            since = date(**dict(zip(["year", "month", "day"],
                                map(int, since.split("-")))))

        print("updating since '{0}'".format(since))

        dler = Downloader()
        while since < today:
            base_date = dict(
                year=since.year,
                month=since.month,
                day=since.day,
            )

            print("downloading files for {year}-{month:02d}-{day:02d}"
                  .format(**base_date))
            urls = [archive_url.format(**(dict(base_date, n=n)))
                    for n in range(24)]
            strt = time.time()
            results = dler.download(
                urls, request_timeout=30*60, connect_timeout=30*60
            )
            print("download took {0} seconds...".format(time.time()-strt))

            list(pool.map(parser, results.items()))

            since += timedelta(1)
