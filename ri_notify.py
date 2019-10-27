#!/usr/bin/env python3

import configparser
import praw
import slack
import multiprocessing

config = configparser.ConfigParser()
config.read('settings.conf')

reddit = praw.Reddit(
    client_id=config['reddit']['client_id'],
    client_secret=config['reddit']['client_secret'],
    username=config['reddit']['username'],
    password=config['reddit']['password'],
    user_agent='BadEconomics RI notifier Bot'
)

badeconomics = reddit.subreddit('badeconomics')


def format_submission(submission):
    return '<https://www.reddit.com{}|“{}”> by /u/{}: '.format(
        submission.permalink, submission.title, submission.author)


@slack.RTMClient.run_on(event='message')
def backlog(**payload):
    data = payload['data']
    if data.get('text', '').casefold().startswith('!backlog'):
        submissions = [
            '  - ' + format_submission(submission)
            for submission in badeconomics.new(limit=100)
            if (not submission.link_flair_text
                and str(submission.author) != 'AutoModerator')
        ]
        text = "RIs without flair:\n" + '\n'.join(submissions)
        payload['web_client'].chat_postMessage(
            channel=data['channel'],
            text=text
        )


def command_watcher():
    rtm_client = slack.RTMClient(token=config['slack']['bot_token'])
    rtm_client.start()


def new_watcher():
    slackclient = slack.WebClient(token=config['slack']['bot_token'])

    for submission in badeconomics.stream.submissions(skip_existing=True):
        if str(submission.author) == 'AutoModerator':
            continue
        slackclient.chat_postMessage(
            channel=('#' + config['slack']['channel']),
            text=('New RI: ' + format_submission(submission))
        )


def main():
    process = multiprocessing.Process(target=command_watcher)
    process.start()
    new_watcher()


if __name__ == '__main__':
    main()
