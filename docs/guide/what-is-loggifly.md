---
title: What is LoggiFly
---

# What is LoggiFly 

LoggiFly is a small, open-source tool that watches container logs and sends notifications when specific keywords or patterns appear. It helps you catch problems early, like crashes, errors, or anything else you care about, without having to set up a full logging stack.
LoggiFly can also be used to get notifications from apps that don't have good notification support. 

::: details Screenshots
![Collage of Screenshots](/collage.png)

### Customize notifications and filter log lines for relevant information

![Custom Templates Collage](/template_collage.png)
:::


LoggiFly runs as a very lightweight container and connects directly to the Docker (or Podman) Socket. You can send alerts to ntfy or via Apprise to most other notification servives (like Discord, Slack, or Telegram). LoggiFly can also restart containers automatically, attach log files to your notifications, format messages by extracting only the relevant informstion and more.

It supports both simple setups via environment variables and advanced configuration via a config.yaml file, giving you full control over alerts per container and even per keyword.

LoggiFly is easy to deploy, flexible, and made for people who want to monitor containers without extra complexity.

**Ideal For**:
- ✅ Catching security breaches (e.g., failed logins in Vaultwarden)
- ✅ Debugging crashes with attached log context
- ✅ Restarting containers on specific errors or stopping them completely to avoid restart loops
- ✅ Monitoring custom app behaviors (e.g., failed logins or when a user downloads an audiobook on your Audiobookshelf server)
