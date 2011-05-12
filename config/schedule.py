# -*- coding: utf-8  -*-

# EarwigBot Configuration File
# This file tells the bot when to run certain wiki-editing tasks.

def check(minute, hour, month_day, month, week_day):
    tasks = [] # tasks to run this turn, each as a tuple of (task_name, kwargs) or just task_name

    if minute == 0: # run every hour on the hour
        tasks.append(("afc_statistics", {"action": "save"})) # save statistics to [[Template:AFC_statistics]]

        if hour == 0: # run every day at midnight
            tasks.append("afc_dailycats") # create daily categories for WP:AFC
            tasks.append("feed_dailycats") # create daily categories for WP:FEED

            if week_day == 0: # run every Sunday at midnight (that is, the start of Sunday, not the end)
                tasks.append("afc_undated") # clear [[Category:Undated AfC submissions]]

            if week_day == 1: # run every Monday at midnight
                tasks.append("afc_catdelink") # delink mainspace categories in declined AfC submissions

            if week_day == 2: # run every Tuesday at midnight
                tasks.append("wrongmime") # tag files whose extensions do not agree with their MIME type

            if week_day == 3: # run every Wednesday at midnight
                tasks.append("blptag") # add |blp=yes to {{WPB}} or {{WPBS}} when it is used along with {{WP Biography}}

    return tasks
