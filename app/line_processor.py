import docker
import os
import re
import time
import logging
import threading
from threading import Thread, Lock
from notifier import send_notification
from load_config import GlobalConfig



class LogProcessor:
    """
    LoggiFly seearches for patterns that signal the start of a log entry to detect entries that span over multiple lines.
    That is what these patterns are for.
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

            # ## TESTING BECAUSE IT DOES NOT WORK FOR IMMICH SERVER LOGS
            r"(?i)\d{2}/\d{2}/\d{4},\s+\d{1,2}:\d{2}:\d{2}\s+(?:AM|PM)",
        ]
            
    COMPILED_STRICT_PATTERNS = [re.compile(pattern, re.ASCII) for pattern in STRICT_PATTERNS]
    COMPILED_FLEX_PATTERNS = [re.compile(pattern, re.ASCII) for pattern in FLEX_PATTERNS]

    def __init__(self, config: GlobalConfig, container, container_stop_event): # container_stop_event, shutdown_event, restart_event
        # self.shutdown_event = shutdown_event
        # self.restart_event = restart_event
        
        self.container_stop_event = container_stop_event
        self.container = container
        self.container_name = container.name

        self.patterns = []
        self.patterns_count = {pattern: 0 for pattern in self.__class__.COMPILED_STRICT_PATTERNS + self.__class__.COMPILED_FLEX_PATTERNS}
        self.lock_buffer = Lock()
        self.flush_thread_stopped = threading.Event()
        self.flush_thread_stopped.set()
        self.waiting_for_pattern = False
        self.valid_pattern = False
        
        
        self.load_config_variables(config)

        
    
    def load_config_variables(self, config):
        logging.debug(f"Loading Config Variables for {self.container.name} in Line_processor Instance")
        self.config = config
        self.container_keywords = self.config.global_keywords.keywords.copy()
        self.container_keywords.extend(keyword for keyword in self.config.containers[self.container_name].keywords if keyword not in self.container_keywords)
        self.container_keywords_with_attachment = self.config.global_keywords.keywords_with_attachment.copy()
        self.container_keywords_with_attachment.extend(keyword for keyword in self.config.containers[self.container_name].keywords_with_attachment if keyword not in self.container_keywords_with_attachment)
        self.container_keywords_restart = [keyword for keyword in self.config.containers[self.container_name].restart_keywords]

        self.lines_number_attachment = self.config.containers[self.container_name].attachment_lines or self.config.settings.attachment_lines
        self.multi_line_config = self.config.settings.multi_line_entries
        self.notification_cooldown = self.config.containers[self.container_name].notification_cooldown or self.config.settings.notification_cooldown
        self.time_per_keyword = {}  
        self.restart_cooldown = self.config.containers[self.container_name].restart_cooldown or 300
        self.last_restart_time = None

        for keyword in self.container_keywords + self.container_keywords_with_attachment + self.container_keywords_restart:
            if isinstance(keyword, dict) and keyword.get("regex") is not None:
                self.time_per_keyword[keyword["regex"]] = 0
            else:
                self.time_per_keyword[keyword] = 0  
                    
        if self.multi_line_config is True:
            self.line_count = 0
            self.line_limit = 300
            if self.valid_pattern is False:
                try:
                    log_tail = self.container.logs(tail=100).decode("utf-8")
                    self._find_pattern(log_tail)
                except Exception as e:
                    logging.error(f"Could not read logs of Container {self.container_name}: {e}")
        
            self.buffer = []
            self.log_stream_timeout = 1 # self.config.settings.flush_timeout Not an supported setting (yet)
            self.log_stream_last_updated = time.time()
            # Start Background-Thread for Timeout
            self._start_flush_thread()
                

            
    def _restart_container(self):
      #  self.restart_event.set()
        try:
            logging.info(f"Restarting Container: {self.container_name}.")
            container = self.container
            container.stop()
            time.sleep(3)
            container.start()
            logging.info(f"Container {self.container_name} has been restarted")
        except Exception as e:
            logging.error(f"Failed to restart container {self.container_name}: {e}")
        

    def _find_pattern(self, line_s):
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
                logging.debug(f"container: {self.container_name}: Found pattern: {pattern[0]} with {pattern[1]} matches of {self.line_count} lines. {round(pattern[1] / self.line_count * 100, 2)}%")
                self.valid_pattern = True
        if self.patterns == []:
            self.valid_pattern = False
        if self.line_count >= self.line_limit:
            if self.patterns == []:
                logging.info(f"Container: {self.container_name}: No pattern found in logs. Mode: single-line after {self.line_limit} lines. Mode: single-line")
            else:   
                logging.debug(f"Container: {self.container_name}: Found pattern(s) in logs. Stopping the search now after {self.line_limit}] lines. Mode: multi-line.")
                logging.debug(f"Container: {self.container_name}: Patterns found: {self.patterns}")

        self.waiting_for_pattern = False


    def _start_flush_thread(self):
    # Every second the buffer (with log lines that should belong to the same entry) gets flushed
        def check_flush():
            while True:
                if self.container_stop_event.is_set(): # self.shutdown_event.is_set() or 
                    logging.debug(f"Container: {self.container_name}: Container_stop_event: {self.container_stop_event.is_set()}. Waiting 15s until flush thread is stopped")
                    time.sleep(15)
                    if self.container_stop_event.is_set():
                        logging.debug(f"Container: {self.container_name}: Stopping Flush Thread. Container_stop_event: {self.container_stop_event.is_set()}")
                        self.flush_thread_stopped.set()
                        break
                with self.lock_buffer:
                    if (time.time() - self.log_stream_last_updated > self.log_stream_timeout) and self.buffer:
                        self._handle_and_clear_buffer()
                time.sleep(1)
            logging.debug(f"Flush Thread stopped for Container {self.container_name}")
        if self.flush_thread_stopped.is_set():
            self.flush_thread = Thread(target=check_flush, daemon=True)
            self.flush_thread.start()
            self.flush_thread_stopped.clear()
            logging.debug(f"Flush thread started for {self.container.name}")
        else:
            logging.debug(f"Flush thread already running for {self.container.name}")


    # This is the only function that gets called from outside this class by the monitor_container_logs function in app.py
    # If the user disables it or if there are no patterns detected (yet) the programm switches to single-line mode
    # In single-line mode the line gets processed and searched for keywords instantly instead of going into the buffer first
    def process_line(self, line):
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
        
            

    def _process_multi_line(self, line):
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

    # This function is called either when the buffer is flushed every second 
    # or if a new log entry was found which means everything in the buffer is one complete log entry
    def _handle_and_clear_buffer(self):
        message = "\n".join(self.buffer)
        self._search_and_send(message)
        self.buffer.clear()

    # Here the line is searchd for simple keywords or regex patterns
    def _search_and_send(self, log_line):
        keywords_found = []
        # Search for normal keywords
        for keyword in self.container_keywords + self.container_keywords_with_attachment + self.container_keywords_restart:
            if isinstance(keyword, dict) and keyword.get("regex") is not None:
                regex_keyword = keyword["regex"]
                if self.time_per_keyword == 0 or time.time() - self.time_per_keyword.get(regex_keyword) >= int(self.notification_cooldown):
                    if re.search(regex_keyword, log_line, re.IGNORECASE):
                        self.time_per_keyword[regex_keyword] = time.time()
                        keywords_found.append(f"regex: {regex_keyword}")
            else:
                if self.time_per_keyword == 0 or time.time() - self.time_per_keyword.get(keyword) >= int(self.notification_cooldown):
                    if str(keyword).lower() in log_line.lower():
                        self.time_per_keyword[keyword] = time.time()
                        keywords_found.append(keyword)
        
        if keywords_found:
            formatted_log_entry ="\n  -----  LOG-ENTRY  -----\n" + ' | ' + '\n | '.join(log_line.splitlines()) + "\n   -----------------------"
            if any(kw in self.container_keywords_with_attachment for kw in keywords_found):
                logging.info(f"The following keywords were found in {self.container_name}: {keywords_found}. (A Logfile will be attached){formatted_log_entry}" 
                        if len(keywords_found) > 1 
                        else f"The Keyword '{keywords_found[0]}' was found in {self.container_name}{formatted_log_entry}"
                        )
                self._send_message(log_line, keywords_found, send_attachment=True)
            else:
                logging.info(f"The following keywords were found in {self.container_name}: {keywords_found}{formatted_log_entry}"
                         if len(keywords_found) > 1 
                         else f"The Keyword '{keywords_found[0]}' was found in {self.container_name}{formatted_log_entry}"
                         )
                self._send_message(log_line, keywords_found, send_attachment=False)
       # Keywords that trigger a restart
            if self.last_restart_time is None or (self.last_restart_time is not None and time.time() - self.last_restart_time >= max(int(self.restart_cooldown), 60)):
                for keyword in self.container_keywords_restart:
                    if keyword in keywords_found:
                        logging.debug(f"Cooldown: {self.restart_cooldown}, last restart time: {self.last_restart_time}")
                        logging.info(f"Restarting {self.container_name} because Keyword: {keyword} was found in {formatted_log_entry}")
                        self._send_message(log_line, [keyword], send_attachment=False, restart=True)
                        self._restart_container()
                        self.last_restart_time = time.time()
                        break
                

    def _log_attachment(self):  
        base_name = f"last_{self.lines_number_attachment}_lines_from_{self.container_name}.log"

        def find_available_name(filename, number=1):
            # Create different file name with number if it already exists (in case of many notifications at same time)
            new_name = f"{filename.rsplit('.', 1)[0]}_{number}.log"
            if os.path.exists(new_name):
                return find_available_name(filename, number + 1)
            return new_name
        
        if os.path.exists(base_name):
            file_name = find_available_name(base_name)
        else:
            file_name = base_name

        try:
            file_name = f"last_{self.lines_number_attachment}_lines_from_{self.container_name}.log"
            log_tail = self.container.logs(tail=self.lines_number_attachment).decode("utf-8")
            with open(file_name, "w") as file:  
                file.write(log_tail)
                return file_name
        except Exception as e:
            logging.error(f"Could not read logs of Container {self.container_name}: {e}")
            return None

    def _send_message(self, message, keyword_list, send_attachment=False, restart=False):
        restart = restart
        if send_attachment:
            file_name = self._log_attachment()
            if file_name and isinstance(file_name, str) and os.path.exists(file_name):
                send_notification(self.config, self.container_name, message, keyword_list, file_name, restart)     
                if os.path.exists(file_name):
                    os.remove(file_name)
                    logging.debug(f"The file {file_name} was deleted.")
                else:
                    logging.debug(f"The file {file_name} does not exist.") 

        else:
            send_notification(self.config, self.container_name, message, keyword_list, None, restart)





