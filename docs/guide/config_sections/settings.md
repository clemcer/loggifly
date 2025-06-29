---
title: Settings Section
---

# Settings

This is how to define global settings in the config.yaml.
These are the default values:
  
```yaml
settings:          
  log_level: INFO               # DEBUG, INFO, WARNING, ERROR
  multi_line_entries: True      # Monitor and catch multi-line log entries instead of going line by line. 
  reload_config: True           # When the config file is changed the program reloads the config
  disable_start_message: False           # Suppress startup notification
  disable_shutdown_message: False        # Suppress shutdown notification
  disable_config_reload_message: False   # Suppress config reload notification
  disable_container_event_message: False # Suppress notification when monitoring of containers start/stop

  notification_cooldown: 5      # Seconds between alerts for same keyword (per container)
  notification_title: default   # configure a custom template for the notification title (see section below)
  action_cooldown: 300          # Cooldown period (in seconds) before the next container action can be performed. Maximum is always at least 60s.
  attach_logfile: False          # Attach a log file to all notifications
  attachment_lines: 20          # Number of Lines to include in log attachments
  hide_regex_in_title: False   # Exclude regex pattern from the notification title for a cleaner look
  excluded_keywords: <empty if not set> # List of keywords that will always be ignored in log lines. See the section below for how to configure these
  
```

## Notification Title

The setting `notification_title` requires a more detailed explanation:


When `notification_title: default` is set LoggiFly uses its own notification titles.
However, if you prefer something simpler or in another language, you can choose your own template for the notification title. 
This setting can also be configured per container and per keyword.

These are the two keys that can be inserted into the template:
- `keywords`: _The keywords that were found in a log line_ 
- `container`: _The name of the container in which the keywords have been found_

Here is an example:

```yaml
notification_title: "The following keywords were found in {container}: {keywords}"
```
Or keep it simple:
```yaml
notification_title: {container}
```

## Excluded Keywords

With this setting you can specify keywords that should _always_ be ignored. This is useful when you don't want to get notifications from irrelevant log lines.

`excluded_keywords` are set like this:

```yaml
settings:
  excluded_keywords:
    - keyword1
    - regex: regex-pattern1
```

