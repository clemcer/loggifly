import os
import sys
import time
import signal
import threading
import logging
import traceback
import docker
from threading import Timer
from docker.tls import TLSConfig
from urllib.parse import urlparse
from pydantic import ValidationError
from typing import Any
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from load_config import load_config, format_pydantic_error
from docker_monitor import DockerLogMonitor
from notifier import send_notification


logging.basicConfig(
    level="INFO",
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler()
    ]
)
logging.getLogger("urllib3.connectionpool").setLevel(logging.WARNING)    
logging.getLogger("docker").setLevel(logging.INFO)
logging.getLogger("watchdog").setLevel(logging.WARNING)


def create_handle_signal(monitor_instances, config, config_observer):
    global_shutdown_event = threading.Event()   

    def handle_signal(signum, frame):
        if not config.settings.disable_shutdown_message:
            send_notification(config, "LoggiFly", "LoggiFly", "Shutting down")
        if config_observer is not None:
            config_observer.stop()
            config_observer.join()
        threads = []
        for monitor in monitor_instances:
            monitor.shutdown_event.set()
            thread = threading.Thread(target=monitor.cleanup)
            threads.append(thread)
            thread.start()
        for thread in threads:
            thread.join(timeout=2)    
        global_shutdown_event.set()

    return handle_signal, global_shutdown_event
    

class ConfigHandler(FileSystemEventHandler):
    """
    When a config.yaml change is detected, the reload_config method is called on each host's DockerLogMonitor instance.
    This method then updates all LogProcessor instances (from line_processor.py) by calling their load_config_variables function.
    This ensures that any new keywords, settings, or other configuration changes are correctly applied especiaööy in the code that handles keyword searching in line_processor.py.    
    """
    def __init__(self, monitor_instances, config):
        self.monitor_instances = monitor_instances  
        self.last_config_reload_time = 0
        self.config = config
        self.reload_timer = None
        self.debounce_seconds = 2

    def on_modified(self, event):
        if self.config.settings.reload_config and not event.is_directory and event.src_path.endswith('config.yaml'):
            if self.reload_timer:
                self.reload_timer.cancel()
            self.reload_timer = Timer(self.debounce_seconds, self._trigger_reload)
            self.reload_timer.start()

    def _trigger_reload(self):
        logging.info("Config change detected, reloading config...")
        try:
            self.config, _ = load_config()
        except ValidationError as e:
            logging.critical(f"Error reloading config (using old config): {format_pydantic_error(e)}")
            return
        for monitor in self.monitor_instances:
            monitor.reload_config(self.config)
        if not self.config.settings.reload_config:
            self.observer.stop()
            self.logger.info("Config watcher stopped because reload_config is set to False.")


def start_config_watcher(monitor_instances, config, path):
    observer = Observer()
    observer.schedule(ConfigHandler(monitor_instances, config), path=path, recursive=False)
    observer.start()
    return observer
    

def check_monitor_status(docker_hosts, global_shutdown_event):
    """
    Every 60s this function checks whether the docker hosts are still monitored and tries to reconnect if the connection is lost.
    """
    def check_and_reconnect():
        while True:
            time.sleep(60)
            for host, values in docker_hosts.items():
                monitor = values["monitor"]
                if monitor.shutdown_event.is_set():
                    while monitor.cleanup_event.is_set():
                        time.sleep(1)
                    if global_shutdown_event.is_set():
                        return
                    tls_config, label = values["tls_config"], values["label"]
                    new_client = None
                    try:    
                        new_client = docker.DockerClient(base_url=host, tls=tls_config)
                    except docker.errors.DockerException as e:
                        logging.warning(f"Could not reconnect to {host} ({label}): {e}")
                    except Exception as e:
                        logging.warning(f"Could not reconnect to {host} ({label}). Unexpected error creating Docker client: {e}")
                    if new_client:
                        logging.info(f"Successfully reconnected to {host} ({label})")
                        monitor.shutdown_event.clear()
                        monitor.start(new_client)
                        monitor.reload_config(None)

    thread = threading.Thread(target=check_and_reconnect, daemon=True)
    thread.start()
    return thread


