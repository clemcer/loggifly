
from pydantic import (
    BaseModel,
    Field,
    field_validator,
    model_validator,
    ConfigDict,
    SecretStr,
    ValidationError   
)
from typing import Dict, List, Optional, Union
import os
import logging
import yaml

logging.getLogger(__name__)

""" 
this may look unnecessarily complicated but I wanted to learn and use pydantic 
I didn't manage to use pydantic's integrated environment variable loading
because I needed env to override yaml data and yaml to override default values and I could not get it to work.
So now I first load the yaml config and the environment variables, merge them and then I validate the merged config with pydantic
"""




class BaseConfigModel(BaseModel):
    model_config = ConfigDict(extra="ignore", validate_default=True)



class Settings(BaseConfigModel):    
    log_level: str = Field("INFO", description="Logging level (DEBUG, INFO, WARNING, ERROR)")
    notification_cooldown: int = Field(5, description="Cooldown in seconds for repeated alerts")
    notification_title: str = Field("default", description="Set a template for the notification title")
    action_cooldown: Optional[int] = Field(300)
    attachment_lines: int = Field(20, description="Number of log lines to include in attachments")
    multi_line_entries: bool = Field(True, description="Enable multi-line log detection")
    disable_start_message: bool = Field(False, description="Disable startup notification")
    disable_shutdown_message: bool = Field(False, description="Disable shutdown notification")
    disable_config_reload_message: bool = Field(False, description="Disable config reload notification")
    disable_container_event_message: bool = Field(False, description="Disable notification on container stops/starts")
    reload_config: bool = Field(True, description="Disable config reaload on config change")


class ModularSettings(BaseConfigModel):
    ntfy_tags: Optional[str] = None
    ntfy_topic: Optional[str] = None
    ntfy_priority: Optional[int] = None
    attachment_lines: Optional[int] = None
    notification_cooldown: Optional[int] = None
    notification_title: Optional[str] = None
    hide_pattern_in_title: Optional[bool] = None
    action_cooldown: Optional[int] = None
    attach_logfile: Optional[bool] = None

class RegexItem(ModularSettings):
    regex: str
    json_template: Optional[str] = None
    template: Optional[str] = None

class KeywordItem(ModularSettings):
    keyword: str
    json_template: Optional[str] = None


class KeywordBase(BaseModel):
    keywords: List[Union[str, KeywordItem, RegexItem]] = []
    keywords_with_attachment: List[Union[str, KeywordItem, RegexItem]] = []

    # for sorting out misconfigured keywords, providing warnings and converting integers to strings (before validation)
    @model_validator(mode="before")
    def int_to_string(cls, values):
        for field in ["keywords", "keywords_with_attachment"]:
            if field in values and isinstance(values[field], list):
                converted = []
                for kw in values[field]:
                    if isinstance(kw, dict):
                        keys = list(kw.keys())
                        # if "regex" in keys:
                        #     if any(key not in ["regex", "template", "json_template", "hide_pattern_in_title"] for key in keys):
                        #         logging.warning(f"Ignoring Error in config for {field}: '{kw}'. Only 'json_template', 'template' and 'hide_pattern_in_title' are allowed as additional keys for regex pattern.")
                        #         continue
                        # elif "keyword" in keys:
                        #     if any(key not in ["keyword", "json_template"] for key in keys):
                        #         logging.warning(f"Ignoring Error in config for {field}: '{kw}'. Only 'json_template' and 'hide_pattern_in_title' are allowed as additional keys for 'keyword'.")
                        #         continue
                        # else:
                        #     logging.warning(f"Ignoring Error in config for {field}: '{kw}'. Only 'keyword' or 'regex' are allowed as keys.")
                        #     continue
                        for key in keys:
                            if isinstance(kw[key], int):
                                kw[key] = str(kw[key])
                        converted.append(kw)
                    else:
                        try:
                            converted.append(str(kw))
                        except ValueError:
                            logging.warning(f"Ignoring unexpected Error in config for {field}: '{kw}'.")
                            continue
                values[field] = converted
        return values
    
