
from pydantic import (
    BaseModel,
    Field,
    field_validator,
    model_validator,
    ConfigDict,
    SecretStr,
    ValidationError
)
from enum import Enum
from typing import Dict, List, Optional, Union
import os
import logging
import copy
import yaml

logging.getLogger(__name__)

""" 
this may look unnecessarily complicated but I wanted to learn and use pydantic 
I didn't manage to use pydantic's integrated environment variable loading
because I needed env to override yaml data and yaml to override default values and I could not get it to work.
So now I first load the yaml config and the environment variables, merge them and then I validate the merged config with pydantic
"""

def validate_priority(v):
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

class BaseConfigModel(BaseModel):
    model_config = ConfigDict(extra="ignore", validate_default=True, use_enum_values=True)

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
    action_cooldown: Optional[int] = None
    attach_logfile: Optional[bool] = None

class ActionEnum(str, Enum):
    RESTART = "restart"
    STOP = "stop"

class RegexItem(ModularSettings):
    regex: str
    json_template: Optional[str] = None
    template: Optional[str] = None
    hide_pattern_in_title: Optional[bool] = None
    action: Optional[ActionEnum] = None

class KeywordItem(ModularSettings):
    keyword: str
    json_template: Optional[str] = None
    action: Optional[ActionEnum] = None


class KeywordBase(BaseModel):
    keywords: List[Union[str, KeywordItem, RegexItem]] = []
   # keywords_with_attachment: List[Union[str, KeywordItem, RegexItem]] = []

    # for sorting out misconfigured keywords, providing warnings and converting integers to strings (before validation)
    @model_validator(mode="before")
    def int_to_string(cls, values):
        for field in ["keywords", "keywords_with_attachment"]:
            if field in values and isinstance(values[field], list):
                converted = []
                for kw in values[field]:
                    if isinstance(kw, dict):
                        keys = list(kw.keys())
                        if not any(key in keys for key in ["keyword", "regex"]):
                            logging.warning(f"Ignoring Error in config for {field}: '{kw}'. You have to set 'keyword' or 'regex' as a key.")
                            continue
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
    
class ContainerConfig(KeywordBase, ModularSettings):    
    pass 

    _validate_priority = field_validator("ntfy_priority", mode="before")(validate_priority)
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

    _validate_priority = field_validator("priority", mode="before")(validate_priority)

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
        # Convert list containers to dict format
        if isinstance(values.get("containers"), list):
            values["containers"] = {name: {} for name in values["containers"]}

        return values
    
    @model_validator(mode="after")
    def check_at_least_one(self) -> "GlobalConfig":
        tmp_list = self.global_keywords.keywords #+ self.global_keywords.keywords_with_attachment
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


def load_env_config(config_path=None): 
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
    if apprise_values["url"]: 
        env_config["notifications"]["apprise"] = apprise_values
    if webhook_values.get("url"):
        env_config["notifications"]["webhook"] = webhook_values

    for k, v in global_keywords_values.items():
        if v:
            env_config["global_keywords"][k]= v

    for key, value in settings_values.items(): 
        if value is not None:
            env_config["settings"][key] = value
    return env_config

def convert_legacy_formats(config):
    config_copy = copy.deepcopy(config)
    global_with_attachment = config_copy.get("global_keywords").get("keywords_with_attachment") 
    if global_with_attachment is not None:
        config_copy["global_keywords"].setdefault("keywords", [])
        print("TEST")
        for kw in global_with_attachment:
            if isinstance(kw, (str, int)):
                config_copy["global_keywords"]["keywords"].append({"keyword": kw, "attach_logfile": True})
            if isinstance(kw, dict):
                kw["attach_logfile"] = True
                config_copy["global_keywords"]["keywords"].append(kw)
        del config_copy["global_keywords"]["keywords_with_attachment"]

    for container in config_copy.get("containers", {}):
        container_config = config_copy["containers"][container]
        keywords_with_attachment = container_config.get("keywords_with_attachment")
        action_keywords = container_config.get("action_keywords")
        if keywords_with_attachment is not None:
            container_config.setdefault("keywords", [])
            for kw in keywords_with_attachment:
                if isinstance(kw, (str, int)):
                    container_config["keywords"].append({"keyword": kw, "attach_logfile": True})
                if isinstance(kw, dict):
                    kw["attach_logfile"] = True
                    container_config["keywords"].append(kw)
        # if action_keywords is not None:
        #     del container_config["keywords_with_attachment"]

    print(f"CONVERTED (FUNCTION): {config}")
    return config_copy


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

    env_config = load_env_config(config_path)

    # Merge environment variables and yaml config
    merged_config = merge_yaml_and_env(yaml_config, env_config)
    print(f"MERGED: {merged_config}\n\n")
    merged_config = convert_legacy_formats(merged_config)
    print(f"CONVERTED: {merged_config}\n\n")
    # Validate the merged configuration with Pydantic
    config = GlobalConfig.model_validate(merged_config)

    config_dict = mask_secret_str(config.model_dump(exclude_none=True, exclude_defaults=False, exclude_unset=False))
    yaml_output = yaml.dump(config_dict, default_flow_style=False, sort_keys=False, indent=4)
    logging.info(f"\n ------------- CONFIG ------------- \n{yaml_output}\n ----------------------------------")

    return config, config_path

