---
title: Configuration Walkthrough
---

## ⚙️ Settings

This is how to define global settings in the config.yaml.
These are the default values:
  
```yaml
settings:          
  log_level: INFO                        # DEBUG, INFO, WARNING, ERROR
  multi_line_entries: True               # Monitor and catch multi-line log entries instead of going line by line. 
  reload_config: True                    # When the config file is changed the program reloads the config
  disable_start_message: False           # Suppress startup notification
  disable_shutdown_message: False        # Suppress shutdown notification
  disable_config_reload_message: False   # Suppress config reload notification
  disable_container_event_message: False # Suppress notification when monitoring of containers start/stop

  # The following settings can also be set per container or per keyword/regex
  notification_cooldown: 5            # Seconds between alerts for same keyword (per container)
  notification_title: default         # Custom template for notification title
  action_cooldown: 300                # Cooldown (seconds) before next container action (min 60s)
  attach_logfile: False               # Attach log file to all notifications
  attachment_lines: 20                # Lines to include in log attachments
  hide_regex_in_title: False          # Hide regex in notification title
  excluded_keywords:                  # List of keywords that will always be ignored in log lines. See the section below for how to configure these. 

```

The setting `notification_title` requires a more detailed explanation:


When `notification_title: default` is set LoggiFly uses its own notification titles.
However, if you prefer something simpler or in another language, you can choose your own template for the notification title. 
This setting can also be configured per container and per keyword.

These are the two keys that can be inserted into the template:
`keywords`: _The keywords that were found in a log line_ 
`container`: _The name of the container in which the keywords have been found_

Here is an example:

```yaml
notification_title: "The following keywords were found in {container}: {keywords}"
```
Or keep it simple:
```yaml
notification_title: {container}
```

`excluded_keywords` are set like this:

```yaml
settings:
  excluded_keywords:
    - keyword1
    - regex: regex-pattern1
```

## 📭 Notifications

You can send notifications either directly to **Ntfy** or via **Apprise** to [most other  notification services](https://github.com/caronc/apprise/wiki). 

If you want the data to be sent to your own **custom endpoint** to integrate it into a custom workflow, you can set a custom webhook URL. LoggiFly will send all data in JSON format.

You can also set all three notification options at the same time

::: code-group

```yaml [Ntfy]
notifications:                       
  ntfy:
    url: http://your-ntfy-server    # Required. The URL of your Ntfy instance
    topic: loggifly.                # Required. the topic for Ntfy
    token: ntfy-token               # Ntfy token in case you need authentication 
    username: john                  # Ntfy Username + Password in case you need authentication 
    password: password              # Ntfy Username + Password in case you need authentication 
    priority: 3                     # Ntfy priority (1-5)
    tags: kite,mag                  # Ntfy tags/emojis 
```



```yaml [Apprise]
notifications:
  apprise:
    url: "discord://webhook-url"    # Any Apprise-compatible URL (https://github.com/caronc/apprise/wiki)
```


```yaml [Custom Webhook]
notifications:
  webhook: 
    url: https://custom.endpoint.com/post
    # add headers if needed
    headers:
      Authorization: "Bearer token"
      X-Custom-Header: "Test123"
```

:::

<details>
<summary><strong> Webhook JSON Structure: </strong></summary>

If a **webhook** is configured LoggiFly will post a JSON to the URL with the following data:

```yaml
{
  "container": "...",
  "keywords": [...],
  "title": "...",
  "message": "...", 
  "host": "..."   # None unless multiple hosts are monitored
}

```
</details>

## 🐳 Containers 

Here you can define containers and assign keywords, regex patterns, and optional settings to each one.
The container names must match the exact container names you would get with `docker ps`.

### Configure **Keywords** and **Regular Expressions**


```yaml
containers:
  container1:
    keywords:
      - keyword1               # simple keyword
      - regex: regex-patern1   # this is how to set regex patterns
      - keyword: keyword2      # another way to set a simple keyword
    
```


### Attach logfiles or trigger restarts/stops of the container

```yaml

containers:
  container2:
    - keyword: keyword1
      attach_logfile: true  # Attach a log file to the notification
    - regex: regex-pattern1
      action: restart  # Restart the container when this regex pattern is found
    - keyword: keyword2
      action: stop     # Stop the container when this keyword is found
```


### Exclude Keywords

You can also exclude certain keywords from triggering notifications. This can be done globally (in `settings`), per container or per keyword/regex. This is useful when you don't want to get notifications from irrelevant log lines that contain certain keywords.


```yaml
containers:
  # Exclude keywords for a whole container
  container2:
    keywords:
      - keyword1
      - regex: regex-pattern1
    excluded_keywords:
      - keyword2  # This keyword will be ignored for this container
      - regex: regex-pattern2  # This regex pattern will be ignored for this container

  # You can also exclude keywords for a specific keyword or regex pattern
  container3:
    keywords:
      - keyword3
      - keyword: keyword4
        excluded_keywords:
          - keyword5  # Log lines with 'keyword4' and 'keyword5' will be ignored
```

### Settings per container and keyword

Most of the **settings** from the `settings` and the `notifications` sections can also be set per container or per keyword. A summary of all the settings and where you can set them can be found [here](#-settings-overview--hierarchy-explained).

>[!Note]
>When multiple keywords are found in a log line that share the same setting, the one listed first in the YAML takes precedence.



```yaml
containers:
  container2:
    apprise_url: "discord://webhook-url"  
    ntfy_tags: closed_lock_with_key   
    ntfy_priority: 3
    ntfy_topic: container3
    webhook_url: https://custom.endpoint.com/post
    attachment_lines: 50
    notification_title: '{keywords} found in {container}'
    notification_cooldown: 2  
    attach_logfile: true
    action_cooldown: 60 
  
    keywords:
      - keyword1
      - keyword2

      - regex: regex-pattern1
        ntfy_tags: partying_face   
        ntfy_priority: 5
        ntfy_topic: error
        attachment_lines: 10
        hide_regex_in_title: true

      - keyword: keyword3
        apprise_url: "discord://webhook-url" 
        action: restart
        action_cooldown: 60 
        notification_title: '{container} restarted because these keywords were found: {keywords}'
        notification_cooldown: 10
        attach_logfile: true


```


### Keep it simple

If `global_keywords` are configured and you don't need additional keywords or settings for a container you can **leave it blank**:
  
```yaml
containers:
  container3:
  container4:
```


The only keyword settings missing are the templates which are explained [here](#-customize-notifications-templates--log-filtering).


## 🌍 Global Keywords

When `global_keywords` are configured, all containers are monitored for these keywords. These keywords can also be configured with additional settings as described in the [containers](#-containers) section. For an overview of all the possible settings refer to this [table](#-settings-overview--hierarchy-explained).
 
```yaml
global_keywords:              
  keywords:
    - error
  keywords_with_attachment: # attach a logfile
    - regex: (critical|error)
```
