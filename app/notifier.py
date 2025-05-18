import requests
import base64
import logging
import urllib.parse
from load_config import GlobalConfig

logging.getLogger(__name__)

def get_ntfy_config(config, container_name, message_config):

    ntfy_config = {"topic": None, "tags": None, "priority": None}
    global_config = config.notifications.ntfy.model_dump(exclude_none=True)
    if container_name in config.containers and getattr(config.containers[container_name], "ntfy", None):
        container_config = config.containers[container_name].ntfy.model_dump(exclude_none=True) 
    else:
        container_config = {}
    message_config = message_config if message_config else {}
    for key in ntfy_config.keys():
        if message_config.get(key) is not None:
            ntfy_config[key] = message_config.get(key)
        elif container_config.get(key) is not None:
            ntfy_config[key] = container_config.get(key)
        elif global_config.get(key) is not None:
            ntfy_config[key] = global_config.get(key)

    ntfy_config["url"] = config.notifications.ntfy.url

    if config.notifications.ntfy.token:
        ntfy_config["authorization"] = f"Bearer {config.notifications.ntfy.token.get_secret_value()}"
    elif config.notifications.ntfy.username and config.notifications.ntfy.password:
        credentials = f"{config.notifications.ntfy.username}:{config.notifications.ntfy.password.get_secret_value()}"
        encoded_credentials = base64.b64encode(credentials.encode('utf-8')).decode('utf-8')
        ntfy_config["authorization"] = f"Basic {encoded_credentials}"
    return ntfy_config


def send_apprise_notification(url, message, title, file_path=None):
    apobj = apprise.Apprise()
    apobj.add(url)
    message = ("This message had to be shortened: \n" if len(message) > 1900 else "") + message[:1900]
    try: 
        if file_path is None:
            apobj.notify(
                title=title,
                body=message,
            )
        else:
            apobj.notify(
                title=title,
                body=message,
                attach=file_path
            )
        logging.info("Apprise-Notification sent successfully")
    except Exception as e:
        logging.error("Error while trying to send apprise-notification: %s", e)


def send_ntfy_notification(ntfy_config, message, title, file_path=None):
    message = ("This message had to be shortened: \n" if len(message) > 3900 else "") + message[:3900]
    headers = {
        "Title": title,
        "Tags": f"{ntfy_config['tags']}",
        "Icon": "https://raw.githubusercontent.com/clemcer/loggifly/main/images/icon.png",
        "Priority": f"{ntfy_config['priority']}"
        }
    if ntfy_config.get('authorization'):
        headers["Authorization"] = f"{ntfy_config.get('authorization')}"

    try:
        if file_path:
            file_name = file_path.split("/")[-1]
            headers["Filename"] = file_name
            with open(file_path, "rb") as file:
                if len(message) < 199:
                    response = requests.post(
                        f"{ntfy_config['url']}/{ntfy_config['topic']}?message={urllib.parse.quote(message)}",
                        data=file,
                        headers=headers
                    )
                else:
                    response = requests.post(
                        f"{ntfy_config['url']}/{ntfy_config['topic']}",
                        data=file,
                        headers=headers
                    )
        else:
            response = requests.post(
                f"{ntfy_config['url']}/{ntfy_config['topic']}", 
                data=message,
                headers=headers
            )
        if response.status_code == 200:
            logging.info("Ntfy-Notification sent successfully")
        else:
            logging.error("Error while trying to send ntfy-notification: %s", response.text)
    except requests.RequestException as e:
        logging.error("Error while trying to connect to ntfy: %s", e)


def send_webhook(json_data, url, headers):
    try: 
        response = requests.post(
            url=url,
            headers=headers,
            json=json_data,
            timeout=10
            )
        if response.status_code == 200:
            logging.info(f"Webhook sent successfully.")
            #logging.debug(f"Webhook Response: {json.dumps(response.json(), indent=2)}")
        else:
            logging.error("Error while trying to send POST request to custom webhook: %s", response.text)
    except requests.RequestException as e:
        logging.error(f"Error trying to send webhook to url: {url}, headers: {headers}: %s", e)


def send_notification(config: GlobalConfig, container_name, title=None, message=None, message_config=None, hostname=None, file_path=None):
    message = message.replace(r"\n", "\n").strip()
    # When multiple hosts are set the hostname is added to the title, when only one host is set the hostname is an empty string
    title = f"[{hostname}] - {title}" if hostname else title

    if (config.notifications and config.notifications.ntfy and config.notifications.ntfy.url and config.notifications.ntfy.topic):
        ntfy_config = get_ntfy_config(config, container_name, message_config)
        send_ntfy_notification(ntfy_config, message=message, title=title, file_path=file_path)

    if (config.notifications and config.notifications.apprise and config.notifications.apprise.url):
        apprise_url = config.notifications.apprise.url.get_secret_value()
        send_apprise_notification(apprise_url, message=message, title=title, file_path=file_path)

    if (config.notifications and config.notifications.webhook and config.notifications.webhook.url):
        keywords = message_config.get("keywords_found", None)
        json_data = {"container": container_name, "keywords": keywords, "title": title, "message": message, "host": hostname}
        webhook_url = config.notifications.webhook.url
        webhook_headers = config.notifications.webhook.headers
        send_webhook(json_data, webhook_url, webhook_headers)

