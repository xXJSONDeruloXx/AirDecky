import os
import sys
import asyncio
import json
import subprocess
import socket
import time
import base64
import hashlib
import uuid
from typing import Dict, List, Optional, Tuple
import threading

import decky

try:
    from zeroconf import ServiceBrowser, Zeroconf, ServiceListener, ServiceInfo
    import requests
except ImportError as e:
    decky.logger.error(f"Missing required dependencies: {e}")
    decky.logger.info("Installing dependencies...")
    
    try:
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", 
            "zeroconf>=0.120.0", "requests>=2.28.0"
        ])
        from zeroconf import ServiceBrowser, Zeroconf, ServiceListener, ServiceInfo
        import requests
        decky.logger.info("Dependencies installed successfully")
    except Exception as install_error:
        decky.logger.error(f"Failed to install dependencies: {install_error}")
        raise

class AirPlayDevice:
    def __init__(self, name: str, address: str, port: int, info: Dict):
        self.name = name
        self.address = address
        self.port = port
        self.info = info
        self.paired = False
        self.session_id = None

class AirPlayServiceListener(ServiceListener):
    def __init__(self):
        self.devices: Dict[str, AirPlayDevice] = {}
        self.callbacks: List = []

    def add_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        info = zc.get_service_info(type_, name)
        if info:
            address = socket.inet_ntoa(info.addresses[0])
            device_name = info.properties.get(b'fn', b'Unknown AirPlay Device').decode('utf-8')
            
            device = AirPlayDevice(
                name=device_name,
                address=address,
                port=info.port,
                info={
                    'features': info.properties.get(b'features', b'').decode('utf-8'),
                    'model': info.properties.get(b'model', b'').decode('utf-8'),
                    'srcvers': info.properties.get(b'srcvers', b'').decode('utf-8')
                }
            )
            
            self.devices[f"{address}:{info.port}"] = device
            self._notify_callbacks('device_added', device)

    def remove_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        info = zc.get_service_info(type_, name)
        if info:
            address = socket.inet_ntoa(info.addresses[0])
            key = f"{address}:{info.port}"
            if key in self.devices:
                device = self.devices.pop(key)
                self._notify_callbacks('device_removed', device)

    def update_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        pass

    def add_callback(self, callback):
        self.callbacks.append(callback)

    def _notify_callbacks(self, event_type: str, device: AirPlayDevice):
        for callback in self.callbacks:
            try:
                callback(event_type, device)
            except Exception as e:
                decky.logger.error(f"Callback error: {e}")

class ScreenCapture:
    def __init__(self):
        self.process = None
        self.running = False

    def start_capture(self, width: int = 1280, height: int = 800, fps: int = 30) -> bool:
        if self.running:
            return False

        try:
            cmd = [
                'ffmpeg', '-f', 'x11grab', '-video_size', f'{width}x{height}',
                '-framerate', str(fps), '-i', ':1.0',
                '-vcodec', 'libx264', '-preset', 'ultrafast',
                '-tune', 'zerolatency', '-pix_fmt', 'yuv420p',
                '-f', 'mpegts', '-'
            ]
            
            self.process = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            self.running = True
            return True
        except Exception as e:
            decky.logger.error(f"Failed to start screen capture: {e}")
            return False

    def stop_capture(self):
        if self.process and self.running:
            self.process.terminate()
            self.process.wait()
            self.running = False

    def read_frame(self) -> Optional[bytes]:
        if not self.running or not self.process:
            return None
        
        try:
            chunk = self.process.stdout.read(4096)
            return chunk if chunk else None
        except Exception:
            return None

