---
title: json_template
---

# Formatting JSON Logs

## Template for JSON Logs:

With the setting `json_template` you can filter the log entry for certain parts. 
This only works if the logs are in JSON Format. Authelia is one such example.<br>
In your template you can insert keys from the JSON log entry you want to catch.<br>

Here is an example where you want to catch this very long log entry from Authelia: 

```json
{"level":"error","method":"POST","msg":"Unsuccessful 1FA authentication attempt by user 'example_user' and they are banned until 12:23:00PM on May 1 2025 (+02:00)","path":"/api/firstfactor","remote_ip":"192.168.178.191","stack":[{"File":"github.com/authelia/authelia/v4/internal/handlers/response.go","Line":274,"Name":"doMarkAuthenticationAttemptWithRequest"},{"File":"github.com/authelia/authelia/v4/internal/handlers/response.go","Line":258,"Name":"doMarkAuthenticationAttempt"},{"File":"github.com/authelia/authelia/v4/internal/handlers/handler_firstfactor_password.go","Line":51,"Name":"handlerMain.FirstFactorPasswordPOST.func14"},{"File":"github.com/authelia/authelia/v4/internal/middlewares/bridge.go","Line":66,"Name":"handlerMain.(*BridgeBuilder).Build.func7.1"},{"File":"github.com/authelia/authelia/v4/internal/middlewares/headers.go","Line":65,"Name":"SecurityHeadersCSPNone.func1"},{"File":"github.com/authelia/authelia/v4/internal/middlewares/headers.go","Line":105,"Name":"SecurityHeadersNoStore.func1"},{"File":"github.com/authelia/authelia/v4/internal/middlewares/headers.go","Line":30,"Name":"SecurityHeadersBase.func1"},{"File":"github.com/fasthttp/router@v1.5.4/router.go","Line":441,"Name":"(*Router).Handler"},{"File":"github.com/authelia/authelia/v4/internal/middlewares/log_request.go","Line":14,"Name":"handlerMain.LogRequest.func31"},{"File":"github.com/authelia/authelia/v4/internal/middlewares/errors.go","Line":38,"Name":"RecoverPanic.func1"},{"File":"github.com/valyala/fasthttp@v1.59.0/server.go","Line":2380,"Name":"(*Server).serveConn"},{"File":"github.com/valyala/fasthttp@v1.59.0/workerpool.go","Line":225,"Name":"(*workerPool).workerFunc"},{"File":"github.com/valyala/fasthttp@v1.59.0/workerpool.go","Line":197,"Name":"(*workerPool).getCh.func1"},{"File":"runtime/asm_amd64.s","Line":1700,"Name":"goexit"}],"time":"2025-05-01T14:19:29+02:00"}
```

In the config.yaml you can set a `json_template` for both plain text keywords and regex patterns.<br>
In this template I inserted three keys from the JSON Log Entry:

```yaml
containers:
  authelia:
    keywords:
      - keyword: Unsuccessful 1FA authentication
        json_template: '🚨 Failed Login Attempt:\n{msg}\n🔎 IP: {remote_ip}\n🕐{time}' 
      - regex: Unsuccessful.*authentication
        json_template: '🚨 Failed Login Attempt:\n{msg}\n🔎 IP: {remote_ip}\n🕐{time}' 
```

---

::: tip
You can add the key `original_log_line` to your template to add the full log entry to your notification message.
:::

## Nested JSON Structures

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
json_template: 'User {user[name]} logged in from {location[city]}, Role: {user[roles][0][name]}'

```

Output:

```
User admin logged in from Berlin, Role: superuser
```

