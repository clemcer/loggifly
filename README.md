<a name="readme-top"></a>

<div align="center">
  <a href="clemcer/loggifly">
    <img src="/images/icon.png" alt="Logo" width="200" height="auto">
  </a>
</div>
<h1 align="center">LoggiFly</h1>

  <p align="center">
    <a href="https://github.com/clemcer/loggifly/issues">Report Bug</a>
    <a href="https://github.com/clemcer/loggifly/issues">Request Feature</a>
  </p>

<br>

**LoggiFly** - A Lightweight Tool that monitors Docker Container Logs for predefined keywords or regex patterns and sends Notifications.

Get instant alerts for security breaches, system errors, or custom patterns through your favorite notification channels. 🚀


**Ideal For**:
- ✅ Catching security breaches (e.g., failed logins in Vaultwarden)
- ✅ Debugging crashes with attached log context
- ✅ Restarting containers on specific errors or stopping them completely to avoid restart loops
- ✅ Monitoring custom app behaviors (e.g., when a user downloads an audiobook on your Audiobookshelf server)


<div align="center">
   <img src="/images/vault_failed_login.gif" alt="Failed Vaultwarden Login" width="auto" height="150">
</div>

---

## Content

- [Features](#-features)
- [Screenshots](#-screenshots)
- [Quick Start](#️-quick-start)
- [Configuration Deep Dive](#-Configuration-Deep-Dive)
  - [Basic config structure](#-basic-structure)
  - [Detailed Configuration Options](#-detailed-configuration-options)
  - [Environment Variables](#-environment-variables)
- [Socket Proxy](#%EF%B8%8F-socket-proxy)
- [Tips](#-tips)

---

## 🚀 Features

- **🔍 Plain Text, Regex & Multi-Line Log Detection**: Catch simple keywords or complex patterns in log entries that span multiple lines.
- **🚨 Ntfy/Apprise Alerts**: Send notifications directly to Ntfy or via Apprise to 100+ different services (Slack, Discord, Telegram).
- **🔁 Trigger Stop/Restart**: A restart/stop of the monitored container can be triggered on specific critical keywords.
- **⚙️ Fine-Grained Control**: Unique keywords and other settings (like ntfy topic/tags/priority) per container.
- **📁 Log Attachments**: Automatically include a log file to the notification for context.
- **⚡ Automatic Reload on Config Change**: The program automatically reloads the `config.yaml` when it detects that the file has been changed.

---
## 🖼 Screenshots

<div align="center">
   <img src="/images/abs_login.png" alt="Audiobookshelf Login" width="300" height="auto">
   <img src="/images/vault_failed_login.png" alt="Vaultwarden Login" width="300" height="auto">
   <img src="/images/abs_download.png" alt="Audiobookshelf Download" width="300" height="auto">
  <img src="/images/ebook2audiobook.png" alt="Ebook2Audiobook conversion finished" width="300" height="auto">

</div>

---

>[!TIP]
For better security use a [Docker Socket Proxy](#%EF%B8%8F-socket-proxy). You won't be able to trigger container stops/restarts with a proxy, but if you don't need that and want to secure your setup I recommend you take a look at [this section](#%EF%B8%8F-socket-proxy) before you finish the Quick Start Install process and think about using that compose file instead of the basic one in the Quick Start.

## ⚡️ Quick start


In this quickstart only the most essential settings are covered, [here](#-Configuration-Deep-Dive) is a more detailed config walkthrough.<br>

Choose your preferred setup method - simple environment variables for basic use or a YAML config for advanced control.
- Environment variables allow for a simple and much quicker setup
- With YAML you can use complex Regex patterns, have different keywords & other settings per container and set keywords that trigger a restart/stop of the container.

> [!Note]
In previous versions the config file was located in `/app/config.yaml`. This path still works but the official path was updated to `/config/config.yaml`. LoggiFly will first first look in `/config/config.yaml` and then `/app/config.yaml`.<br>
When `/config` is mounted a config template will be downloaded into that directory. 

<details><summary><em>Click to expand:</em> 🐋 <strong>Basic Setup: Docker Compose (Environment Variables)</strong></summary>
Ideal for quick setup with minimal configuration

```yaml
version: "3.8"
services:
  loggifly:
    image: ghcr.io/clemcer/loggifly:latest
    container_name: loggifly
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
#      - ./loggifly/config:/config  # This is where you would put your config file (ignore if you are only using environment variables)
    environment:
      # Choose at least one notification service
      NTFY_URL: "https://ntfy.sh"       
      NTFY_TOPIC: "your_topic"          
      # Token or Username+Password In case you need authentication
      # NTFY_TOKEN:
      # NTFY_USERNAME:
      # NTFY_PASSWORD:
      APPRISE_URL: "discord://..."      # Apprise-compatible URL
    
      CONTAINERS: "vaultwarden,audiobookshelf"        # Comma-separated list
      GLOBAL_KEYWORDS: "error,failed login,password"  # Basic keyword monitoring
      GLOBAL_KEYWORDS_WITH_ATTACHMENT: "critical"     # Attaches a log file to the notification
    restart: unless-stopped 
```
</details>


<details><summary><em>Click to expand:</em><strong> 📜 Advanced Setup: YAML Configuration</strong></summary>

Recommended for granular control, regex patterns and action_keywords. <br>

**Step 1: Docker Compose**

Use this [docker compose](/docker-compose.yaml) and edit this line:
```yaml
volumes:
  - ./loggifly/config:/config  # 👈 Replace left side of the mapping with your local path
```
If you want you can configure some of the settings or sensitive values like ntfy tokens or apprise URLs via [Environment Variables](#-environment-variables).

**Step 2: Configure Your config.yaml**

If `/config` is mounted a [template file](/config_template.yaml) will be downloaded into that directory. You can edit the downloaded template file and rename it to `config.yaml` to use it.<br>
You can also take a look at the [Configuration-Deep-Dive](#-Configuration-Deep-Dive) for all the configuration options.<br>
Or you can edit and copy paste the following minimal config into a newly created `config.yaml` file in `/config`.
```yaml
# You have to configure at least one container.
containers:
  container-name:  # Exact container name
  # Configure at least one type of keywords or use global keywords
    keywords:
      - error
      - regex: (username|password).*incorrect  # Use regex patterns when you need them
    # Attach a log file to the notification 
    keywords_with_attachment:
      - warn
    # Caution advised! These keywords will trigger a restart/stop of the container
    action_keywords:
      - stop: traceback
      - restart: critical

# Optional. These keywords are being monitored for all configured containers. There is an action_cooldown (see config deep dive)
global_keywords:
  keywords:
    - failed
  keywords_with_attachment:
    - critical

notifications:     
  # Configure either Ntfy or Apprise or both
  ntfy:
    url: http://your-ntfy-server  
    topic: loggifly                   
    token: ntfy-token               # Ntfy token in case you need authentication 
    username: john                  # Ntfy Username+Password in case you need authentication 
    password: 1234                  # Ntfy Username+Password in case you need authentication 
  apprise:
    url: "discord://webhook-url"    # Any Apprise-compatible URL (https://github.com/caronc/apprise/wiki)
```
</details><br>


**When everything is configured start the container**


```bash
docker compose up -d
```

---


## 🤿 Configuration Deep Dive


The Quick Start only covered the essential settings, here is a more detailed walktrough of all the configuration options.


### 📁 Basic Structure

The `config.yaml` file is divided into four main sections:

1. **`settings`**: Global settings like cooldowns and log levels. (_Optional since they all have default values_)
2. **`notifications`**: Configure Ntfy (_URL, Topic, Token, Priority and Tags_) and/or your Apprise URL
3. **`containers`**: Define which Containers to monitor and their specific Keywords (_plus optional settings_).
4. **`global_keywords`**: Keywords that apply to _all_ monitored Containers.


> [!IMPORTANT]
For the program to function you need to configure:
>- at least one container
>- at least one notification service (Ntfy or Apprise)
>- at least one keyword (either set globally or per container)
>
>  The rest is optional or has default values.


### 🔎 Detailed Configuration Options 

<details><summary><em>Click to expand:</em><strong> ⚙️ Settings </strong></summary>

```yaml
# These are the default settings
settings:          
  log_level: INFO               # DEBUG, INFO, WARNING, ERROR
  notification_cooldown: 5      # Seconds between alerts for same keyword (per container)
  action_cooldown: 300          # Cooldown period (in seconds) before the next container action can be performed. Maximum is always at least 60s.
  attachment_lines: 20          # Number of Lines to include in log attachments
  multi_line_entries: True      # Monitor and catch multi-line log entries instead of going line by line. 
  reload_config: True        # When the config file is changed the program reloads the config
  disable_start_message: False  # Suppress startup notification
  disable_shutdown_message: False  # Suppress shutdown notification
  disable_config_reload_message: False   # Suppress config reload notification
```

</details>



<details><summary><em>Click to expand:</em><strong> 📭 notifications </strong></summary>

```yaml
notifications:                       
  # At least one of the two (Ntfy/Apprise) is required.
  ntfy:
    url: http://your-ntfy-server    # Required. The URL of your Ntfy instance
    topic: loggifly.                # Required. the topic for Ntfy
    token: ntfy-token               # Ntfy token in case you need authentication 
    username: john                  # Ntfy Username+Password in case you need authentication 
    password: password              # Ntfy Username+Password in case you need authentication 
    priority: 3                     # Ntfy priority (1-5)
    tags: kite,mag                  # Ntfy tags/emojis 
  apprise:
    url: "discord://webhook-url"    # Any Apprise-compatible URL (https://github.com/caronc/apprise/wiki)
```
</details>


<details><summary><em>Click to expand:</em><strong> 🐳 containers </strong></summary>

```yaml
containers:
  container1: # leave blank if you only need global keywords

  container2: # these names must match the exact container names
    keywords:
      - keyword1
      - regex: regex-patern   # this is how to set regex patterns
    keywords_with_attachment: # attach a logfile to the notification
      - keyword2
    action_keywords: # trigger a restart/stop of the container. can not be set globally
      - restart: keyword3
      - stop: keyword4
  
  container3:
  # The next 6 settings override the global settings only for this container
    ntfy_tags: closed_lock_with_key   
    ntfy_priority: 5
    ntfy_topic: container3
    attachment_lines: 50     
    notification_cooldown: 2  
    action_cooldown: 60 

    keywords:
      - keyword1
    keywords_with_attachment:
      - keyword2
    action_keywords:  
      - stop: keyword3
      - restart: 
          regex: regex-pattern # this is how to set regex patterns for action_keywords
```

 </details>


<details><summary><em>Click to expand:</em><strong> 🌍 global_keywords </strong></summary>

```yaml
# This section is optional.
# These keywords are being monitored for all containers. 
global_keywords:              
  keywords:
    - error
  keywords_with_attachment:  # When one of these keywords is found a logfile is attached
    - regex: (critical|error)
```

</details>

<br>

[Here](/config_template.yaml) you can find a config template with all available configuration options and explaining comments. When `/config` is mounted in the volumes section of your docker compose this template file will be downloaded. <br>
[Here](/config.yaml) you can find an example config with some use cases.


### 🍀 Environment Variables

Except for `restart_keywords`, container specific settings/keywords and regex patterns you can configure most settings via docker environment variables.

<details><summary><em>Click to expand:</em><strong> Environment Variables </strong></summary><br>


| Variables                         | Description                                              | Default  |
|-----------------------------------|----------------------------------------------------------|----------|
| `NTFY_URL`                      | URL of your Ntfy server instance                           | _N/A_    |
| `NTFY_TOKEN`                    | Authentication token for Ntfy in case you need authentication.      | _N/A_    |
| `NTFY_USERNAME`                 | Ntfy Username to use with the password in case you need authentication.             | _N/A_    |
| `NTFY_PASSWORD`                 | Ntfy password to use with the username in case you need authentication.             | _N/A_    |
| `NTFY_TOPIC`                    | Notification topic for Ntfy.                               | _N/A_  |
| `NTFY_TAGS`                     | [Tags/Emojis](https://docs.ntfy.sh/emojis/) for ntfy notifications. | kite,mag  |
| `NTFY_PRIORITY`                 | Notification [priority](https://docs.ntfy.sh/publish/?h=priori#message-priority) for ntfy messages.                 | 3 / default |
| `APPRISE_URL`                   | Any [Apprise-compatible URL](https://github.com/caronc/apprise/wiki)  | _N/A_    |
| `CONTAINERS`                    | A comma separated list of containers. These are added to the containers from the config.yaml (if you are using one).| _N/A_     |
| `GLOBAL_KEYWORDS`       | Keywords that will be monitored for all containers. Overrides `global_keywords.keywords` from the config.yaml.| _N/A_     |
| `GLOBAL_KEYWORDS_WITH_ATTACHMENT`| Notifications triggered by these global keywords have a logfile attached. Overrides `global_keywords.keywords_with_attachment` from the config.yaml.| _N/A_     |
| `NOTIFICATION_COOLDOWN`         | Cooldown period (in seconds) per container per keyword before a new message can be sent  | 5        | 
| `ACTION_COOLDOWN`         | Cooldown period (in seconds) before the next container action can be performed. Always at least 60s. (`action_keywords` are only configurable in YAML)  | 300        |
| `LOG_LEVEL`                     | Log Level for LoggiFly container logs.                    | INFO     |
| `MULTI_LINE_ENTRIES`            | When enabled the program tries to catch log entries that span multiple lines.<br>If you encounter bugs or you simply don't need it you can disable it.| True     |
| `ATTACHMENT_LINES`              | Define the number of Log Lines in the attachment file     | 20     |
| `RELOAD_CONFIG`               | When the config file is changed the program reloads the config | True  |
| `DISBLE_START_MESSAGE`          | Disable startup message.                                  | False     |
| `DISBLE_SHUTDOWN_MESSAGE`       | Disable shutdown message.                                 | False     |
| `DISABLE_CONFIG_RELOAD_MESSAGE`       | Disable message when the config file is reloaded.| False     |

</details>

---

## ⚠️ Socket Proxy

A Docker Socket Proxy adds a security layer by controlling access to the Docker daemon — essentially letting LoggiFly only read container info and logs without giving it full control over the docker socket.<br>
With the linuxserver Image I have had some connection and timeout problems while streaming logs so the recommended proxy is [Tecnativa/docker-socket-proxy](https://github.com/Tecnativa/docker-socket-proxy).<br>
When using the Tecnativa Proxy the log stream connection drops every ~10 minutes for whatever reason, LoggiFly simply resets the connection.<br>
Here is a sample docker-compose file:


<details><summary><em>Click to expand:</em> <strong>Socket Proxy: Docker Compose </strong></summary>

```yaml
services:
  loggifly:
    image: ghcr.io/clemcer/loggifly:latest
    container_name: loggifly 
    volumes:
      - .loggifly/config:/config
    environment:
      TZ: Europe/Berlin
      DOCKER_HOST: tcp://socket-proxy:2375
    depends_on:
      - socket-proxy
    restart: unless-stopped
    
  socket-proxy:
    image: tecnativa/docker-socket-proxy
    container_name: docker-socket-proxy
    environment:
      - CONTAINERS=1  
      - POST=0        
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro  
    restart: unless-stopped

```

</details>

<br>

>[!Note]
`action_keywords` don't work when using a socket proxy.

## 💡 Tips

1. Ensure containers names **exactly match** your Docker **container names**. 
    - Find out your containers names: ```docker ps --format "{{.Names}}" ```
    - 💡 Pro Tip: Define the `container_name:` in your compose files.
2. **`action_keywords`** can not be set via environment variables, they can only be set per container in the `config.yaml`. The `action_cooldown` is always at least 60s long and defaults to 300s
3. **Test Regex Patterns**: Validate patterns at [regex101.com](https://regex101.com) before adding them to your config.
4. **Troubleshooting Multi-Line Log Entries**. If LoggiFly only catches single lines from log entries that span over multiple lines:
    - Wait for Patterns: LoggiFly needs to process a few lines in order to detect the pattern the log entries start with (e.g. timestamps/log level)
    - Unrecognized Patterns: If issues persist, open an issue and share the affected log samples

---

## License
[MIT](https://github.com/clemcer/LoggiFly/blob/main/LICENSE)