def create_docker_clients() -> dict[str, dict[str, Any]]: # {host: {client: DockerClient, tls_config: TLSConfig, label: str}}
    """
    This function creates Docker clients for all hosts specified in the DOCKER_HOST environment variables + the mounted docker socket.
    TLS certificates are searched in '/certs/{ca,cert,key}'.pem 
    or '/certs/{host}/{ca,cert,key}.pem' (to use in case of multiple hosts) with {host} being the IP or FQDN of the host.
    """
    def get_tls_config(hostname):
        cert_locations = [
            (os.path.join("/certs", hostname)),   
            (os.path.join("/certs"))             
        ]

        for cert_dir in cert_locations:
            logging.debug(f"Checking TLS certs for {hostname} in {cert_dir}")
            ca = os.path.join(cert_dir, "ca.pem")
            cert = os.path.join(cert_dir, "cert.pem")
            key = os.path.join(cert_dir, "key.pem")
            
            if all(os.path.exists(f) for f in [ca, cert, key]):
                logging.debug(f"Found TLS certs for {hostname} in {cert_dir}")
                return TLSConfig(client_cert=(cert, key), ca_cert=ca, verify=True)
        return None

    docker_host = os.environ.get("DOCKER_HOST", "")
    logging.debug(f"Environment variable DOCKER_HOST: {os.environ.get('DOCKER_HOST', ' - Not configured - ')}")
    tmp_hosts = [h.strip() for h in docker_host.split(",") if h.strip()]
    hosts = []
    for host in tmp_hosts:
        label = None
        if "|" in host:
            host, label = host.split("|", 1)
        hosts.append((host, label.strip()) if label else (host.strip(), None))

    if os.path.exists("/var/run/docker.sock"):
        logging.debug(f"Path to docker socket exists: True")
        if not any(h[0] == "unix:///var/run/docker.sock" for h in hosts):
            hosts.append(("unix:///var/run/docker.sock", None)) 

    logging.debug(f"Configured docker hosts to connect to: {[host for (host, _) in hosts]}")

    if len(hosts) == 0:
        logging.critical("No docker hosts configured. Please set the DOCKER_HOST environment variable or mount your docker socket.")


    docker_hosts = {}
    for host, label in hosts:
        logging.info(f"Trying to connect to docker client on host: {host}")
        parsed = urlparse(host)
        tls_config = None
        if parsed.scheme == "unix":
            pass
        elif parsed.scheme == "tcp":
            hostname = parsed.hostname
            tls_config = get_tls_config(hostname)
        try:
            if "podman" in host:
                # podman seems to use the timeout for the log stream as well so when there are no logs for a while there are timeout exceptions.
                # This is a workaround to avoid this issue by first creating a client with a short timeout to check the connection and then creating a client with a longer timeout.
                client = docker.DockerClient(base_url=host, tls=tls_config, timeout=10)
                if client.ping():
                    logging.info(f"Successfully connected to Podman client on {host}")
                    client.close()
                    client = docker.DockerClient(base_url=host, tls=tls_config, timeout=300)
            else:
                client = docker.DockerClient(base_url=host, tls=tls_config, timeout=10)
                docker_hosts[host] = {"client": client, "tls_config": tls_config, "label": label}
        except docker.errors.DockerException as e:
            logging.error(f"Error creating Docker client for {host}: {e}")
            logging.debug(f"Traceback: {traceback.format_exc()}")
            continue
        except Exception as e:
            logging.error(f"Unexpected error creating Docker client for {host}: {e}")
            logging.debug(f"Traceback: {traceback.format_exc()}")
            continue
        
    if len(docker_hosts) == 0:
        logging.critical("Could not connect to any docker hosts. Please check your DOCKER_HOST environment variable or mounted docker socket.")
        logging.info("Waiting 10s to prevent restart loop...")
        time.sleep(10)
        sys.exit(1)
    logging.info(f"Connections to Docker-Clients established for {', '.join([host for host in docker_hosts.keys()])}"
                 if len(docker_hosts.keys()) > 1 else "Connected to Docker Client")
    return docker_hosts


def start_loggifly():
    try:
        config, path = load_config()
    except ValidationError as e:
        logging.critical(f"Error loading Config: {format_pydantic_error(e)}")
        logging.info("Waiting 15s to prevent restart loop...")
        time.sleep(15)
        sys.exit(1)

    logging.getLogger().setLevel(getattr(logging, config.settings.log_level.upper(), logging.INFO))
    logging.info(f"Log-Level set to {config.settings.log_level}")

    docker_hosts = create_docker_clients()
    hostname = ""
    for number, (host, values) in enumerate(docker_hosts.items(), start=1):
        client, label = values["client"], values["label"]
        if len(docker_hosts.keys()) > 1:
            try:
                hostname = label if label else client.info()["Name"]
            except Exception as e:
                hostname = f"Host-{number}"
                logging.warning(f"Could not get hostname for {host}. LoggiFly will call this host '{hostname}' in notifications and in logging to differentiate it from the other hosts."
                    f"\nThis error might have been raised because you are using a Socket Proxy without the environment variable 'INFO=1'"
                    f"\nYou can also set a label for the docker host in the DOCKER_HOST environment variable like this: 'tcp://host:2375|label' to use instead of the hostname."
                    f"\nError details: {e}")    
                                
        logging.info(f"Starting monitoring for {host} {'(' + hostname + ')' if hostname else ''}")
        monitor = DockerLogMonitor(config, hostname, host)
        monitor.start(client)   
        docker_hosts[host]["monitor"] = monitor

    monitor_instances = [docker_hosts[host]["monitor"] for host in docker_hosts.keys()]
    # Start config observer to catch config.yaml changes
    if config.settings.reload_config and isinstance(path, str) and os.path.exists(path):
        config_observer = start_config_watcher(monitor_instances, config, path)
    else:
        logging.debug("Config watcher was not started because reload_config is set to False or because no valid config path exist.")
        config_observer = None

    handle_signal, global_shutdown_event = create_handle_signal(monitor_instances, config, config_observer)
    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)   

    # Start the thread that checks whether the docker hosts are still monitored and tries to reconnect if the connection is lost.
    check_monitor_status(docker_hosts, global_shutdown_event)
    return global_shutdown_event


if __name__ == "__main__":
    global_shutdown_event = start_loggifly()
    global_shutdown_event.wait()
    
