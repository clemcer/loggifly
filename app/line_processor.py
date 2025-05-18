import docker
import os
import re
import time
import json
import string
import logging
import traceback
import threading
from threading import Thread, Lock
from notifier import send_notification
from load_config import GlobalConfig, KeywordItem, RegexItem

class LogProcessor:
    """
    This class processes log lines from a Docker container and:
    - searches for patterns and keywords, 
    - tries to catch entries that span multple lines by detecting patterns and putting lines in a buffer first to see if the next line belongs to the same entry or not
    - triggers notifications when a keyword is found
    - triggers restarts/stops of the monitored container


    LoggiFly searches for patterns that signal the start of a log entry to detect entries that span over multiple lines.
    That is what these patterns are for:
    """
    STRICT_PATTERNS = [
            
        # combined timestamp and log level
        r"^\[\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}(?:,\d{3})?\] \[(?:INFO|ERROR|DEBUG|WARN|WARNING|CRITICAL)\]", # 
        r"^\d{4}-\d{2}-\d{2}(?:, | )\d{2}:\d{2}:\d{2}(?:,\d{3})? (?:INFO|ERROR|DEBUG|WARN|WARNING|CRITICAL)",
        
        # ISO in brackets
        r"^\[\d{4}-\d{2}-\d{2}(?:T|, | )\d{2}:\d{2}:\d{2}(?:Z|[\.,]\d{2,6}|[+-]\d{2}:\d{2}| [+-]\d{4})\]", # [2025-02-17T03:23:07Z] or [2025-02-17 04:22:59 +0100] or [2025-02-18T03:23:05.436627]

        # Months in brackets
        r"^\[(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) \d{1,2}, \d{4} \d{2}:\d{2}:\d{2}\]",                                                  # [Feb 17, 2025 10:13:02]
        r"^\[\d{1,2}\/(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\/\d{4}(?:\:| |\/)\d{2}:\d{2}:\d{2}(?:Z||\s[+\-]\d{2}:\d{2}|\s[+\-]\d{4})\]", # [17/Feb/2025:10:13:02 +0000]

        # ISO without brackes
        r"^\b\d{4}-\d{2}-\d{2}(?:T|, | )\d{2}:\d{2}:\d{2}(?:Z|[\.,]\d{2,6}|[+-]\d{2}:\d{2}| [+-]\d{4})\b",

        # Months without brackets
        r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) \d{1,2}, \d{4} \d{2}:\d{2}:\d{2}\b",
        r"\b\d{1,2}\/(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\/\d{4}(?:\:| |\/)\d{2}:\d{2}:\d{2}(?:Z||\s[+\-]\d{2}:\d{2}|\s[+\-]\d{4})\b",   # 17/Feb/2025:10:13:02 +0000
        
        # Unix-like Timestamps
        r"^\[\d{4}\/\d{2}\/\d{2} \d{2}:\d{2}:\d{2}\.\d{2,6}\]",
        
        # Log-Level at the beginning of the line
        r"^\[(?:INFO|ERROR|DEBUG|WARN|WARNING|CRITICAL)\]",
        r"^\((?:INFO|ERROR|DEBUG|WARN|WARNING|CRITICAL)\)"
    ]

    FLEX_PATTERNS = [
            # ----------------------------------------------------------------
            # Generic Timestamps (Fallback)
            # ----------------------------------------------------------------
            
            r"\b\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\b",
            r"\b\d{4}-\d{2}-\d{2}(?:T|, | )\d{2}:\d{2}:\d{2}(?:Z|[\.,]\d{2,6}|[+-]\d{2}:\d{2}| [+-]\d{4})\b", # 2025-02-17T03:23:07Z
            r"\b(?:0[1-9]|1[0-2])-(?:0[1-9]|[12]\d|3[01])-\d{4} \d{2}:\d{2}:\d{2}\b",
            r"(?i)\b\d{2}\/\d{2}\/\d{4}(?:,\s+|:|\s+])\d{1,2}:\d{2}:\d{2}\s*(?:AM|PM)?\b",
            r"\b\d{10}\.\d+\b",                                                          # 1739762586.0394847

            # ----------------------------------------------------------------
            # Log-Level (Fallback)
            # ----------------------------------------------------------------
            r"(?i)(?<=^)\b(?:INFO|ERROR|DEBUG|WARN(?:ING)?|CRITICAL)\b(?=\s|:|$)",      
            r"(?i)(?<=\s)\b(?:INFO|ERROR|DEBUG|WARN(?:ING)?|CRITICAL)\b(?=\s|:|$)",
            r"(?i)\[(?:INFO|ERROR|DEBUG|WARN(?:ING)?|CRITICAL)\]",
            r"(?i)\((?:INFO|ERROR|DEBUG|WARN(?:ING)?|CRITICAL)\)",
            r"(?i)\d{2}/\d{2}/\d{4},\s+\d{1,2}:\d{2}:\d{2}\s+(?:AM|PM)",
        ]
            
    COMPILED_STRICT_PATTERNS = [re.compile(pattern, re.ASCII) for pattern in STRICT_PATTERNS]
    COMPILED_FLEX_PATTERNS = [re.compile(pattern, re.ASCII) for pattern in FLEX_PATTERNS]

    def __init__(self, logger, hostname, config: GlobalConfig, container, container_stop_event, swarm_service=None): 
        self.logger = logger    
        self.hostname = hostname    # empty string if only one client else the hostname of the client 
        self.container_stop_event = container_stop_event
        self.container = container
        self.swarm_service=swarm_service
        self.container_name = self.swarm_service if self.swarm_service else self.container.name

        self.patterns = []
        self.patterns_count = {pattern: 0 for pattern in self.__class__.COMPILED_STRICT_PATTERNS + self.__class__.COMPILED_FLEX_PATTERNS}
        self.lock_buffer = Lock()
        self.flush_thread_stopped = threading.Event()
        self.flush_thread_stopped.set()
        self.waiting_for_pattern = False
        self.valid_pattern = False

        self.load_config_variables(config)

    
    def get_keywords(self, keywords):
        returned_keywords = []
        self.logger.debug(f"Keywords from config for {self.container_name}: {keywords}")
        for item in keywords:
            if isinstance(item, (KeywordItem)):
                returned_keywords.append((item.keyword, item))
            elif isinstance(item, RegexItem):
                returned_keywords.append((item.regex, item))
            elif isinstance(item, str):
                returned_keywords.append((item, None))
        return returned_keywords

    def load_config_variables(self, config):
        """
        This function can get called from the log_monitor function in app.py to reload the config variables
        """
        self.config = config
        # self.container_keywords = self.config.global_keywords.keywords.copy()
        # self.container_keywords_with_attachment = self.config.global_keywords.keywords_with_attachment.copy()
        self.logger.debug(f"CONFIG: {self.config}")
        config_global_keywords = self.config.global_keywords
        self.logger.debug(f"Global Keywords from config: {config_global_keywords}")
        self.logger.debug(f"Global keyword keywords: {config_global_keywords.keywords}")
        self.keywords = self.get_keywords(config_global_keywords.keywords)



        if self.swarm_service:
            container_config = self.config.swarm_services[self.swarm_service]
           # self.container_action_keywords = []
        else:
            container_config = self.config.containers[self.container_name]
            #self.container_action_keywords = [keyword for keyword in container_config.action_keywords]
        self.keywords.extend(self.get_keywords(container_config.keywords))
        # keywords = self.get_keywords(container_config.keywords.copy())
        # self.keywords.extend(keywords)       
        # self.container_keywords.extend(keyword for keyword in self.config.swarm_services[self.swarm_service].keywords if keyword not in self.container_keywords)
        # self.container_keywords_with_attachment.extend(keyword for keyword in self.config.swarm_services[self.swarm_service].keywords_with_attachment if keyword not in self.container_keywords_with_attachment)
        self.logger.debug(f"\n\nFINISHED KEYWORDS FOR {self.container_name}: {self.keywords}\n")

        self.number_attachment_lines = container_config.attachment_lines or self.config.settings.attachment_lines
        self.notification_cooldown = container_config.notification_cooldown or self.config.settings.notification_cooldown
        self.action_cooldown = container_config.action_cooldown or self.config.settings.action_cooldown or 300
        self.notification_title = container_config.notification_title or self.config.settings.notification_title

        self.multi_line_config = self.config.settings.multi_line_entries
        self.time_per_keyword = {}  
        self.last_action_time = None

        for keyword, item in self.keywords:
            self.time_per_keyword[keyword] = 0  
                    
        if self.multi_line_config is True:
            self.line_count = 0
            self.line_limit = 300
            if self.valid_pattern is False:
                try:
                    log_tail = self.container.logs(tail=100).decode("utf-8")
                    self._find_pattern(log_tail)
                except Exception as e:
                    self.logger.error(f"Could not read logs of Container {self.container_name}: {e}")
                if self.valid_pattern:
                    self.logger.debug(f"{self.container_name}: Mode: Multi-Line. Found starting pattern(s) in logs.")
                else:
                    self.logger.debug(f"{self.container_name}: Mode: Single-Line. Could not find starting pattern in the logs. Continuing the search in the next {self.line_limit - self.line_count} lines")
        
            self.buffer = []
            self.log_stream_timeout = 1 # self.config.settings.flush_timeout Not an supported setting (yet)
            self.log_stream_last_updated = time.time()
            # Start Background-Thread for Timeout (only starts when it is not already running)
            self._start_flush_thread()

        self.logger.debug(f"LogProcessor for {self.container_name} initialized. Multi-Line Mode: {self.multi_line_config}. Keywords: {self.keywords}")
                
    def process_line(self, line):
        """        
        This function gets called from outside this class by the monitor_container_logs function in app.py
        If the user disables multi_line_entries or if there are no patterns detected (yet) the program switches to single-line mode
        In single-line mode the line gets processed and searched for keywords instantly instead of going into the buffer first
        """
        clean_line = re.sub(r"\x1b\[[0-9;]*m", "", line)
        if self.multi_line_config == False:
            self._search_and_send(clean_line)
        else:
            if self.line_count < self.line_limit:
                self._find_pattern(clean_line)
            if self.valid_pattern == True:
                self._process_multi_line(clean_line)
            else:
                self._search_and_send(clean_line)        

    def _find_pattern(self, line_s):
        """
        searches for patterns in the log lines to be able to detect the start of new log entries.
        When a pattern is found self.valid_pattern is set to True and the pattern gets added to self.patterns.
        When no pattern is found self.valid_pattern stays False which sets the mode to single-line (not catching multi line entries).
        """
        self.waiting_for_pattern = True
        for line in line_s.splitlines():
            clean_line = re.sub(r"\x1b\[[0-9;]*m", "", line)
            self.line_count += 1
            for pattern in self.__class__.COMPILED_STRICT_PATTERNS:
                if pattern.search(clean_line):
                    self.patterns_count[pattern] += 1
                    break
            else:
                for pattern in self.__class__.COMPILED_FLEX_PATTERNS:
                    if pattern.search(clean_line):
                        self.patterns_count[pattern] += 1
                        break
  
        sorted_patterns = sorted(self.patterns_count.items(), key=lambda x: x[1], reverse=True)
        threshold = max(5, int(self.line_count * 0.075))

        for pattern in sorted_patterns:
            if pattern[0] not in self.patterns and pattern[1] > threshold:
                self.patterns.append(pattern[0])
                self.logger.debug(f"{self.container_name}: Found pattern: {pattern[0]} with {pattern[1]} matches of {self.line_count} lines. {round(pattern[1] / self.line_count * 100, 2)}%")
                self.valid_pattern = True
        if self.patterns == []:
            self.valid_pattern = False
        if self.line_count >= self.line_limit:
            if self.patterns == []:
                self.logger.info(f"{self.container_name}: No pattern found in logs after {self.line_limit} lines. Mode: single-line")

        self.waiting_for_pattern = False

    def _start_flush_thread(self):
        def check_flush():
            """
            When mode is multi-line new lines go into a buffer first to see whether the next line belongs to the same entry or not.
            Every second the buffer gets flushed
            """ 
            self.flush_thread_stopped.clear()
            while True:
                if self.container_stop_event.is_set(): # self.shutdown_event.is_set() or 
                    time.sleep(4)
                    if self.container_stop_event.is_set():
                        break
                if self.multi_line_config is False:
                    break
                with self.lock_buffer:
                    if (time.time() - self.log_stream_last_updated > self.log_stream_timeout) and self.buffer:
                        self._handle_and_clear_buffer()
                time.sleep(1)
            self.flush_thread_stopped.set()
            self.logger.debug(f"Flush Thread stopped for Container {self.container_name}")
            
        if self.flush_thread_stopped.is_set():
            self.flush_thread = Thread(target=check_flush, daemon=True)
            self.flush_thread.start()

    def _handle_and_clear_buffer(self):
        """    
        This function is called either when the buffer is flushed 
        or when a new log entry was found that does not belong to the last line in the buffer
        It calls the _search_and_send function to search for keywords in all log lines in the buffer
        """
        log_entry = "\n".join(self.buffer)
        self._search_and_send(log_entry)
        self.buffer.clear()

    def _process_multi_line(self, line):
        """
        When mode is multi-line this function processes the log lines.
        It checks if the line matches any of the patterns (meaning the line signals a new log entry) 
        and if so, it flushes the buffer and appends the new line to the buffer.
        """
        # When the pattern gets updated by _find_pattern() this function waits 
        while self.waiting_for_pattern is True:
            time.sleep(1)

        for pattern in self.patterns:
            # If there is a pattern in the line idicating a new log entry the buffer gets flushed and the line gets appended to the buffer           
            if pattern.search(line):
                if self.buffer:
                    self._handle_and_clear_buffer()
                self.buffer.append(line)
                match = True
                break
            else:
                match = False
        # If the line is not a new entry (no pattern was found) it gets appended to the buffer
        if match is False:
            if self.buffer:
                self.buffer.append(line)
            else:
                # Fallback: Unexpected Format 
                self.buffer.append(line)
        self.log_stream_last_updated = time.time()

    def _search_keyword(self, log_line, keyword, item, ignore_keyword_time=False):
        """
        searches for keywords and regex patterns in the log entry it is given-
        When a keywords is found and the time since the last notification is greater than the cooldown time
        it returns the keywords, if nothing is found it returns None
        """
        if isinstance(item, (RegexItem, KeywordItem)):
            notification_cooldown = item.notification_cooldown if item.notification_cooldown else self.notification_cooldown
        else:
            notification_cooldown = self.notification_cooldown
        if isinstance(item, RegexItem):
            hide_pattern = True if item.hide_pattern_in_title else False
            if ignore_keyword_time or time.time() - self.time_per_keyword.get(keyword) >= int(notification_cooldown):
                match = re.search(keyword, log_line, re.IGNORECASE)
                if match:
                    self.time_per_keyword[keyword] = time.time()
                    return "Regex-Pattern" if hide_pattern else f"Regex: {keyword}"
                
        elif isinstance(item, KeywordItem) or item is None:
        #     keyword = item.keyword

        # if isinstance(keyword, str):
            if ignore_keyword_time or time.time() - self.time_per_keyword.get(keyword) >= int(notification_cooldown):
                if keyword.lower() in log_line.lower():
                    self.time_per_keyword[keyword] = time.time()
                    return keyword
        return None
    
    def _update_message_config(self, item):
        if item is not None:
            for key, value in self.message_config.items():
                if value is None:
                    self.message_config[key] = getattr(item, key)


    def _search_and_send(self, log_line):
        """
        Triggers the search for keywords, keywords with attachment and action_keywords 
        and if found calls the _send_message function to send a notification 
        or the _container_action function to restart/stop the container
        """
        keywords_found = []
        send_attachment = False
        message = log_line
        message_config = {"message": log_line}

        for keyword, item in self.keywords:
            found = self._search_keyword(log_line, keyword, item)
            if found:
                if isinstance(item, (RegexItem, KeywordItem)):
                    if getattr(item, "template", None) or getattr(item, "json_template", None):
                        message_config["message"] = self.message_from_template(item, log_line)
                    if item.attach_logfile is True:
                        send_attachment = True
                    for (key, value) in item:
                        if message_config.get(key) is None and value is not None:
                            message_config[key] = value
                keywords_found.append(found)

        # Trigger notification if keywords have been found
        if keywords_found:   
            message_config["keywords_found"] = keywords_found
            action = message_config.get("action")
            if action is not None:
                 self._container_action(action)

            self.logger.debug(f"MESSAGE_CONFIG:\n{json.dumps(message_config, indent=2)}\n")

            formatted_log_entry ="\n  -----  LOG-ENTRY  -----\n" + ' | ' + '\n | '.join(log_line.splitlines()) + "\n   -----------------------"
            self.logger.info(f"{'Stopping' if action == 'stop' else 'Restarting'} {self.container_name}" if action else ""
                        + f"The following keywords were found in {self.container_name}: {keywords_found}."
                        + (f" (A Log FIle will be attached)" if send_attachment else "")
                        + f"{formatted_log_entry}"
                        )
            if send_attachment:
                self._send_message(message_config, send_attachment=True, action=None)
            else:
                self._send_message(message_config, send_attachment=False, action=None)


    def _send_message(self, message_config, send_attachment=False, action=None):
        """Adapt the notification title and call the send_notification function from notifier.py"""
        title = self.get_notification_title(message_config, action)
        if action:
            title = f"{'Stopping' if action == 'stop' else 'Restarting'} {self.container_name}! - " + title
        file_path = None
        if send_attachment:
            if message_config.get("attachment_lines") is not None:
                number_attachment_lines = message_config["attachment_lines"]
            else:
                number_attachment_lines = self.config.settings.attachment_lines
            file_path = self._log_attachment(number_attachment_lines)
        send_notification(self.config, 
                        container_name=self.container_name, 
                        title=title, 
                        message=message_config["message"], 
                        message_config=message_config, 
                        hostname=self.hostname, 
                        file_path=file_path)  
        
        if file_path and isinstance(file_path, str) and os.path.exists(file_path):
            if os.path.exists(file_path):
                os.remove(file_path)
                self.logger.debug(f"The file {file_path} was deleted.")
            else:
                self.logger.debug(f"The file {file_path} does not exist.") 

    def get_notification_title(self, message_config, action):
        keywords_found = message_config.get("keywords_found", "")
        if message_config.get("notification_title"):
            notification_title = self.message_config["notification_title"]
        else:
            notification_title = self.notification_title

        if notification_title.strip().lower() != "default":# and action is None:
            template = ""
            try:
                keywords = ', '.join(f"'{word}'" for word in keywords_found)
                template = self.notification_title.strip()
                possible_template_fields = {"keywords": keywords, "container": self.container_name}
                template_fields = [f for _, f, _, _ in string.Formatter().parse(template) if f]
                configured_template_fields = {k: v for k, v in possible_template_fields.items() if k in template_fields}
                title = template.format(**configured_template_fields)
                return title
            except KeyError as e:
                self.logger.error(f"Missing key in template: {template}. Template requires keys that weren't provided. Error: {e}")
            except Exception as e:
                self.logger.error(f"Error trying to apply this template for the notification title: {template} {e}")

        if isinstance(keywords_found, list):
            if len(keywords_found) == 1:
                keyword = keywords_found[0]
                title = f"'{keyword}' found in {self.container_name}"
            elif len(keywords_found) == 2:
                joined_keywords = ' and '.join(f"'{word}'" for word in keywords_found)
                title = f"{joined_keywords} found in {self.container_name}"
            elif len(keywords_found) > 2:
                joined_keywords = ', '.join(f"'{word}'" for word in keywords_found)
                title = f"The following keywords were found in {self.container_name}: {joined_keywords}"
            else:
                title = f"{self.container_name}: {keywords_found}"
        elif isinstance(keywords_found, str) and action:
            keyword = keywords_found
            title = f"{'Stopping' if action == 'stop' else 'Restarting'} {self.container_name} because '{keyword}' was found"
        else: 
            title = f"{self.container_name}: {keywords_found}"
            
        return title

    def message_from_template(self, keyword_item, log_line):
        message = log_line
        if not isinstance(keyword_item, (KeywordItem, RegexItem)):
            return message
        if keyword_item.json_template is not None:
            template = keyword_item.json_template
            try:
                json_log_entry = json.loads(log_line)
                json_template_fields = [f for _, f, _, _ in string.Formatter().parse(template) if f]
                json_log_data = {k: json_log_entry.get(k, "") for k in json_template_fields}
                json_log_data["original_log_line"] = log_line
                message = template.format(**json_log_data)
                self.logger.debug(f"Successfully applied this template: {template}")
            except (json.JSONDecodeError, UnicodeDecodeError):
                self.logger.error(f"Error parsing log line as JSON: {log_line}")
            except KeyError as e:
                self.logger.error(f"KeyError: {e} in template: {template} with log line: {log_line}")
            except Exception as e:
                self.logger.error(f"Unexpected Error trying to parse a JSON log line with template {template}: {e}")
                self.logger.error(f"Details: {traceback.format_exc()}") 

        elif isinstance(keyword_item, RegexItem) and keyword_item.template is not None:
            template = keyword_item.template
            match = re.search(keyword_item.regex, log_line, re.IGNORECASE)
            if match:
                groups = match.groupdict()
                groups.setdefault("original_log_line", log_line) 
                try:
                    message = template.format(**groups)
                    self.logger.debug(f"Successfully applied this template: {template}")
                    return message
                except KeyError as e:
                    self.logger.error(f"Key Error for template '{template}': {e}")
                except Exception as e:
                    self.logger.error(f"Error applying template {template}: {e}")
        return message

    def _log_attachment(self, number_attachment_lines):  
        """Tail the last lines of the container logs and save them to a file"""
        base_name = f"last_{self.number_attachment_lines}_lines_from_{self.container_name}.log"
        folder = "/tmp/"

        def find_available_name(filename, number=1):
            """Create different file name with number if it already exists (in case of many notifications at same time)"""
            new_name = f"{filename.rsplit('.', 1)[0]}_{number}.log"
            path = folder + new_name
            if os.path.exists(path):
                return find_available_name(filename, number + 1)
            return path
        
        if os.path.exists(base_name):
            file_path = find_available_name(base_name)
        else:
            file_path = folder + base_name
        try:
            os.makedirs("/tmp", exist_ok=True)
            log_tail = self.container.logs(tail=number_attachment_lines).decode("utf-8")
            with open(file_path, "w") as file:  
                file.write(log_tail)
                logging.debug(f"Wrote file: {file_path}")
                return file_path
        except Exception as e:
            self.logger.error(f"Could not create log attachment file for Container {self.container_name}: {e}")
            return None

    def _container_action(self, action):
        try: 
            if action == "stop":
                self.logger.info(f"Stopping Container: {self.container_name}.")
                container = self.container
                container.stop()
                self.logger.info(f"Container {self.container_name} has been stopped")
            elif action == "restart":
                self.logger.info(f"Restarting Container: {self.container_name}.")
                container = self.container
                container.stop()
                time.sleep(3)
                container.start()
                self.logger.info(f"Container {self.container_name} has been restarted")
        except Exception as e:
            self.logger.error(f"Failed to {action} {self.container_name}: {e}")

