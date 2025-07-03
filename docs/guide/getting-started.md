---
title: What is LoggiFly?
---

# Getting Started

LoggiFly can easily be deployed on Docker, Docker Swarm or Podman.
The quickest way to get started is by configuring LoggiFly with environment variables only, but for full flexibility and feature access, using a config.yaml file is recommended.

::: info
Environment variables allow for a simple and much quicker setup but they don't support configuring different keywords per container or features like regex, container actions, message formatting and more.
With a config.yaml you do have access to all features as well as finegrained control over which keywords and settings are applied to each container.
:::

The following section will provide a quick start with minimal configuration. 
For more features and customization options, start [here](./config-structure) to learn more about how to configure LoggiFly.

## Notification Services

You can directly send notifications to ntfy and change topic, tags, priority, etc. 

You can also send notifications to most other notification services via **Apprise**. Just follow their [docs](https://github.com/caronc/apprise/wiki) on how to best configure the Apprise URL for your notification service.

---

::: tip Tips
- With a config.yaml you can change ntfy settings and Apprise URLs per container and even per keyword allowing you to send notifications to different channels based on the container/keyword.
- For better security use a **[Docker Socket Proxy](#socket-proxy)**.
:::

## Option 1: Environment Variables Only (no `config.yaml`)

This is the fastest way to try out LoggiFly with minimal setup.
Simply run the container and pass the required options as environment variables. All available environment variables are listed [here](./environment-variables).

::: code-group

```yaml [docker-compose.yaml]
version: "3.8"
services:
  loggifly:
    image: ghcr.io/clemcer/loggifly:latest
    container_name: loggifly
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
    environment:
      # Choose at least one notification service
      NTFY_URL: "https://ntfy.sh"       
      NTFY_TOPIC: "your_topic"          
      # ntfy Token or Username + Password In case you need authentication
      NTFY_TOKEN: <token>
      NTFY_USERNAME: <username>
      NTFY_PASSWORD: <password>
      APPRISE_URL: "discord://..."      # Apprise-compatible URL
    
      CONTAINERS: "vaultwarden,audiobookshelf"        # Comma-separated list
      GLOBAL_KEYWORDS: "error,failed login,password"  # Basic keyword monitoring
      GLOBAL_KEYWORDS_WITH_ATTACHMENT: "critical"     # Attaches a log file to the notification
    restart: unless-stopped 
```


```sh
docker run --name loggifly \
-v /var/run/docker.sock:/var/run/docker.sock:ro \
-e NTFY_URL=https://ntfy.sh \
-e NTFY_TOPIC=your_topic \
-e NTFY_TOKEN -e NTFY_USERNAME \
-e NTFY_PASSWORD \
-e APPRISE_URL=discord://... \
-e CONTAINERS=vaultwarden,audiobookshelf \
-e GLOBAL_KEYWORDS="error,failed login,password" \
-e GLOBAL_KEYWORDS_WITH_ATTACHMENT=critical \
--restart unless-stopped \
ghcr.io/clemcer/loggifly:latest

```
:::


## Option 2: Mount a config.yaml (recommended for most setups)

Recommended for granular control and access to all features like regex, container actions, message formatting and more.

::: code-group

```yaml [docker-compose.yaml]
version: "3.8"
services:
  loggifly:
    image: ghcr.io/clemcer/loggifly:latest
    container_name: loggifly
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - ./loggifly/config:/config    # Place your config.yaml in this directory
    restart: unless-stopped 
```


```sh
# Place your config.yaml in ./loggifly/config
docker run --name loggifly \
-v /var/run/docker.sock:/var/run/docker.sock:ro \
-v ./loggifly/config:/config \
--restart unless-stopped \
ghcr.io/clemcer/loggifly:latest

```
:::

::: tip Tips
- For all configuration options take a look at the [Config Sections](./config-structure). 
- If `/config` is mounted a **[template file](./config-structure#config-template) will be downloaded** into that directory. You can edit the downloaded template file and rename it to `config.yaml` to use it. 
- You can also draw inspiration from this **[config example](./config-structure#config-example)** with some real use cases.
:::

Here is a very **minimal config** that you can edit and copy paste into a newly created `config.yaml` file in the mounted `/config` directory:

```yaml
# You have to configure at least one container.
containers:
  container-name:  # Exact container name
    keywords:
      - error
      - regex: (username|password).*incorrect  # Use regex when you need them
  another-container:
    keywords:
      - login
    
# Optional. These keywords are being monitored for all configured containers. 
global_keywords:
  keywords:
    - failed
    - critical

notifications:     
  # Configure either ntfy or Apprise or both
  ntfy:
    url: http://your-ntfy-server  
    topic: loggifly                   
    token: ntfy-token               # ntfy token in case you need authentication 
    username: john                  # ntfy Username + Password in case you need authentication 
    password: 1234                  # ntfy Username + Password in case you need authentication 
  apprise:
    url: "discord://webhook-url"    # Any Apprise-compatible URL (https://github.com/caronc/apprise/wiki)
```
