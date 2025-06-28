---
title: template
---

# Format Notifications from plain text log lines

## Regex with named capturing groups

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
        hide_regex_in_title: true  # Exclude the regex pattern from the notification title for a cleaner look
      
```

**Result:**

Normal notification and notification With `template` and `hide_regex_in_title`:

![Template Comparison](/template_comparison.png)