class AirPlayClient:
    def __init__(self, device: AirPlayDevice):
        self.device = device
        self.session = requests.Session()
        self.session_id = str(uuid.uuid4())

    def pair(self, pin: str) -> bool:
        try:
            url = f"http://{self.device.address}:{self.device.port}/pair-setup"
            
            # Simplified pairing - in real implementation would use SRP protocol
            data = {
                'method': 'pin',
                'pin': pin,
                'user': 'AirDecky'
            }
            
            response = self.session.post(url, json=data, timeout=10)
            
            if response.status_code == 200:
                self.device.paired = True
                self.device.session_id = self.session_id
                return True
            return False
        except Exception as e:
            decky.logger.error(f"Pairing failed: {e}")
            return False

    def start_mirroring(self, width: int = 1280, height: int = 800) -> bool:
        if not self.device.paired:
            return False

        try:
            url = f"http://{self.device.address}:{self.device.port}/stream"
            
            headers = {
                'Content-Type': 'application/x-apple-binary-plist',
                'X-Apple-Session-ID': self.session_id
            }
            
            stream_info = {
                'width': width,
                'height': height,
                'refreshRate': 60,
                'maxFPS': 30,
                'compressionType': 'H264'
            }
            
            response = self.session.post(url, json=stream_info, headers=headers, timeout=10)
            return response.status_code == 200
        except Exception as e:
            decky.logger.error(f"Failed to start mirroring: {e}")
            return False

    def stop_mirroring(self) -> bool:
        try:
            url = f"http://{self.device.address}:{self.device.port}/stream"
            headers = {'X-Apple-Session-ID': self.session_id}
            response = self.session.delete(url, headers=headers, timeout=5)
            return response.status_code == 200
        except Exception:
            return False

class Plugin:
    def __init__(self):
        self.loop = None
        self.zeroconf = None
        self.listener = None
        self.screen_capture = ScreenCapture()
        self.current_client: Optional[AirPlayClient] = None
        self.streaming = False
        self.stream_thread = None

    async def discover_devices(self) -> List[Dict]:
        if not self.listener:
            return []
        
        devices = []
        for device in self.listener.devices.values():
            devices.append({
                'name': device.name,
                'address': device.address,
                'port': device.port,
                'paired': device.paired,
                'model': device.info.get('model', 'Unknown')
            })
        
        return devices

    async def pair_device(self, address: str, port: int, pin: str) -> bool:
        device_key = f"{address}:{port}"
        if device_key not in self.listener.devices:
            return False

        device = self.listener.devices[device_key]
        client = AirPlayClient(device)
        
        success = client.pair(pin)
        if success:
            self.current_client = client
        
        return success

    async def start_streaming(self, address: str, port: int) -> bool:
        if self.streaming:
            return False

        device_key = f"{address}:{port}"
        if device_key not in self.listener.devices:
            return False

        device = self.listener.devices[device_key]
        if not device.paired:
            return False

        if not self.current_client or self.current_client.device.address != address:
            self.current_client = AirPlayClient(device)

        if not self.current_client.start_mirroring():
            return False

        if not self.screen_capture.start_capture():
            self.current_client.stop_mirroring()
            return False

        self.streaming = True
        self.stream_thread = threading.Thread(target=self._stream_worker)
        self.stream_thread.daemon = True
        self.stream_thread.start()

        return True

    async def stop_streaming(self) -> bool:
        if not self.streaming:
            return False

        self.streaming = False
        
        if self.stream_thread:
            self.stream_thread.join(timeout=5)

        self.screen_capture.stop_capture()
        
        if self.current_client:
            self.current_client.stop_mirroring()

        return True

    def _stream_worker(self):
        try:
            while self.streaming:
                frame_data = self.screen_capture.read_frame()
                if frame_data and self.current_client:
                    self._send_frame(frame_data)
                time.sleep(1/30)  # 30 FPS
        except Exception as e:
            decky.logger.error(f"Streaming error: {e}")
            self.streaming = False

    def _send_frame(self, frame_data: bytes):
        try:
            url = f"http://{self.current_client.device.address}:{self.current_client.device.port}/stream-data"
            headers = {
                'Content-Type': 'video/mp2t',
                'X-Apple-Session-ID': self.current_client.session_id
            }
            self.current_client.session.post(url, data=frame_data, headers=headers, timeout=1)
        except Exception as e:
            decky.logger.error(f"Failed to send frame: {e}")

    async def get_streaming_status(self) -> Dict:
        return {
            'streaming': self.streaming,
            'connected_device': self.current_client.device.name if self.current_client else None
        }

    async def _main(self):
        self.loop = asyncio.get_event_loop()
        
        try:
            self.zeroconf = Zeroconf()
            self.listener = AirPlayServiceListener()
            
            self.browser = ServiceBrowser(
                self.zeroconf, "_airplay._tcp.local.", self.listener
            )
            
            decky.logger.info("AirDecky plugin initialized")
        except Exception as e:
            decky.logger.error(f"Failed to initialize AirDecky: {e}")

    async def _unload(self):
        await self.stop_streaming()
        
        if self.zeroconf:
            self.zeroconf.close()
        
        decky.logger.info("AirDecky plugin unloaded")

    async def _uninstall(self):
        await self._unload()
        decky.logger.info("AirDecky plugin uninstalled")
