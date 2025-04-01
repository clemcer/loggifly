import os
import logging
import docker
import threading
import traceback
import signal
import atexit
import time
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from notifier import send_notification
from line_processor import LogProcessor
from load_config import load_config

logging.basicConfig(
    level="INFO",
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("monitor.log", mode="w"),
        logging.StreamHandler()
    ]
)

class DockerLogMonitor:
    def __init__(self):
        self.config = load_config()
        self._init_logging()
        self.client = docker.from_env()
        self.shutdown_event = threading.Event()
        self.threads = []
        self.threads_lock = threading.Lock()
        self.processors = {}
        self.processors_lock = threading.Lock()

        self.stream_connections = {}
        self.stream_connections_lock = threading.Lock()
        self.restarting_event = threading.Event()
        self.monitored_containers = {}
        self.selected_containers = []
        
        signal.signal(signal.SIGTERM, self.handle_signal)
        signal.signal(signal.SIGINT, self.handle_signal)
      #  atexit.register(self.cleanup)
        
        self.watch_events()

    def _init_logging(self):
        log_level = self.config.settings.log_level
        logging.getLogger().handlers.clear()
        logging.basicConfig(
            level = getattr(logging, log_level.upper(), logging.INFO),
            format="%(asctime)s - %(levelname)s - %(message)s",
            handlers=[
                logging.FileHandler("monitor.log", mode="w"),
                logging.StreamHandler()
            ]
        )
        logging.getLogger("urllib3.connectionpool").setLevel(logging.WARNING)        
        logging.info(f"Log-Level set to {log_level}")

            
    class ConfigHandler(FileSystemEventHandler):
        def __init__(self, monitor):
            self.monitor = monitor
            
        def on_modified(self, event):
            if not event.is_directory and event.src_path.endswith('config.yaml'):
                logging.info("Config change detected, restarting...")
                self.monitor.restart_loggifly()

    def handle_signal(self, signum, frame):
        if not self.config.settings.disable_shutdown_message:
            send_notification(self.config, "Loggifly:", "Shutting down")
        self.shutdown_event.set()
        self.cleanup()


    def restart_loggifly(self):
        if not self.config.settings.disable_restart_message:
            send_notification(self.config, "Loggifly:", "Config Change detected. The programm is restarting...")
        self.restarting_event.set()
        time.sleep(1.1) # Give _self.flush_threads() from line_processor.py some time to finish
        self.cleanup()
        self.config = load_config()
        self._init_logging()
        self.client = docker.from_env()
        self.monitored_containers = {}
        self.restarting_event.clear()
        self.start()


    def start_config_watcher(self):
        observer = Observer()
        observer.schedule(self.ConfigHandler(self), path="/app/config.yaml", recursive=False)
        observer.start()
        self.add_thread(observer)

    def add_thread(self, thread):
        with self.threads_lock:
            self.threads.append(thread)

    def add_processor(self, processor, container_name):
        with self.processors_lock:
            if container_name not in self.processors:
                self.processors[container_name] = processor
                return True
            else:
                return False

    def add_stream_connection(self, container_name, connection):
        with self.stream_connections_lock:
            self.stream_connections[container_name] = connection


    def close_stream_connecion(self, container_name):
        stream = self.stream_connections.get(container_name, None)
        if stream:
            try: 
                logging.debug(f"Trying to close log stream for container {container_name}")
                stream.close()
                self.stream_connections.pop(container_name)
            except Exception as e:
                    logging.warning(f"Error while trying do close stream during cleanup: {e}")
        else:
            logging.debug(f"Could not find stream connection for container {container_name}")
    def handle_error(self, error_count, last_error_time):
            new_count = error_count + 1
            current_time = time.time()
            if current_time - last_error_time > 180:
                new_count = 1
            return new_count, current_time
    
    def monitor_container(self, container):
        
        def check_container(container_start_time):
            container.reload()
            if container.status != "running":
                logging.debug(f"Container {container.name} not running")
                return False
            if container.attrs['State']['StartedAt'] != container_start_time:
                logging.debug(f"Container {container.name} not not same restart time")
                return False
            return True
        

        def log_monitor():
            """
            I am using a buffer in case the logstream has an unfinished log line that can't be decoded correctly.
            """
            container_start_time = container.attrs['State']['StartedAt']
            container_stop_event = threading.Event()
            container_stop_event.clear()
            error_count = 0
            last_error_time = time.time()  
            logging.debug(f"Container {container.name} Start Time: {container_start_time}")
            if container.name in self.processors:
                logging.debug(f"Re-Using old line processor")
                processor = self.processors[container.name]
            else:
               # logging.debug(f"Creating new line processor")
                processor = LogProcessor(self.config, container, container_stop_event, self.shutdown_event, self.restarting_event)  
                self.add_processor(processor, container.name)
            while not self.shutdown_event.is_set() and not self.restarting_event.is_set():
                buffer = b""
                try:
                    now = datetime.now()
                    last_chunk_time = time.time()
                    until_time = time.time() + 30
                    log_stream = container.logs(stream=True, follow=True, since=now)#, until=until_time)
                    self.add_stream_connection(container.name, log_stream)
                    logging.info(f"Monitoring for Container started: {container.name}")
                    for chunk in log_stream:
                        if container.name == "vg-backend":
                            logging.debug(f"CHuNK FROM VG_BACKEND: {chunk}")

                        if self.shutdown_event.is_set() or self.restarting_event.is_set():
                            logging.debug(f"stopping for chunk loop in {container.name}")
                            break
                        last_chunk_time = time.time()
                        # MAX_BUFFER_SIZE = 10 * 1024 * 1024  # 10MB
                        buffer += chunk
                        # if len(buffer) > MAX_BUFFER_SIZE:
                        #     logging.error("Buffer overflow detected, resetting")
                        #     buffer = b""
                        while b'\n' in buffer:
                            if container.name == "vg-backend":
                                logging.debug(f"'\\n' found in buffer {buffer} for vg-backend")
                            line, buffer = buffer.split(b'\n', 1)
                            try:
                                log_line_decoded = str(line.decode("utf-8")).strip()
                                if container.name == "vg-backend":
                                    logging.debug(f"LINE FROM VG_BACKEND: {log_line_decoded} (1)")
                            except UnicodeDecodeError:
                                log_line_decoded = line.decode("utf-8", errors="replace").strip()
                                logging.warning(f"{container.name}: Error while trying to decode a log line. Used errors='replace' for line: {log_line_decoded}")
                            if log_line_decoded: 
                                processor.process_line(log_line_decoded)

                            if container.name == "vg-backend":
                                logging.debug(f"LINE FROM VG_BACKEND: {log_line_decoded} (2)")
                       # time.sleep(0.1)
                        # if not check_container(container_start_time):
                        #     break

                except docker.errors.NotFound as e:
                    logging.error(F"Log Stream: Container {container} not found: {e}")
                    log_stream.close()   
                except docker.errors.APIError as e:
                    if e.response and e.response.status_code == 409:
                        logging.info(f"Connection to Container {container.name} closed.")
                        log_stream.close()   
                    else:
                        logging.error(f"Docker API-Errorer for Container {container.name}: {e}")
                    error_count, last_error_time = self.handle_error(error_count, last_error_time)
                except Exception as e:
                    logging.error("Error while trying to monitor %s: %s", container.name, e)
                    logging.error("Error details: %s", str(e.__class__.__name__))
                    logging.debug(traceback.format_exc())
                    error_count, last_error_time = self.handle_error(error_count, last_error_time)
                finally:
                    logging.info(f"Finally block for container {container.name}")
                    time.sleep(0.1)
                    if not check_container(container_start_time):
                        try:
                            logging.debug(f"Trying to close old log stream for container {container.name}")
                            log_stream.close()
                            break
                        except Exception as e:
                            logging.error(f"Could not close Log Stream for container {container.name}")
                            break
                    if self.shutdown_event.is_set() or self.restarting_event.is_set():
                        try:
                            logging.debug("Shutdown event or restart event is set. Closing log stream.")
                            log_stream.close()  
                            break 
                        except Exception as e:
                            logging.debug(f"Error closing stream: Container {container.name}: {str(e)}")
                            break
                    if error_count > 5:
                        logging.error(f"Error trying to establish Log Stream for {container.name}. Critical error threshold (6) reached.")
                        log_stream.close()  
                        break
                    logging.debug(f"Monitoring stopped for Container: {container.name}. Trying to reconnect")

                    
            logging.info("Monitoring stopped for Container: %s", container.name)
            container_stop_event.set()
        thread = threading.Thread(target=log_monitor, daemon=True)
        self.add_thread(thread)
        thread.start()

    def start(self):
        if self.config.settings.reload_config:
            self.start_config_watcher()

        containers = self.client.containers.list()
        self.selected_containers = []
        for container in self.config.containers:
            self.selected_containers.append(container)
        containers = self.client.containers.list()
        containers_to_monitor = [c for c in containers if c.name in self.selected_containers]
        containers_to_monitor_str = "\n - ".join(c.name for c in containers_to_monitor)
        logging.info(f"These containers are being monitored:\n - {containers_to_monitor_str}")
        unmonitored_containers = [c for c in self.selected_containers if c not in [c.name for c in containers_to_monitor]]
        if unmonitored_containers:
            unmonitored_containers_str = "\n - ".join(unmonitored_containers)
            logging.info(f"These selected Containers are not running:\n - {unmonitored_containers_str}")
        else:
            unmonitored_containers_str = ""

        if self.config.settings.disable_start_message is False:
            send_notification(self.config, "Loggifly", f"The programm is running and monitoring these selected Containers:\n - {containers_to_monitor_str}\n\nThese selected Containers are not running:\n - {unmonitored_containers_str}")
        
        for container in containers_to_monitor:
            self.monitor_container(container)
            self.monitored_containers[container.id] = container
        

    def watch_events(self):
        def event_handler():
            error_count = 0
            last_error_time = time.time()
            last_event_time = time.time()
            while not self.shutdown_event.is_set() and not self.restarting_event.is_set():
                until_time = time.time() + 1
                try: 
                    for event in self.client.events(decode=True, filters={"event": ["start", "stop"]}, until=until_time, since=last_event_time): #["start", "stop"]}):
                        if self.shutdown_event.is_set():
                            logging.debug("Shutdown event is set. Stopping event handler.")
                            break
                        container = self.client.containers.get(event["Actor"]["ID"])
                        if event.get("Action") == "start":
                            if container.name in self.selected_containers:
                                logging.info("Monitoring new container: %s", container.name)
                                send_notification(self.config, "Loggifly", f"Monitoring new container: {container.name}")
                                self.monitor_container(container)
                                self.monitored_containers[container.id] = container
                            # else:
                            #     logging.debug("Container %s is not in the config, ignoring.", container.name)
                        elif event.get("Action") == "stop":
                            if container.id in self.monitored_containers:
                                logging.debug(f"Event Handler: {container.name} stopped")
                                self.close_stream_connecion(container.name)
                                self.monitored_containers.pop(container.id)
                            

                        last_event_time = event.get("time", last_event_time)
                except docker.errors.NotFound as e:
                    logging.error(F"Event-Handler: Container {container} not found: {e}")
                    break
                except Exception as e:  
                    if self.shutdown_event.is_set():
                        break
                    logging.error(f"Event-Handler was stopped {e}. Trying to restart it.")
                    error_count, last_error_time = self.handle_error(error_count, last_error_time)
                finally:
                    if self.shutdown_event.is_set() or self.restarting_event.is_set():    
                        logging.debug("Event handler is shutting down.")
                        break
                    last_event_time = time.time()
                    if error_count > 5:
                        logging.error(f"Error trying to read docker events. Critical error threshold (6) reached.")
                        break
            logging.debug("Event handler stopped.")

        logging.info("Watching for new containers...")
        thread = threading.Thread(target=event_handler, daemon=True)
        self.add_thread(thread)
        thread.start()
    

    def cleanup(self):
        stream_connections = self.stream_connections.copy()
       # remaining_streams = []
        
        with self.stream_connections_lock:
            for container, stream in self.stream_connections.copy().items():
                logging.debug(f"Trying to close Log Stream Connections. {len(self.stream_connections)} remaining streams to close")
                self.close_stream_connecion(container)
            logging.debug(f"No Log Stream Connections left" if len(stream_connections) ==0 else f"{len(stream_connections)} Log Stream Connections remaining")
            #logging.debug(f"remaining streams {remaining_streams}")
       
        with self.threads_lock:
            alive_threads = []
            for thread in self.threads[::-1]:
                logging.debug(f"Trying to stop Thread {thread.name} is alive: {thread.is_alive()}, daemon: {thread.daemon} current_thread: {threading.current_thread()}")    
                if isinstance(thread, Observer):
                    thread.stop()
                if thread is not threading.current_thread() and thread.is_alive():
                    thread.join(timeout=3)
                    if thread.is_alive():
                        logging.warning(f"Thread {thread.name} nicht gestoppt")
                        alive_threads.append(thread)
            self.threads = alive_threads

        try:
            self.client.close()
            logging.info("Shutdown completed")
        except Exception as e:
            logging.warning(f"Error while trying do close docker client connection during cleanup: {e}")

        logging.debug(f"Threads still alive {len(alive_threads)}: {alive_threads}")
        logging.debug(f"Threading Enumerate: {threading.enumerate()}")


if __name__ == "__main__":
    monitor = DockerLogMonitor()
    try:
        monitor.start()
        while not monitor.shutdown_event.is_set():
            monitor.shutdown_event.wait(1)
    except KeyboardInterrupt:
        monitor.shutdown_event.set()
