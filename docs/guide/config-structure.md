---
title: Config Structure
---

# Config Structure

The `config.yaml` file is divided into four main sections:

1. [**`settings`**](./config_sections/settings): Global settings for the whole program (_Optional since they all have default values_)
2. [**`notifications`**](./config_sections/notifications): Ntfy (_URL, Topic, Token, Priority and Tags_), your Apprise URL and/or a custom webhook url 
3. [**`containers`**](./config_sections/containers): Define which Containers to monitor and their specific Keywords (_plus optional settings_).
4. [**`global_keywords`**](./config_sections/global-keywords): Keywords that apply to _all_ monitored Containers.


> [!IMPORTANT]
For the program to function you need to configure:
>- **at least one container**
>- **at least one notification service (Ntfy, Apprise or custom webhook)**
>- **at least one keyword / regex pattern (either set globally or per container)**
>
>  The rest is optional or has default values.

## Config Template

Here is an example config. This file automatically gets downloaded into your mounted `/config` directory. 
::: details Config Template

<<< @/configs/config_template.yaml{yaml}

:::


## Config Example

Here is an example config with some real use cases. 
::: details Config Example with Use Cases

<<< @/configs/config_example.yaml{yaml}

:::

::: info
Feel free to contribute your use cases to [the file](https://github.com/clemcer/loggifly/blob/main/docs/configs/config_example.yaml).
:::