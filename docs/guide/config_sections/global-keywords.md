
# Global Keywords

`global_keywords` are monitored on all containers. 

Keywords/regexes under `global_keywords` can also be configured with additional settings as described in the [containers](#-containers) section. For an overview of all the possible settings refer to this [table](#-settings-overview--hierarchy-explained).
 

```yaml
global_keywords:              
  keywords:
    - login failed
    - regex: "critical"
      action: stop
    - keyword: "error"
      attach_logfile: true
```