class ActionKeywords(BaseConfigModel):
    action_keywords: List[Union[str, Dict[str, Union[str, Dict[str, str]]]]] = []

    @field_validator("action_keywords", mode="before")
    def convert_int_to_str(cls, value):
        allowed_keys = {"restart", "stop"}
        converted = []
        for kw in value:
            if isinstance(kw, dict):
                if any(key not in allowed_keys for key in kw.keys()):
                    logging.warning(f"Ignoring Error in config for action_keywords: Key not allowed for restart_keywords. Wrong Input: '{kw}'. Allowed Keys: {allowed_keys}.")
                    continue
                for key, val in kw.items():
                    if not val:
                        logging.warning(f"Ignoring Error in config for action_keywords: Wrong Input: '{key}: {val}'.") 
                        continue
                    # convert Integer to String
                    if isinstance(val, int):
                        converted.append({key: str(val)})
                    elif isinstance(val, dict):
                        if val.get("regex"):
                            # Convert regex-value, if Integer
                            if isinstance(val["regex"], (int, str)):
                                converted.append({key: str(val["regex"])})
                            else:
                                logging.warning(f"Ignoring Error in config for action_keywords: Wrong Input: '{key}: {val}' regex keyword is not a valid value.")
                        else:
                            logging.warning(f"Ignoring Error in config for action_keywords: Wrong Input: '{key}: {val}'. If you put a dictionary after 'restart'/'stop' only 'regex' is allowed as a key.") 
                    else:
                        converted.append({key: val})
            else:
                logging.warning(f"Ignoring Error in config for action_keywords: Wrong Input: '{kw}'. You have to set a dictionary with 'restart' or 'stop' as key.")
        return converted
    

class ContainerConfig(KeywordBase, ActionKeywords, ModularSettings):    
    pass 

    @field_validator("ntfy_priority")
    def validate_priority(cls, v):
        if isinstance(v, str):
            try:
                v = int(v)
            except ValueError:
                pass
        if isinstance(v, int):
            if not 1 <= int(v) <= 5:
                logging.warning(f"Error in config for ntfy_priority. Must be between 1-5, '{v}' is not allowed. Using default: '3'")
                return 3
        if isinstance(v, str):
            options = ["max", "urgent", "high", "default", "low", "min"]
            if v not in options:
                logging.warning(f"Error in config for ntfy_priority:'{v}'. Only 'max', 'urgent', 'high', 'default', 'low', 'min' are allowed. Using default: '3'")
                return 3
        return v
    
class GlobalKeywords(BaseConfigModel, KeywordBase):
    pass

class NtfyConfig(BaseConfigModel):
    url: str = Field(..., description="Ntfy server URL")
    topic: str = Field(..., description="Ntfy topic name")
    token: Optional[SecretStr] = Field(default=None, description="Optional access token")
    username: Optional[str] = Field(default=None, description="Optional username")
    password: Optional[SecretStr] = Field(default=None, description="Optional password")
    priority: Union[str, int] = 3 # Field(default=3, description="Message priority 1-5")
    tags: Optional[str] = Field("kite,mag", description="Comma-separated tags")

    @field_validator("priority", mode="before")
    def validate_priority(cls, v):
        if isinstance(v, str):
            try:
                v = int(v)
            except ValueError:
                pass
        if isinstance(v, int):
            if not 1 <= int(v) <= 5:
                logging.warning(f"Error in config for ntfy.priority. Must be between 1-5, '{v}' is not allowed. Using default: '3'")
                return 3
        if isinstance(v, str):
            options = ["max", "urgent", "high", "default", "low", "min"]
            if v not in options:
                logging.warning(f"Error in config for ntfy.priority:'{v}'. Only 'max', 'urgent', 'high', 'default', 'low', 'min' are allowed. Using default: '3'")
                return 3
        return v

class AppriseConfig(BaseConfigModel):  
    url: SecretStr = Field(..., description="Apprise compatible URL")

class WebhookConfig(BaseConfigModel):
    url: str
    headers: Optional[dict] = Field(default=None)

