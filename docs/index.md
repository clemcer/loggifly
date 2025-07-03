---
# https://vitepress.dev/reference/default-theme-home-page
layout: home

hero:
  name: "LoggiFly"
  text: "Get Alerts from your Docker Container Logs"
  # tagline: My great project tagline
  image:
    src: /icon.png
    alt: LoggiFly Logo

  actions:
    - theme: brand
      text: Get Started  
      link: /guide/getting-started
    - theme: alt
      text: GitHub
      link: https://github.com/clemcer/loggifly
    - theme: alt
      text: Buy me a Coffee
      link: https://www.buymeacoffee.com/clemcer

features:
  - title: Plain Text, Regex & Multi-Line Log Detection
    details: Catch simple keywords or complex patterns in log entries that span multiple lines.
    icon: 🔍
  - title: Notifications
    details: Send notifications directly to ntfy or via Apprise to 100+ different services (Slack, Discord, Telegram) or even to your own custom endpoint.
    icon: 🚨
  - title: Trigger Stop/Restart
    details: Restart or stop containers automatically when critical keywords appear in the logs.
    icon: 🔁
  - title: Log Attachments
    details: Automatically include a log file with your notification for better context.
    icon: 📁
  - title: Automatic Reload on Config Change
    details: LoggiFly automatically reloads the config.yaml when changes are detected.
    icon: ⚡
  - title: Configurable Alerts
    details: Format log messages with templates and only display the relevant information.
    icon: 📝
    linkText: Learn More
    link: /guide/customize-notifications
  - title: Remote Hosts
    details: Monitor and receive alerts from multiple remote Docker hosts.
    icon: 🌐
    linkText: Learn More
    link: /guide/remote-hosts
  - title: Multi-Platform
    details: LoggiFly runs on Docker, Docker Swarm and Podman
    icon: 🐳
    linkText: Learn More
    link: /guide/swarm


---

