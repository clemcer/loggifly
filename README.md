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



**LoggiFly** - A Lightweight Tool that monitors Docker Container Logs for predefined keywords or regex patterns and sends Notifications.

Get instant alerts for security breaches, system errors, or custom patterns through your favorite notification channels. 🚀


**Ideal For**:
- ✅ Catching security breaches (e.g., failed logins in Vaultwarden)
- ✅ Debugging crashes with attached log context
- ✅ Restarting containers on specific errors or stopping them completely to avoid restart loops
- ✅ Monitoring custom app behaviors (e.g., when a user downloads an audiobook on your Audiobookshelf server)


<div align="center">
   <img src="/images/vault_failed_login.gif" alt="Failed Vaultwarden Login" width="auto" height="200">
</div>

---

# Content

- [Features](#-features)
- [Screenshots](#-screenshots)
- [Quick Start](#️-quick-start)
- [Configuration Deep Dive](#-Configuration-Deep-Dive)
  - [Basic config structure](#-basic-structure)
  - [Settings Overview & Hierarchy Explained](#-settings-overview--hierarchy-explained)
    - [Settings](#%EF%B8%8F-settings)
    - [Notifications](#-notifications)
    - [Containers](#-containers)
    - [Global Keywords](#-global-keywords)
  - [Customize Notifications (Templates & Log Filtering)](#-customize-notifications-templates--log-filtering)
  - [Environment Variables](#-environment-variables)
- [Remote Hosts](#-remote-hosts)
  - [Labels](#labels)
  - [Assign Containers to hosts](#assign-containers-to-specific-hosts)
  - [Remote Hosts Example](#remote-hosts-example)
  - [Socket Proxy](#socket-proxy)
- [Docker Swarm](#docker-swarm)
- [Podman](#podman)
- [Tips](#-tips)
- [Support / Buy me a coffee](#support)


---

# 🚀 Features

- **🔍 Plain Text, Regex & Multi-Line Log Detection**: Catch simple keywords or complex patterns in log entries that span multiple lines.
- **🚨 Ntfy/Apprise Alerts**: Send notifications directly to Ntfy or via Apprise to 100+ different services (Slack, Discord, Telegram) or even to your own custom endpoint.
- **🔁 Trigger Stop/Restart**: A restart/stop of the monitored container can be triggered on specific critical keywords.
- **📁 Log Attachments**: Automatically include a log file to the notification for context.
- **⚡ Automatic Reload on Config Change**: The program automatically reloads the `config.yaml` when it detects that the file has been changed.
- **📝 Configurable Alerts**: Filter log lines for relevant information and use templates for your messages and notification titles.
- **🌐 Remote Hosts**: Connect to multiple remote Docker hosts.


---
# 🖼 Screenshots

<div style="display: flex; justify-content: center; gap: 10px; align-items: center;">
  <img src="/images/collage.png" alt="collage of screenshots" object-fit: contain;">
</div>

<br>

### 🎯 Customize notifications and filter log lines for relevant information:

<div style="display: flex; justify-content: center; gap: 10px; align-items: center;">
  <img src="/images/template_collage_rounded.png" alt="Custom Tepmplates Collage" object-fit: contain;">
</div>


---

>[!TIP]
>For better security use a **[Docker Socket Proxy](#socket-proxy)**.
You won't be able to trigger container stops/restarts with a proxy, but if you don't need that, consider taking a look at [this section](#socket-proxy) before you wrap up the Quick Start install and consider using that compose file instead of the basic one.

# ⚡️ Quick start

In this quickstart only the most essential settings are covered, [here](#-configuration-deep-dive) is a more detailed config walkthrough.<br>

Choose your preferred setup method - a simple docker compose with environment variables for basic use or a YAML config for advanced control.
- Environment variables allow for a **simple** and **much quicker** setup
- With a `config.yaml ` you can use complex **Regex patterns**, have different keywords & other settings **per container** and set keywords that trigger a **restart/stop** of the container.

> [!Note]
When `/config` is mounted a config template will be downloaded into that directory. 

<details><summary><em>Click to expand:</em> 🐋 <strong>Basic Setup: Docker Compose (Environment Variables)</strong></summary>
<br>
Ideal for quick setup with minimal configuration:

```yaml
version: "3.8"
services:
  loggifly:
    image: ghcr.io/clemcer/loggifly:latest
    container_name: loggifly
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
      # This is where you would put your config.yaml file (ignore if you are only using environment variables)
      # - ./loggifly/config:/config  
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

[Here](#-environment-variables) you can find some more environment variables that you could set.


</details>


<details><summary><em>Click to expand:</em><strong> 📜 Advanced Setup: YAML Configuration</strong></summary>
<br>
Recommended for granular control, regex patterns and action_keywords: <br>
<br>
  
**Step 1: Docker Compose**

Use this [docker compose](/docker-compose.yaml) and edit this line:
```yaml
volumes:
  - ./loggifly/config:/config  # 👈 Replace left side of the mapping with your local path
```
If you want you can configure some of the settings or sensitive values like ntfy tokens or apprise URLs via [Environment Variables](#environment-variables).

**Step 2: Configure Your config.yaml**

If `/config` is mounted a **[template file](/config_template.yaml) will be downloaded** into that directory. You can edit the downloaded template file and rename it to `config.yaml` to use it.<br>
You can also take a look at the [Configuration-Deep-Dive](#-Configuration-Deep-Dive) for all the configuration options.<br>

Or you can just edit and copy paste the following **minimal config** into a newly created `config.yaml` file in the mounted `/config` directory:
```yaml
# You have to configure at least one container.
containers:
  container-name:  # Exact container name
  # Configure at least one type of keywords or use global keywords
    keywords:
      - error
      - regex: (username|password).*incorrect  # Use regex patterns when you need them
  another-container:
    keywords:
      - login
    
# Optional. These keywords are being monitored for all configured containers. 
global_keywords:
  keywords:
    - failed
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


# 🤿 Configuration Deep Dive

The Quick Start only covered the essential settings, here is a more detailed walktrough of all the configuration options.


## 📁 Basic Structure

The `config.yaml` file is divided into four main sections:

1. **`settings`**: Global settings like cooldowns and log levels. (_Optional since they all have default values_)
2. **`notifications`**: Ntfy (_URL, Topic, Token, Priority and Tags_), your Apprise URL and/or a custom webhook url 
3. **`containers`**: Define which Containers to monitor and their specific Keywords (_plus optional settings_).
4. **`global_keywords`**: Keywords that apply to _all_ monitored Containers.


> [!IMPORTANT]
For the program to function you need to configure:
>- **at least one container**
>- **at least one notification service (Ntfy, Apprise or custom webhook)**
>- **at least one keyword / regex pattern (either set globally or per container)**
>
>  The rest is optional or has default values.

[Here](/config_template.yaml) you can find a **config template** with all available configuration options and explaining comments. When `/config` is mounted in the volumes section of your docker compose this template file will automatically be downloaded. <br>

[Here](/config_example.yaml) you can find an example config with some **use cases**.


## 🧩 Settings Overview & Hierarchy Explained

Before we dive into the four main sections of the config.yaml, it's important to understand how settings can be applied on three different levels (this applies to both normal `settings` and `notifications` settings):
- Global (`settings` / `notifications`)
- Per container (`containers`)
- Per keyword or regex (`keyword` / `regex`)

When the same setting is defined in multiple places, the following priority applies:

`keyword/regex > container > global`

The table below shows which settings are available and where they can be configured.<br>
This table is just for reference, detailled explanations and examples for these settings can be found below.

<details><summary><em>Click to expand:</em><strong> Overview of all the setings: </strong></summary>


| Setting                         | Global (`settings`) | Per Container (`containers`) | Per Keyword (`keywords`) | Description |
|---------------------------------|--------------------|-------------------------------|--------------------------|-------------|
| `log_level`                      | ✅                   | –                             | –                     | Logging level: `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `multi_line_entries`            | ✅                   | –                             | –                      | Enable detection of multi-line log entries |
| `reload_config`                 | ✅                   | –                             | –                      | Automatically reload config on changes |
| `disable_start_message`         | ✅                   | –                             | –                      | Disable startup notification |
| `disable_shutdown_message`      | ✅                   | –                             | –                      | Disable shutdown notification |
| `disable_config_reload_message` | ✅                   | –                             | –                      | Disable notification when config is reloaded |
| `disable_container_event_message`| ✅                  | –                             | –                      | Disable notification when container monitoring starts/stops |
| `hostnames`                      | –                    | ✅                            | –                      | Name of the host a container should be monitored on (if monitoring multiple hosts) |
| `hide_pattern_in_title`         | ✅                   | ✅                            | ✅                     | Exclude regex pattern from notification title for cleaner look | 
| `notification_cooldown`         | ✅                   | ✅                            | ✅                     | Seconds between repeated alerts per container and keyword |
| `notification_title`            | ✅                   | ✅                            | ✅                     | Template for the notification title (`{container}`, `{keywords}`) |
| `attachment_lines`              | ✅                   | ✅                            | ✅                     | Number of log lines to include in attachments |
| `attach_logfile`                | ✅                   | ✅                            | ✅                     | Attach log output to the notification (true/false) |
| `action_cooldown`               | ✅                   | ✅                            | –                      | Cooldown before triggering container actions (restart/stop) |
| `action`                        | –                    | –                             | ✅                      | Trigger container actions (restart/stop) |
| `json_template`                 | –                    | –                            | ✅                      | Template for JSON log entries |
| `template`                      | –                    | –                            | ✅                      | Template for plain text log entries using named capturing groups |

The same applies to the `notifications` settings. You can set the same settings globally or per container or per keyword/regex pattern. <br>

| Setting                         | Global (`notifications`) | Per Container (`containers`) | Per Keyword (`keywords`) | Description |
|---------------------------------|--------------------|-------------------------------|--------------------------|-------------|
| `apprise_url`                  | ✅ (`.apprise.url`)   | ✅                            | ✅                      | Apprise-compatible URL for notifications |
| `ntfy_url`                      | ✅ (`.ntfy.url`)     | ✅                            | ✅                 | Ntfy server URL |
| `ntfy_topic`                    | ✅ (`.ntfy.topic`)   | ✅                            | ✅                 | Ntfy topic |
| `ntfy_priority`                 | ✅ (`.ntfy.priority`)| ✅                            | ✅                 | Ntfy priority (1–5) |
| `ntfy_tags`                     | ✅ (`.ntfy.tags`)    | ✅                            | ✅                 | Tags/emojis for ntfy notifications |
| `ntfy_token`                    | ✅ (`.ntfy.token`)   | ✅                            |✅                      | Ntfy token for authentication |
| `ntfy_username`                 | ✅ (`.ntfy.username`) | ✅                            | ✅                     | Ntfy username for authentication |
| `ntfy_password`                 | ✅ (`.ntfy.password`) | ✅                            | ✅                     | Ntfy password for authentication |
| `webhook_url`                   | ✅ (`.webhook.url`)  | ✅                            | ✅                     | Custom webhook URL for notifications |
| `webhook_headers`               | ✅ (`.webhook.headers`) | ✅                            | ✅                     | Custom headers for webhook notifications |

> ✅ = supported<br>
> – = not supported
</details>


### ⚙️ Settings

Here you can see how to define global settings in the config.yaml. These are the default values:

<details><summary><em>Click to expand:</em><strong> Settings: </strong></summary>
  
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
  hide_pattern_in_title: False   # Exclude regex pattern from the notification title for a cleaner look

```
</details>


The setting `notification_title` requires a more detailed explanation:<br>

<details><summary><em>Click to expand:</em><strong> notification_title: </strong></summary>
<br>


When `notification_title: default` is set LoggiFly uses its own notification titles.<br>
However, if you prefer something simpler or in another language, you can choose your own template for the notification title. <br>
This setting can also be configured per container and per keyword (_see [containers](#-containers) section_).

These are the two keys that can be inserted into the template:<br>
`keywords`: _The keywords that were found in a log line_ <br>
`container`: _The name of the container in which the keywords have been found_



Here is an example:

```yaml
notification_title: "The following keywords were found in {container}: {keywords}"
```
Or keep it simple:
```yaml
notification_title: {container}
```

</details>


### 📭 Notifications

You can send notifications either directly to **Ntfy** or via **Apprise** to [most other  notification services](https://github.com/caronc/apprise/wiki). 

If you want the data to be sent to your own **custom endpoint** to integrate it into a custom workflow, you can set a custom webhook URL. LoggiFly will send all data in JSON format.

You can also set all three notification options at the same time

#### Ntfy:

<details><summary><em>Click to expand:</em><strong> Ntfy: </strong></summary>

```yaml
notifications:                       
  ntfy:
    url: http://your-ntfy-server    # Required. The URL of your Ntfy instance
    topic: loggifly.                # Required. the topic for Ntfy
    token: ntfy-token               # Ntfy token in case you need authentication 
    username: john                  # Ntfy Username+Password in case you need authentication 
    password: password              # Ntfy Username+Password in case you need authentication 
    priority: 3                     # Ntfy priority (1-5)
    tags: kite,mag                  # Ntfy tags/emojis 
```

</details>

#### Apprise:

<details><summary><em>Click to expand:</em><strong> Apprise: </strong></summary>

```yaml
notifications:
  apprise:
    url: "discord://webhook-url"    # Any Apprise-compatible URL (https://github.com/caronc/apprise/wiki)
```

</details>

#### Custom Webhook

<details><summary><em>Click to expand:</em><strong> Custom Webhook: </strong></summary>

```yaml
notifications:
  webhook: 
    url: https://custom.endpoint.com/post
    # add headers if needed
    headers:
      Authorization: "Bearer token"
      X-Custom-Header": "Test123"
```

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

### 🐳 Containers 

Here you can define containers and assign keywords, regex patterns, and optional settings to each one.<br>
The container names must match the exact container names you would get with `docker ps`.<br>

#### Configure **Keywords** and **Regular Expressions**

<details><summary><em>Click to expand:</em><strong> Keywords and Regex: </strong></summary>


```yaml
containers:
  container1:
    keywords:
      - keyword1               # simple keyword
      - regex: regex-patern1   # this is how to set regex patterns
      - keyword: keyword2      # another way to set a simple keyword
    
```

</details>


#### Attach logfiles or trigger restarts/stops of the container

<details><summary><em>Click to expand:</em><strong> Attachments and Actions: </strong></summary>

```yaml

containers:
  container2:
    - keyword: keyword1
      attatch_logfile: true  # Attach a log file to the notification
    - regex: regex-pattern1
      action: restart  # Restart the container when this regex pattern is found
    - keyword: keyword2
      action: stop     # Stop the container when this keyword is found
```

</details>

#### Settings per container and keyword

Most of the **settings** from the `settings` and the `notifications` sections can also be set per container or per keyword. A summary of all the settings and where you can set them can be found [here](#-settings-overview--hierarchy-explained) <br>

>[!Note]
>When multiple keywords are found in a log line that share the same setting, the one listed first in the YAML takes precedence.

<details><summary><em>Click to expand:</em><strong> Modular Settings: </strong></summary>


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
        hide_pattern_in_title: true

      - keyword: keyword3
        apprise_url: "discord://webhook-url" 
        action: restart
        action_cooldown: 60 
        notification_title: '{container} restarted because these keywords were found: {keywords}'
        notification_cooldown: 10
        attach_logfile: true


```

</details>

#### Keep it simple

If `global_keywords` are configured and you don't need additional keywords for a container you can **leave it blank**:

<details><summary><em>Click to expand:</em><strong> Keep it simple: </strong></summary>
  
```yaml
containers:
  container3:
  container4:
```
</details>

<br>

The only keyword settings missing are the templates which are explained [here](#-customize-notifications-templates--log-filtering).


### 🌍 Global Keywords

When `global_keywords` are configured, all containers are monitored for these keywords. These keywords can also be configured with additional settings as described in the [containers](#-containers) section. For an overview of all the possible settings refer to this [table](#-settings-overview--hierarchy-explained).
 
<details><summary><em>Click to expand:</em><strong> Global Keywords: </strong></summary>

```yaml
global_keywords:              
  keywords:
    - error
  keywords_with_attachment: # attach a logfile
    - regex: (critical|error)
```
<br>

</details>


## 📝 Customize Notifications (Templates & Log Filtering)


For users who want more control over the appearance of their notifications, there is an option to configure templates and filter log entries to display only the relevant parts.<br>
Here are some [examples](#-customize-notifications-and-filter-log-lines-for-relevant-information).<br>
Filtering is most straightforward with logs in JSON Format, but plain text logs can also be parsed by using named groups in the regex pattern.<br>

> [!Note]
> If you want to modify the notification title take a look at the setting `notification_title` in the [settings section](#%EF%B8%8F-settings). 

#### Template for JSON Logs:

<details><summary><em>Click to expand:</em> Filter Logs using a json_template:</summary>

<br>

`json_template` only works if the Logs are in JSON Format. Authelia is one such example.<br>
You can only use the placeholder variables that exist as keys in the JSON from the log line you want to catch.<br>

Here is an example where you want to catch this very long log entry from Authelia: 

```
{"level":"error","method":"POST","msg":"Unsuccessful 1FA authentication attempt by user 'example_user' and they are banned until 12:23:00PM on May 1 2025 (+02:00)","path":"/api/firstfactor","remote_ip":"192.168.178.191","stack":[{"File":"github.com/authelia/authelia/v4/internal/handlers/response.go","Line":274,"Name":"doMarkAuthenticationAttemptWithRequest"},{"File":"github.com/authelia/authelia/v4/internal/handlers/response.go","Line":258,"Name":"doMarkAuthenticationAttempt"},{"File":"github.com/authelia/authelia/v4/internal/handlers/handler_firstfactor_password.go","Line":51,"Name":"handlerMain.FirstFactorPasswordPOST.func14"},{"File":"github.com/authelia/authelia/v4/internal/middlewares/bridge.go","Line":66,"Name":"handlerMain.(*BridgeBuilder).Build.func7.1"},{"File":"github.com/authelia/authelia/v4/internal/middlewares/headers.go","Line":65,"Name":"SecurityHeadersCSPNone.func1"},{"File":"github.com/authelia/authelia/v4/internal/middlewares/headers.go","Line":105,"Name":"SecurityHeadersNoStore.func1"},{"File":"github.com/authelia/authelia/v4/internal/middlewares/headers.go","Line":30,"Name":"SecurityHeadersBase.func1"},{"File":"github.com/fasthttp/router@v1.5.4/router.go","Line":441,"Name":"(*Router).Handler"},{"File":"github.com/authelia/authelia/v4/internal/middlewares/log_request.go","Line":14,"Name":"handlerMain.LogRequest.func31"},{"File":"github.com/authelia/authelia/v4/internal/middlewares/errors.go","Line":38,"Name":"RecoverPanic.func1"},{"File":"github.com/valyala/fasthttp@v1.59.0/server.go","Line":2380,"Name":"(*Server).serveConn"},{"File":"github.com/valyala/fasthttp@v1.59.0/workerpool.go","Line":225,"Name":"(*workerPool).workerFunc"},{"File":"github.com/valyala/fasthttp@v1.59.0/workerpool.go","Line":197,"Name":"(*workerPool).getCh.func1"},{"File":"runtime/asm_amd64.s","Line":1700,"Name":"goexit"}],"time":"2025-05-01T14:19:29+02:00"}
```

In the config.yaml you can set a `json_template` for both plain text keywords and regex patterns. In the template I inserted three keys from the JSON Log Entry:

```yaml
containers:
  authelia:
    keywords:
      - keyword: Unsuccessful 1FA authentication
        json_template: '🚨 Failed Login Attempt:\n{msg}\n🔎 IP: {remote_ip}\n🕐{time}' 
      - regex: Unsuccessful.*authentication
        json_template: '🚨 Failed Login Attempt:\n{msg}\n🔎 IP: {remote_ip}\n🕐{time}' 
```

You can also extract data from nested json structures, including dictionaries and lists:

- {key} for top-level fields
- {dict[key]} for nested fields
- {list[index][key]} for list access (with indices starting at 0)

Example json log entry:

```json
{
  "user": {
    "name": "admin",
    "roles": [
      {"name": "superuser"},
      {"name": "editor"}
    ]
  },
  "location": {
    "city": "Berlin",
    "country": "Germany"
  }
}

```

Example `json_template`:

```yaml
json_template: 'User {user[name]}logged in from {location[city]}, Role: {user[roles][0][name]}'

```

<br>

</details>


#### Template using named capturing groups in Regex Pattern:

<details><summary><em>Click to expand:</em> Filter Logs using named capturing groups:</summary>


To filter non JSON Log Lines for certain parts you have to use a regex pattern with **named capturing groups**.<br> 
Lets take `(?P<group_name>...)` as an example. 
`P<group_name>` assigns the name `group_name` to the group.
The part inside the parentheses `(...)` is the pattern to match.<br>
Then you can insert the `{group_name}` into your custom message `template`.
<br>

Example Log Line from audiobookshelf:

```
[2025-05-03 10:16:53.154] INFO: [SocketAuthority] Socket VKrcSNa--FjwAqmSAAAU disconnected from client "example user" after 11696ms (Reason: transport close)
```

Regex pattern & Template:

```yaml
containers:
  audiobookshelf:
    keywords:
      - regex: '(?P<timestamp>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{3}).*Socket.*disconnected from client "(?P<user>[A-Za-z\s]+)"'
        template: '\n🔎 The user {user} was seen!\n🕐 {timestamp}'
        hide_pattern_in_title: true  # Exclude the regex pattern from the notification title for a cleaner look
      
```

**Result:**

- with `template` and `hide_pattern_in_title`:

<div style="display: flex; justify-content: center; gap: 10px;">
  <img src="/images/abs_with_template.png" style="height: 100px; object-fit: contain;">
</div>

- without for comparison:

<div style="display: flex; justify-content: center; gap: 10px;">
  <img src="/images/abs_without_template.png" style="height: 200px; object-fit: contain;">
</div>


<br>

</details>

>[!Note]
WIth both `json_template` and `template` you can add the key `original_log_line` to your template to add the full log entry to your notification message.


## 🍀 Environment Variables

Except for container / keyword specific settings and regex patterns you can configure most settings via **Docker environment variables**.

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
| `SWARM_SERVICES`              |  A comma separated list of docker swarm services to monitor. | _N/A_     |
| `LOGGIFLY_MODE`              | Set this variable to `swarm` when wanting to use LoggiFly in swarm mode | _N/A_     |
| `GLOBAL_KEYWORDS`       | Keywords that will be monitored for all containers. Overrides `global_keywords.keywords` from the config.yaml.| _N/A_     |
| `GLOBAL_KEYWORDS_WITH_ATTACHMENT`| Notifications triggered by these global keywords have a logfile attached. (These are converted into normal keywords with `attach_logfile`set to `True`| _N/A_     |
| `ATTACH_LOGFILE`                | Attach a Logfile to *all* notifications. | True    |
| `ATTACHMENT_LINES`              | Define the number of Log Lines in the attachment file     | 20     |
| `NOTIFICATION_COOLDOWN`         | Cooldown period (in seconds) per container per keyword before a new message can be sent  | 5        | 
| `ACTION_COOLDOWN`         | Cooldown period (in seconds) before the next container action can be performed. Always at least 60s. (`action_keywords` are only configurable in YAML)  | 300        |
| `LOG_LEVEL`                     | Log Level for LoggiFly container logs.                    | INFO     |
| `MULTI_LINE_ENTRIES`            | When enabled the program tries to catch log entries that span multiple lines.<br>If you encounter bugs or you simply don't need it you can disable it.| True     |
| `HIDE_PATTERN_IN_TITLE`         | Exclude regex pattern from the notification title for a cleaner look. Useful when using very long regex patterns.| False     |
| `RELOAD_CONFIG`               | When the config file is changed the program reloads the config | True  |
| `DISBLE_START_MESSAGE`          | Disable startup message.                                  | False     |
| `DISBLE_SHUTDOWN_MESSAGE`       | Disable shutdown message.                                 | False     |
| `DISABLE_CONFIG_RELOAD_MESSAGE`       | Disable message when the config file is reloaded.| False     |
| `DISABLE_CONTAINER_EVENT_MESSAGE`       | Disable message when the monitoring of a container stops or starts.| False     |

</details>

---

# 📡 Remote Hosts

LoggiFly supports connecting to **multiple remote hosts**.<br>
Remote hosts can be configured by providing a **comma-separated list of addresses** in the `DOCKER_HOST` environment variable.<br>
To use **TLS** you have to mount `/certs` in the volumes section of your docker compose.<br>
LoggiFly expects the TLS certificates to be in `/certs/{ca,cert,key}.pem` or in case of multiple hosts `/certs/{host}/{ca,cert,key}.pem` with `{host}` being either the IP or FQDN.<br>
You can also combine remote hosts with a mounted docker socket.<br>

>[!NOTE]
When the connection to a docker host is lost, LoggiFly will try to reconnect every 60s

## Labels 
When multiple hosts are set LoggiFly will use **labels** to differentiate between them both in notifications and in logging.<br>
You can set a **label** by appending it to the address with `"|"` ([_see example_](#remote-hosts-example)).<br>
When no label is set LoggiFly will use the **hostname** retrieved via the docker daemon. If that fails, usually because `INFO=1` has to be set when using a proxy, the labels will just be `Host-{Nr}`.<br>

If you want to set a label to the mounted docker socket you can do so by adding `unix:///var/run/docker.sock|label` in the `DOCKER_HOST` environment variable (_the socket still has to be mounted_) or just set the address of a [socket proxy](#socket-proxy) with a label.

## Assign Containers to specific Hosts

You can assign containers to specific hosts by providing a comma-separated list of hostnames under the `hostnames` field in the container configuration. The [labels](#labels) section shows how the hostname is constructed.<br> 
When no hostnames are set LoggiFly will look for the container on all configured remote hosts.

Here is a short yaml snippet showing how to assign a container to a specific host:

<details><summary><em>Click to expand:</em><strong> Assign Containers </strong></summary><br>
  
```yaml 
containers:
  container1:
    hostnames: foobar  # This container will only be monitored on the host with the label 'foobar'
    keywords:
      - error
```
</details>

## Remote Hosts Example

In this example, LoggiFly monitors container logs from the **local host** via a mounted Docker socket, as well as from **two remote Docker hosts** configured with TLS. One of the remote hosts is referred to as ‘foobar’. The local host and the second remote host have no custom label and are identified by their respective hostnames.

<details><summary><em>Click to expand:</em> <strong>Remote Hosts: Docker Compose </strong></summary>

```yaml
version: "3.8"
services:
  loggifly:
    image: ghcr.io/clemcer/loggifly:latest
    container_name: loggifly 
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - ./loggifly/config:/config # Place your config.yaml here if you are using one
      - ./certs:/certs
      # Assuming the Docker hosts use TLS, the folder structure for the certificates should be like this:
      # /certs/
      # ├── 192.168.178.80/
      # │   ├── ca.pem
      # │   ├── cert.pem
      # │   └── key.pem
      # └── 192.168.178.81/
      #     ├── ca.pem
      #     ├── cert.pem
      #     └── key.pem
    environment:
      TZ: Europe/Berlin
      DOCKER_HOST: tcp://192.168.178.80:2376,tcp://192.168.178.81:2376|foobar
    restart: unless-stopped
```
</details>

## Socket Proxy

You can also connect via a **Docker Socket Proxy**.<br>
A Socket Proxy adds a security layer by **controlling access to the Docker daemon**, essentially letting LoggiFly only read certain info like container logs without giving it full control over the docker socket.<br>
With the linuxserver image I have had some connection and timeout problems so the recommended proxy is **[Tecnativa/docker-socket-proxy](https://github.com/Tecnativa/docker-socket-proxy)**.<br>
When using the Tecnativa Proxy the log stream connection drops every ~10 minutes for whatever reason, LoggiFly simply resets the connection.<br>

Here is a sample **docker compose** file:

<details><summary><em>Click to expand:</em> <strong>Socket Proxy: Docker Compose </strong></summary>

```yaml
version: "3.8"
services:
  loggifly:
    image: ghcr.io/clemcer/loggifly:latest
    container_name: loggifly 
    volumes:
      - ./loggifly/config:/config # Place your config.yaml here if you are using one
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

>[!Note]
`action_keywords` don't work when using a socket proxy.
<br>


# Docker Swarm

> [!Important] 
Docker Swarm Support is still experimental because I have little to no experience with it and can not say for certain whether it works flawlessly.
If you notice any bugs or have suggestions let me know.

To use LoggiFly in swarm mode you have to set the environment variable `LOGGIFLY_MODE` to `swarm`.<br>

The `config.yaml` is passed to each worker via [Docker Configs](https://docs.docker.com/reference/cli/docker/config/) (_see example_).<br>

The configuration pretty much stays the same except that you set `swarm_services` instead of `containers` or use the `SWARM_SERVICES` environment variable. <br>

If normal `containers` are set instead of or additionally to `swarm_services` LoggiFly will also look for these containers on every node.

**Docker Compose**

<details><summary><em>Click to expand:</em> <strong>Docker Compose </strong></summary>

```yaml
version: "3.8"

services:
  loggifly:
    image: ghcr.io/clemcer/loggifly:latest
    deploy:
      mode: global  # runs on every node
      restart_policy:
        condition: any
        delay: 5s
        max_attempts: 5
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro 
    environment:
      TZ: Europe/Berlin
      LOGGIFLY_MODE: swarm
      # Uncomment the next three variables if you want to only use environment variables instead of a config.yaml
      # SWARM_SERVICES: nginx,redis
      # GLOBAL_KEYWORDS: keyword1,keyword2
      # GLOBAL_KEYWORDS_WITH_ATTACHMENT: keyword3
      # For more environment variables see the environment variables section in the README 
# Comment out the rest of this file if you are only using environment variables
    configs:
      - source: loggifly-config
        target: /config/config.yaml  

configs:
  loggifly-config:
    file: ./loggifly/config.yaml  # SET YOU THE PATH TO YOUR CONFIG.YAML HERE

```
</details>

**Config.yaml**

<details><summary><em>Click to expand:</em> <strong>config.yaml </strong></summary>

In the `config.yaml` you can set services that should be monitored just like you would do with containers.

```yaml
swarm_services:
  nginx:
    keywords:
      - error
  redis:
    keywords_with_attachment:
      - fatal
```

If both nginx and redis are part of the same compose stack named `my_service` you can configure that service name to monitor both:
```yaml
swarm_services:
  my_service: # includes my_service_nginx and my_service_redis
    keywords:
      - error
    keywords_with_attachment:
      - fatal
```

For all available configuration options, refer to the [Containers section](#-containers) of the configuration walkthrough — the `swarm_services` configuration is identical to that of `containers`.

</details>


# Podman

LoggiFly can also be used with Podman.<br>
When running the container as root you can just use the docker compose file and start the container with `podman-compose up -d`. 
Just make sure to mount your Podman socket and set the environment variable `DOCKER_HOST` to the socket, e.g. `DOCKER_HOST=unix:///run/user/1000/podman/podman.sock`. <br>

When running the container rootless it is a bit more complicated.<br>
You have to set the `userns` which unfortunately can not be set in the docker compose.<br>
So your two options are to either use a `podman run` command or create a podman quadlet file and run it via `systemctl --user start loggifly`. <br>
  
Sometimes the `User` and `SecurityLabelDisable` options have to be set as well. <br>

Here is an example of how to run LoggiFly with a Podman run command. <br>

<details><summary><em>Click to expand:</em> <strong>Podman run command: </strong></summary>


```bash

podman run -d \
  --name loggifly \
  --userns keep-id:uid=1000,gid=1000 \
  -v /run/user/1000/podman/podman.sock:/run/user/1000/podman/podman.sock \
  -v /path/to/config.yaml:/config/config.yaml \
  -e DOCKER_HOST=unix:///run/user/1000/podman/podman.sock \
  -e CONTAINERS="container1,container2" \
  -e GLOBAL_KEYWORDS="error,critical" \
  ghcr.io/clemcer/loggifly:latest
```

You might also need these two options depending on your setup:

```bash
  --security-opt label=disable \  # only necessary if SElinux prohibits the access of sockets from inside the container
  --user 1000:1000 \              # might be necessary depending on your setup```
```

</details>


Here is an example of how to run LoggiFly with a Podman quadlet file. <br>

<details><summary><em>Click to expand:</em> <strong>Podman Quadlet: </strong></summary>

Place the following file in  `~/.config/containers/systemd/loggifly.container` and edit it to suit your needs:

```ini
[Unit]
Description=Loggifly container
Wants=network-online.target
After=network-online.target

[Container]
ContainerName=loggifly
Image=ghcr.io/clemcer/loggifly:latest
AutoUpdate=registry # auto update of image, podman-auto-update.timer needs to run for it to work
Environment=CONTAINERS="container1,container2"
Environment=GLOBAL_KEYWORDS="error,failed login,password"
Environment=GLOBAL_KEYWORDS_WITH_ATTACHMENT="critical"
Environment=APPRISE_URL=<apprise url>
Environment=DOCKER_HOST=unix:///run/user/1000/podman/podman.sock
Volume=/path/to/config:/config
Volume=/run/user/1000/podman/podman.sock:/run/user/1000/podman/podman.sock
UserNS=keep-id:uid=1000,gid=1000 
#User=1000:1000            # might be necessary depending on your setup
#SecurityLabelDisable=true # only necessary if SElinux prohibits the access of sockets from inside the container

[Service]
Restart=always

[Install]
WantedBy=multi-user.target default.target # default target is only necessary if a start at boot is desired

```

Start the container with:

```bash 
systemctl --user start loggifly
```

</details>


# 💡 Tips

1. Ensure containers names **exactly match** your Docker **container names**. 
    - Find out your containers names: ```docker ps --format "{{.Names}}" ```
    - 💡 Pro Tip: Define the `container_name:` in your compose files.
2. **Regex Patterns**:
   - Validate patterns at [regex101.com](https://regex101.com) before adding them to your config.
   - use `hide_pattern_in_title: true` when using very long regex patterns to have a cleaner notification title _(or hide found keywords from the title altogether with your own custom `notification_title` ([see settings](#%EF%B8%8F-settings))_
   - 
3. **Troubleshooting Multi-Line Log Entries**. If LoggiFly only catches single lines from log entries that span over multiple lines:
    - Wait for Patterns: LoggiFly needs to process a few lines in order to detect the pattern the log entries start with (e.g. timestamps/log level)
    - Unrecognized Patterns: If issues persist, open an issue and share the affected log samples

---


# Support

If you find LoggiFly useful, drop a ⭐️ on the repo

<p>
    <a href="https://www.buymeacoffee.com/clemcer" target="_blank"><img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" alt="Buy Me A Coffee" height="50"></a>
</p>


# Star History

[![Star History Chart](https://api.star-history.com/svg?repos=clemcer/loggifly&type=Date)](https://www.star-history.com/#clemcer/loggifly&Date)

## License
[MIT](https://github.com/clemcer/LoggiFly/blob/main/LICENSE)