class NotificationsConfig(BaseConfigModel):
    ntfy: Optional[NtfyConfig] = Field(default=None, validate_default=False)
    apprise: Optional[AppriseConfig] = Field(default=None, validate_default=False)
    webhook: Optional[WebhookConfig] = Field(default=None, validate_default=False)

    @model_validator(mode="after")
    def check_at_least_one(self) -> "NotificationsConfig":
        if self.ntfy is None and self.apprise is None and self.webhook is None:
            raise ValueError("At least on of these has to be configured: 'apprise' / 'ntfy' / 'webhook'")
        return self


class GlobalConfig(BaseConfigModel):
    containers: Optional[Dict[str, ContainerConfig]] = Field(default=None)
    swarm_services: Optional[Dict[str, ContainerConfig]] = Field(default=None)
    global_keywords: GlobalKeywords
    notifications: NotificationsConfig
    settings: Settings

    @model_validator(mode="before")
    def transform_legacy_format(cls, values):
        # Convert list global_keywords format into dict
        if isinstance(values.get("global_keywords"), list):
            values["global_keywords"] = {
                "keywords": values["global_keywords"],
                "keywords_with_attachment": []
            }
        # Convert list containers to dict format
        if isinstance(values.get("containers"), list):
            values["containers"] = {
                name: {} for name in values["containers"]
            }
         # Convert list keywords format per container into dict
        for container in values.get("containers"):
            if isinstance(values.get("containers").get(container), list):
                values["containers"][container] = {
                    "keywords": values["containers"][container],
                    "keywords_with_attachment": []
                }
            elif values.get("containers").get(container) is None:
                values["containers"][container] = {
                    "keywords": [],
                    "keywords_with_attachment": []
                }
        return values
    
    @model_validator(mode="after")
    def check_at_least_one(self) -> "GlobalConfig":
        tmp_list = self.global_keywords.keywords + self.global_keywords.keywords_with_attachment
        if not tmp_list:
            for k in self.containers:
                tmp_list.extend(self.containers[k].keywords)
        if not tmp_list:
            raise ValueError("No keywords configured. You have to set keywords either per container or globally.")
        if not self.containers and not self.swarm_services:
            raise ValueError("You have to configure at least one container")
        return self
    

def format_pydantic_error(e: ValidationError) -> str:
    error_messages = []
    for error in e.errors():
        location = ".".join(map(str, error["loc"]))
        msg = error["msg"]
        msg = msg = msg.split("[")[0].strip()
        error_messages.append(f"Field '{location}': {msg}")
    return "\n".join(error_messages)


