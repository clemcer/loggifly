# Containers 

Here you can define containers and assign keywords, regex patterns and optional settings to each one.
The container names must match the exact container names you would get with `docker ps`.

## Configure **Keywords** and **Regular Expressions**


```yaml
containers:
  container1:
    keywords:
      - error               # simple keyword
      - regex: \error\b.*   # this is how to set regex patterns
      - keyword: critical   # another way to set a simple keyword
    
```


## Attach Logfiles

With the `attach_logfile` option you can attach a logfile to the notification. 

::: tip
The setting `attachment_lines` lets you configure the number of log lines included in the attached file.
:::


```yaml
containers:
  container2:
    - keyword: error
      attach_logfile: true  # Attach a log file to the notification
```

## Container Actions


With the `action` option you can either `stop` or `restart` the container.

```yaml
containers:
  container3:
    - regex: \error\b.*
      action: restart  # Restart the container when this regex is found
    - keyword: critical
      action: stop     # Stop the container when this keyword is found
```

## Exclude Keywords

You can also exclude certain keywords from triggering notifications. This can be done globally (in [`settings`](./settings.md)), per container or per keyword/regex. 

```yaml
containers:
  container4:
    # Exclude keywords for a whole container
    excluded_keywords:
      - timeout  # This keyword will be ignored for this container
      - regex: \btimeout\b.*  # This regex will be ignored for this container
    keywords:
      - error
      - regex: \error\b.*
        # Exclude keywords for a specific keyword or regex pattern
        excluded_keywords:
          - uncritical  # Log lines with '\error\b.*' and 'uncritical' will be ignored
```

## Settings per container and keyword

Most of the **settings** from the `settings` and the `notifications` sections can be set per container or per keyword/regex.<br>
A summary of all the settings and where you can set them can be found [here](../settings-overview.md).

::: info
When multiple keywords with the same setting (e.g., `notification_title`) are found in a log line, the one listed first in the YAML takes precedence.
:::


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
      - critical

      - regex: \error\b.*
        ntfy_tags: partying_face   
        ntfy_priority: 5
        ntfy_topic: error
        attachment_lines: 10
        hide_regex_in_title: true

      - keyword: timeout
        apprise_url: "discord://webhook-url" 
        action: restart
        action_cooldown: 60 
        notification_title: '{container} restarted because these keywords were found: {keywords}'
        notification_cooldown: 10
        attach_logfile: true


```


## Keep it simple

If `global_keywords` are configured and you don't need additional keywords or settings for a container you can **leave it blank**:
  
```yaml
containers:
  container3:
  container4:
```

::: info
The only keyword settings missing here are the templates which are explained [here](../customize-notifications/).
:::
