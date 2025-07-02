# Notifications

You can send notifications either directly to **ntfy** or via **Apprise** to [most other  notification services](https://github.com/caronc/apprise/wiki). 

If you want the data to be sent to your own **custom endpoint** to integrate it into a custom workflow, you can set a custom webhook URL. LoggiFly will send all data in JSON format.

You can also set all three notification options at the same time.

::: code-group

```yaml [ntfy]
notifications:                       
  ntfy:
    url: http://your-ntfy-server    # Required. The URL of your ntfy instance
    topic: loggifly.                # Required. the topic for ntfy
    token: ntfy-token               # ntfy token in case you need authentication 
    username: john                  # ntfy Username + Password in case you need authentication 
    password: password              # ntfy Username + Password in case you need authentication 
    priority: 3                     # ntfy priority (1-5)
    tags: kite,mag                  # ntfy tags/emojis 
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

::: details Webhook JSON Structure

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
:::