def mask_secret_str(data):
    if isinstance(data, dict):
        return {k: mask_secret_str(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [mask_secret_str(item) for item in data]
    elif isinstance(data, SecretStr):
        return "**********"  
    else:
        return data


def merge_yaml_and_env(yaml, env_update):
    for key, value in env_update.items():
        if isinstance(value, dict) and key in yaml and key != {}:
            merge_yaml_and_env(yaml[key],value)
        else:
            if value is not None :
                yaml[key] = value
    return yaml


def load_config(official_path="/config/config.yaml"):
    """
    Load the configuration from a YAML file and environment variables.
    The config.yaml is expected in /config/config.yaml or /app/config.yaml (older version)
    """
    config_path = None
    required_keys = ["containers", "notifications", "settings", "global_keywords"]
    yaml_config = None
    legacy_path = "/app/config.yaml"
    paths = [official_path, legacy_path]
    for path in paths: 
        logging.info(f"Trying path: {path}")
        if os.path.isfile(path):
            try:
                with open(path, "r") as file:
                    yaml_config = yaml.safe_load(file)
                    config_path = path
                    break
            except FileNotFoundError:
                logging.info(f"Error loading the config.yaml file from {path}")
            except yaml.YAMLError as e:
                logging.error(f"Error parsing the YAML file: {e}")
            except Exception as e:
                logging.error(f"Unexpected error loading the config.yaml file: {e}")
        else:
            logging.info(f"The path {path} does not exist.")

    if yaml_config is None:
        logging.warning(f"The config.yaml could not be loaded.")
        yaml_config = {}
    else:
        logging.info(f"The config.yaml file was found in {path}.")

    for key in required_keys:
        if key not in yaml_config or yaml_config[key] is None:
            yaml_config[key] = {}
    """
    -------------------------LOAD ENVIRONMENT VARIABLES---------------------
    """
    env_config = { "notifications": {}, "settings": {}, "global_keywords": {}, "containers": {}}
    settings_values = {
        "log_level": os.getenv("LOG_LEVEL"),
        "attachment_lines": os.getenv("ATTACHMENT_LINES"),
        "multi_line_entries": os.getenv("MULTI_LINE_ENTRIES"),
        "notification_cooldown": os.getenv("NOTIFICATION_COOLDOWN"),
        "notification_title": os.getenv("NOTIFICATION_TITLE"),
        "reload_config": False if config_path is None else os.getenv("RELOAD_CONFIG"), 
        "disable_start_message": os.getenv("DISABLE_START_MESSAGE"),
        "disable_restart_message": os.getenv("DISABLE_CONFIG_RELOAD_MESSAGE"),
        "disable_shutdown_message": os.getenv("DISABLE_SHUTDOWN_MESSAGE"),
        "disable_container_event_message": os.getenv("DISABLE_CONTAINER_EVENT_MESSAGE"),
        "action_cooldown": os.getenv("ACTION_COOLDOWN")
        } 
    ntfy_values =  {
        "url": os.getenv("NTFY_URL"),
        "topic": os.getenv("NTFY_TOPIC"),
        "token": os.getenv("NTFY_TOKEN"),
        "priority": os.getenv("NTFY_PRIORITY"),
        "tags": os.getenv("NTFY_TAGS"),
        "username": os.getenv("NTFY_USERNAME"),
        "password": os.getenv("NTFY_PASSWORD")
        }
    webhook_values = {
        "url": os.getenv("WEBHOOK_URL"),
        "headers":os.getenv("WEBHOOK_HEADERS")
    }
    apprise_values = {
        "url": os.getenv("APPRISE_URL")
    }
    global_keywords_values = {
        "keywords": [kw.strip() for kw in os.getenv("GLOBAL_KEYWORDS", "").split(",") if kw.strip()] if os.getenv("GLOBAL_KEYWORDS") else [],
        "keywords_with_attachment": [kw.strip() for kw in os.getenv("GLOBAL_KEYWORDS_WITH_ATTACHMENT", "").split(",") if kw.strip()] if os.getenv("GLOBAL_KEYWORDS_WITH_ATTACHMENT") else [],
    }
    # Fill env_config dict with environment variables if they are set
    if os.getenv("CONTAINERS"):
        for c in os.getenv("CONTAINERS", "").split(","):
            c = c.strip()
            env_config["containers"][c] = {}

    if os.getenv("SWARM_SERVICES"):
        env_config["swarm_services"] = {}
        for s in os.getenv("SWARM_SERVICES", "").split(","):
            s = s.strip()
            env_config["swarm_services"][s] = {}

    if any(ntfy_values.values()):
        env_config["notifications"]["ntfy"] = ntfy_values
        yaml_config["notifications"]["ntfy"] = {} if yaml_config["notifications"].get("ntfy") is None else yaml_config["notifications"]["ntfy"]
    if apprise_values["url"]: 
        env_config["notifications"]["apprise"] = apprise_values
        yaml_config["notifications"]["apprise"] = {} if yaml_config["notifications"].get("apprise") is None else yaml_config["notifications"]["apprise"]
    if webhook_values.get("url"):
        env_config["notifications"]["webhook"] = webhook_values
        yaml_config["notifications"]["webhook"] = {} if yaml_config["notifications"].get("webhook") is None else yaml_config["notifications"]["webhook"]

    for k, v in global_keywords_values.items():
        if v:
            env_config["global_keywords"][k]= v
    for key, value in settings_values.items(): 
        if value is not None:
            env_config["settings"][key] = value
    # Merge environment variables and yaml config
    merged_config = merge_yaml_and_env(yaml_config, env_config)
    # Validate the merged configuration with Pydantic
    config = GlobalConfig.model_validate(merged_config)

    config_dict = mask_secret_str(config.model_dump(exclude_none=True, exclude_defaults=False, exclude_unset=False))
    yaml_output = yaml.dump(config_dict, default_flow_style=False, sort_keys=False, indent=4)
    logging.info(f"\n ------------- CONFIG ------------- \n{yaml_output}\n ----------------------------------")

    return config, config_path

