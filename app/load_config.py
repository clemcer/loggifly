
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
I didn't manage to use pydantic with environment variables the way I wanted. 
I needed env to override yaml data and yaml to override default values and I could not get it to work 
so now I first load the yaml and the environment variables, merge them and then I validate the data with pydantic
"""

class BaseConfigModel(BaseModel):
    model_config = ConfigDict(extra="ignore", validate_default=True)

class KeywordBase(BaseModel):
    keywords: List[Union[str, Dict[str, str]]] = []
    keywords_with_attachment: List[Union[str, Dict[str, str]]] = []

    @model_validator(mode="before")
    def int_to_string(cls, values):
        for field in ["keywords", "keywords_with_attachment"]:
            if field in values and isinstance(values[field], list):
                converted = []
                for kw in values[field]:
                    if isinstance(kw, dict):
                        keys = list(kw.keys())
                        if len(keys) == 1 and keys[0] == "regex":
                            if isinstance(kw["regex"], (str, int)):
                                converted.append({keys[0]: str(kw["regex"])})
                        else:
                            logging.warning(f"Ignoring Error in config for {field}: '{kw}'. Only 'regex' is allowed as a key.")
                            continue
                    else:
                        try:
                            converted.append(str(kw))
                        except ValueError:
                            continue
                values[field] = converted
        return values
    
class ActionKeywords(BaseModel):
    action_keywords: List[Union[str, Dict[str, Union[str, Dict[str, str]]]]] = []

    @field_validator("action_keywords", mode="before")
    def convert_int_to_str(cls, value):
        allowed_keys = {"restart", "stop"}
        converted = []
        for item in value:
            if isinstance(item, dict):
                for key, val in item.items():
                    if key not in allowed_keys:
                        logging.warning(f"Ignoring Error in config for action_keywords: Key not allowed for restart_keywords. Wrong Input: '{key}: {val}'. Allowed Keys: {allowed_keys}.")
                        continue  
                    # convert Integer zu String
                    if isinstance(val, int):
                        converted.append({key: str(val)})
                    elif isinstance(val, dict):
                        if "regex" in val:
                            # Convert regex-value, if Integer
                            regex_val = val["regex"]
                            if isinstance(regex_val, (int, str)):
                                val["regex"] = str(regex_val)
                            else:
                                logging.warning(f"Ignoring Error in config for action_keywords: Wrong Input: '{key}: {val}' regex keyword is not a valid value.")
                                continue
                            converted.append({key: val})
                        else:
                            logging.warning(f"Ignoring Error in config for action_keywords: Wrong Input: '{key}: {val}'. If you put a dictionary after 'restart'/'stop' only 'regex' is allowed as a key.") 
                    else:
                        converted.append({key: val})
            else:
                logging.warning(f"Ignoring Error in config for action_keywords: Wrong Input: '{item}'. You have to set a dictionary with 'restart' or 'stop' as key.")
        return converted
    

class ContainerConfig(BaseConfigModel, KeywordBase, ActionKeywords):    
    ntfy_tags: Optional[str] = None
    ntfy_topic: Optional[str] = None
    ntfy_priority: Optional[int] = None
    attachment_lines: Optional[int] = None
    notification_cooldown: Optional[int] = None
    action_cooldown: Optional[int] = None

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

class NotificationsConfig(BaseConfigModel):
    ntfy: Optional[NtfyConfig] = Field(default=None, validate_default=False)
    apprise: Optional[AppriseConfig] = Field(default=None, validate_default=False)

    @model_validator(mode="after")
    def check_at_least_one(self) -> "NotificationsConfig":
        if self.ntfy is None and self.apprise is None:
            raise ValueError("At least on of these two Apprise / Ntfy has to be configured.")
        return self

class Settings(BaseConfigModel):    
    log_level: str = Field("INFO", description="Logging level (DEBUG, INFO, WARNING, ERROR)")
    notification_cooldown: int = Field(5, description="Cooldown in seconds for repeated alerts")
    action_cooldown: Optional[int] = Field(300)
    attachment_lines: int = Field(20, description="Number of log lines to include in attachments")
    multi_line_entries: bool = Field(True, description="Enable multi-line log detection")
    disable_start_message: bool = Field(False, description="Disable startup notification")
    disable_shutdown_message: bool = Field(False, description="Disable shutdown notification")
    disable_config_reload_message: bool = Field(False, description="Disable config reload notification")
    reload_config: bool = Field(True, description="Disable restart on config change")

class GlobalConfig(BaseConfigModel):
    containers: Dict[str, ContainerConfig]
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
        tmp_list = []
        if not self.global_keywords.keywords and not self.global_keywords.keywords_with_attachment:
            for k in self.containers:
                tmp_list.extend(self.containers[k].keywords)
        else:
            return self
        if not tmp_list:
            raise ValueError("No keywords configured. You have to set keywords either per container or globally.")
        return self

    @field_validator("containers")
    def validate_priority(cls, v):
        if isinstance(v, dict):
            if not v:
                raise ValueError(f"You have to configure at least one container")
        return v


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
        return "*****"  
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


def load_config(path="/app/config.yaml"):
    required_keys = ["containers", "notifications", "settings", "global_keywords"]
    yaml_config = {}
    if os.path.isfile(path):
        try:
            with open(path, "r") as file:
                yaml_config = yaml.safe_load(file)
                logging.info(f"YAML CONFIG: {yaml_config}")
                logging.info("config.yaml succesfully loaded.")
                no_config_file = False
        except FileNotFoundError:
            logging.warning("config.yaml not found. Only using environment variables.")
            no_config_file = True
    else:
        logging.warning("config.yaml not found. Only using environment variables.")
        no_config_file = True

    if yaml_config is None:
        yaml_config = {}
    for key in required_keys:
        yaml_config.setdefault(key, {})
    """
    -------------------------LOAD ENVIRONMENT VARIABLES---------------------
    """
    env_config = { "notifications": {}, "settings": {}, "global_keywords": {}, "containers": {}}
    settings_values = {
        "log_level": os.getenv("LOG_LEVEL"),
        "attachment_lines": os.getenv("ATTACHMENT_LINES"),
        "multi_line_entries": os.getenv("MULTI_LINE_ENTRIES"),
        "notification_cooldown": os.getenv("NOTIFICATION_COOLDOWN"),
        "reload_config": False if no_config_file is True else os.getenv("DISABLE_RESTART"),
        "disable_start_message": os.getenv("DISABLE_START_MESSAGE"),
        "disable_restart_message": os.getenv("DISABLE_CONFIG_RELOAD_MESSAGE"),
        "disable_shutdown_message": os.getenv("DISABLE_SHUTDOWN_MESSAGE"),
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
    apprise_values = {
        "url": os.getenv("APPRISE_URL")
    }
    global_keywords_values = {
        "keywords": [kw.strip() for kw in os.getenv("GLOBAL_KEYWORDS", "").split(",") if kw.strip()] if os.getenv("GLOBAL_KEYWORDS") else [],
        "keywords_with_attachment": [kw.strip() for kw in os.getenv("GLOBAL_KEYWORDS_WITH_ATTACHMENT", "").split(",") if kw.strip()] if os.getenv("GLOBAL_KEYWORDS_WITH_ATTACHMENT") else [],
    }
    if os.getenv("CONTAINERS"):
        for c in os.getenv("CONTAINERS", "").split(","):
            c = c.strip()
            env_config["containers"][c] = {}
    if any(ntfy_values.values()):
        env_config["notifications"] = {}
        env_config["notifications"]["ntfy"] = ntfy_values
        yaml_config["notifications"]["ntfy"] = {}
    if apprise_values["url"]: 
        env_config["notifications"] = {}
        env_config["notifications"]["apprise"] = apprise_values
        yaml_config["notifications"]["apprise"] = {}
    for k, v in global_keywords_values.items():
        if v:
            env_config["global_keywords"][k]= v
    for key, value in settings_values.items(): 
        if value is not None:
            env_config["settings"][key] = value
    merged_config = merge_yaml_and_env(yaml_config, env_config)
    config = GlobalConfig.model_validate(merged_config)
    config_dict = mask_secret_str(config.model_dump(exclude_none=True, exclude_defaults=False, exclude_unset=False))
    yaml_output = yaml.dump(config_dict, default_flow_style=False, sort_keys=False, indent=4)
    logging.info(f"\n ------------- CONFIG ------------- \n{yaml_output}\n ----------------------------------")

   # logging.info(f"\n ------------- CONFIG ------------- \n{config.model_dump_json(indent=2, exclude_none=True)}\n ----------------------------------")
    return config

