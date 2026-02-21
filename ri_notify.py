#!/usr/bin/env python3

import argparse
import datetime
import configparser
import logging
import praw
import random

from slack_sdk.rtm_v2 import RTMClient

PONG_SENTENCES = [
    "Let me know if you need help understanding the implications of this"
    " pong.",
    "ssSSssssSSssSSSsssssSsssspongssSssssSsssSSss",
    "Did you mean virtual table tennis with constructed rackets?",
    "If there really was a ping, someone else would have already ponged it.",
]


def format_submission(submission):
    return '<https://www.reddit.com{}|“{}”> by /u/{}: '.format(
        submission.permalink, submission.title, submission.author)


class Bot:
    def __init__(self, config):
        self.slack_token = config['slack']['bot_token']
        self.slack_channel = '#' + config['slack']['channel']
        self.reddit = praw.Reddit(
            client_id=config['reddit']['client_id'],
            client_secret=config['reddit']['client_secret'],
            username=config['reddit']['username'],
            password=config['reddit']['password'],
            user_agent='BadEconomics RI notifier Bot'
        )
        self.badeconomics = self.reddit.subreddit('badeconomics')
        self.rtm_client = RTMClient(token=self.slack_token, trace_enabled=True)

        @self.rtm_client.on('message')
        def _handle_message(client, event):
            self.handle_message(client, event)

    def run(self):
        self.rtm_client.connect()
        self.run_post_watcher()

    def run_post_watcher(self):
        for submission in self.badeconomics.stream.submissions(
            skip_existing=True
        ):
            if str(submission.author) == 'AutoModerator':
                continue
            # Skip submissions older than 4 hours to workaround
            # https://github.com/praw-dev/praw/issues/2090
            # https://www.reddit.com/r/bugs/comments/1nzpf87/praw_api_old_submissions_sporadically_showing_up/
            timedelta = (
                datetime.datetime.now(datetime.UTC)
                - datetime.datetime.fromtimestamp(
                    submission.created_utc, tz=datetime.UTC
                )
            )
            if timedelta.total_seconds() > 60 * 60 * 4:
                continue
            self.rtm_client.web_client.chat_postMessage(
                channel=self.slack_channel,
                text=('New RI: ' + format_submission(submission))
            )

    def handle_message(self, client, event):
        msg = event.get('text', '')
        if msg.casefold().startswith('!ping'):
            client.web_client.chat_postMessage(
                channel=event['channel'],
                text=random.choice(PONG_SENTENCES)
            )
        if msg.casefold().startswith('!backlog'):
            submissions = [
                '  - ' + format_submission(submission)
                for submission in self.badeconomics.new(limit=100)
                if (not submission.link_flair_text
                    and str(submission.author) != 'AutoModerator')
            ]
            text = "RIs without flair:\n" + '\n'.join(submissions)
            client.web_client.chat_postMessage(
                channel=event['channel'],
                text=text
            )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--config', default='settings.conf')
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    config = configparser.ConfigParser()
    config.read(args.config)

    bot = Bot(config)
    bot.run()


if __name__ == '__main__':
    main()
