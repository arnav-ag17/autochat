"""
Log streaming utilities for Terraform, CloudWatch, and local files.
"""

import subprocess
import threading
import time
import json
import os
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass
from enum import Enum
import boto3
from botocore.exceptions import ClientError


class LogSource(Enum):
    """Sources of log data."""
    TERRAFORM = "terraform"
    EC2_CLOUD_INIT = "ec2:cloud-init"
    EC2_SYSTEMD = "systemd"
    ECS_TASK = "ecs:task"
    CLOUDWATCH = "cloudwatch"


@dataclass
class LogStream:
    """Represents a log stream configuration."""
    source: LogSource
    group: str
    stream: str
    region: str
    deployment_id: str


class StreamManager:
    """Manages multiple log streams and provides unified streaming interface."""
    
    def __init__(self, deployment_id: str, region: str, event_callback: Callable[[str, Dict[str, Any]], None]):
        self.deployment_id = deployment_id
        self.region = region
        self.event_callback = event_callback
        self.streams: Dict[str, LogStream] = {}
        self.active_threads: Dict[str, threading.Thread] = {}
        self.stop_event = threading.Event()
        self.cloudwatch_client = None
        
    def _get_cloudwatch_client(self):
        """Lazy initialization of CloudWatch client."""
        if self.cloudwatch_client is None:
            self.cloudwatch_client = boto3.client('logs', region_name=self.region)
        return self.cloudwatch_client
    
    def add_stream(self, stream_id: str, source: LogSource, group: str, stream: str):
        """Add a log stream to monitor."""
        log_stream = LogStream(
            source=source,
            group=group,
            stream=stream,
            region=self.region,
            deployment_id=self.deployment_id
        )
        self.streams[stream_id] = log_stream
        
        # Emit OBS_ATTACH event
        self.event_callback("OBS_ATTACH", {
            "source": source.value,
            "group": group,
            "stream": stream,
            "stream_id": stream_id
        })
    
    def start_streaming(self, stream_id: str):
        """Start streaming from a specific log source."""
        if stream_id not in self.streams:
            raise ValueError(f"Stream {stream_id} not found")
        
        stream = self.streams[stream_id]
        
        if stream.source == LogSource.CLOUDWATCH:
            self._start_cloudwatch_stream(stream_id, stream)
        elif stream.source == LogSource.EC2_CLOUD_INIT:
            self._start_cloudwatch_stream(stream_id, stream)
        elif stream.source == LogSource.EC2_SYSTEMD:
            self._start_cloudwatch_stream(stream_id, stream)
        elif stream.source == LogSource.ECS_TASK:
            self._start_cloudwatch_stream(stream_id, stream)
        else:
            # For terraform, we don't stream here as it's handled by terraform.py
            pass
    
    def _start_cloudwatch_stream(self, stream_id: str, stream: LogStream):
        """Start streaming from CloudWatch Logs."""
        def stream_worker():
            try:
                client = self._get_cloudwatch_client()
                start_time = int(time.time() * 1000)  # milliseconds
                
                while not self.stop_event.is_set():
                    try:
                        # Get log events
                        response = client.get_log_events(
                            logGroupName=stream.group,
                            logStreamName=stream.stream,
                            startTime=start_time,
                            startFromHead=False
                        )
                        
                        for event in response.get('events', []):
                            message = event.get('message', '').strip()
                            if message:
                                # Emit OBS_LINE event
                                self.event_callback("OBS_LINE", {
                                    "source": stream.source.value,
                                    "message": message,
                                    "timestamp": event.get('timestamp'),
                                    "stream_id": stream_id
                                })
                        
                        # Update start time for next poll
                        if response.get('events'):
                            start_time = response['events'][-1]['timestamp'] + 1
                        
                        # Poll every 5 seconds
                        time.sleep(5)
                        
                    except ClientError as e:
                        if e.response['Error']['Code'] == 'ResourceNotFoundException':
                            # Log group/stream doesn't exist yet, wait and retry
                            time.sleep(10)
                        else:
                            # Other error, log and continue
                            self.event_callback("OBS_LINE", {
                                "source": stream.source.value,
                                "message": f"CloudWatch error: {e}",
                                "stream_id": stream_id,
                                "error": True
                            })
                            time.sleep(30)
                    except Exception as e:
                        self.event_callback("OBS_LINE", {
                            "source": stream.source.value,
                            "message": f"Streaming error: {e}",
                            "stream_id": stream_id,
                            "error": True
                        })
                        time.sleep(30)
                        
            except Exception as e:
                self.event_callback("OBS_LINE", {
                    "source": stream.source.value,
                    "message": f"Failed to start streaming: {e}",
                    "stream_id": stream_id,
                    "error": True
                })
        
        thread = threading.Thread(target=stream_worker, daemon=True)
        thread.start()
        self.active_threads[stream_id] = thread
    
    def emit_cloudwatch_ready(self, stream_id: str):
        """Emit OBS_CWL_READY event when CloudWatch logs are available."""
        if stream_id in self.streams:
            stream = self.streams[stream_id]
            console_url = self._build_cloudwatch_console_url(stream.group, stream.stream)
            
            self.event_callback("OBS_CWL_READY", {
                "group": stream.group,
                "stream": stream.stream,
                "console_url": console_url,
                "stream_id": stream_id
            })
    
    def _build_cloudwatch_console_url(self, group: str, stream: str) -> str:
        """Build CloudWatch console URL for log group/stream."""
        encoded_group = group.replace('/', '$252F')
        encoded_stream = stream.replace('/', '$252F')
        return f"https://console.aws.amazon.com/cloudwatch/home?region={self.region}#logsV2:log-groups/log-group/{encoded_group}/log-events/{encoded_stream}"
    
    def stop_all_streams(self):
        """Stop all active streams."""
        self.stop_event.set()
        for thread in self.active_threads.values():
            thread.join(timeout=5)
        self.active_threads.clear()
    
    def get_stream_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all streams."""
        status = {}
        for stream_id, stream in self.streams.items():
            status[stream_id] = {
                "source": stream.source.value,
                "group": stream.group,
                "stream": stream.stream,
                "active": stream_id in self.active_threads,
                "console_url": self._build_cloudwatch_console_url(stream.group, stream.stream)
            }
        return status


def tail_cloudwatch_logs(log_group: str, log_stream: str, region: str, follow: bool = True) -> subprocess.Popen:
    """Tail CloudWatch logs using AWS CLI."""
    cmd = [
        "aws", "logs", "tail", log_group,
        "--log-stream-names", log_stream,
        "--region", region,
        "--format", "short"
    ]
    
    if follow:
        cmd.append("--follow")
    
    return subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1
    )


def stream_terraform_output(process: subprocess.Popen, event_callback: Callable[[str, Dict[str, Any]], None]):
    """Stream Terraform output and emit summarized events."""
    def stream_worker():
        for line in iter(process.stdout.readline, ''):
            if line:
                line = line.strip()
                if line:
                    # Emit OBS_LINE for terraform output
                    event_callback("OBS_LINE", {
                        "source": LogSource.TERRAFORM.value,
                        "message": line
                    })
    
    thread = threading.Thread(target=stream_worker, daemon=True)
    thread.start()
    return thread
