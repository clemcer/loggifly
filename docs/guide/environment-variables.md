---
title: Environment Variables
---

# Environment Variables

Except for container / keyword specific settings and regex patterns a lot of the settings can be configured via **Environment Variables**.


| Variables                         | Description                                              | Default  |
|-----------------------------------|----------------------------------------------------------|----------|
| `NTFY_URL`                      | URL of your ntfy server instance                           | _N/A_    |
| `NTFY_TOKEN`                    | Authentication token for ntfy in case you need authentication.      | _N/A_    |
| `NTFY_USERNAME`                 | ntfy Username to use with the password in case you need authentication.             | _N/A_    |
| `NTFY_PASSWORD`                 | ntfy password to use with the username in case you need authentication.             | _N/A_    |
| `NTFY_TOPIC`                    | Notification topic for ntfy.                               | _N/A_  |
| `NTFY_TAGS`                     | [Tags/Emojis](https://docs.ntfy.sh/emojis/) for ntfy notifications. | kite,mag  |
| `NTFY_PRIORITY`                 | Notification [priority](https://docs.ntfy.sh/publish/?h=priori#message-priority) for ntfy messages.                 | 3 / default |
| `APPRISE_URL`                   | Any [Apprise-compatible URL](https://github.com/caronc/apprise/wiki)  | _N/A_    |
| `CONTAINERS`                    | A comma separated list of containers. These are added to the containers from the `config.yaml` (if you are using one).| _N/A_     |
| `SWARM_SERVICES`              |  A comma separated list of docker swarm services to monitor. | _N/A_     |
| `LOGGIFLY_MODE`              | Set this variable to `swarm` when wanting to use LoggiFly in swarm mode | _N/A_     |
| `GLOBAL_KEYWORDS`       | Keywords that will be monitored for all containers. Overrides `global_keywords.keywords` from the `config.yaml`.| _N/A_     |
| `GLOBAL_KEYWORDS_WITH_ATTACHMENT`| Notifications triggered by these global keywords have a logfile attached. | _N/A_     |
| `EXCLUDED_KEYWORDS`       | Keywords that will always be ignored. Can be used to suppress notifications from irrelevant log lines | _N/A_     |
| `ATTACH_LOGFILE`                | Attach a Logfile to *all* notifications. | True    |
| `ATTACHMENT_LINES`              | Define the number of Log Lines in the attachment file     | 20     |
| `NOTIFICATION_COOLDOWN`         | Cooldown period (in seconds) per container per keyword before a new message can be sent  | 5        | 
| `ACTION_COOLDOWN`         | Cooldown period (in seconds) before the next container action can be performed. Always at least 60s. (`action_keywords` are only configurable in YAML)  | 300        |
| `LOG_LEVEL`                     | Log Level for LoggiFly container logs.                    | INFO     |
| `MULTI_LINE_ENTRIES`            | When enabled the program tries to catch log entries that span multiple lines.<br>If you encounter bugs or you simply don't need it you can disable it.| True     |
| `HIDE_REGEX_IN_TITLE`         | Exclude regex from the notification title for a cleaner look. Useful when using very long regexes.| False     |
| `RELOAD_CONFIG`               | When the config file is changed the program reloads the config | True  |
| `DISABLE_START_MESSAGE`          | Disable startup message.                                  | False     |
| `DISABLE_SHUTDOWN_MESSAGE`       | Disable shutdown message.                                 | False     |
| `DISABLE_CONFIG_RELOAD_MESSAGE`       | Disable message when the config file is reloaded.| False     |
| `DISABLE_CONTAINER_EVENT_MESSAGE`       | Disable message when the monitoring of a container stops or starts.| False     |

