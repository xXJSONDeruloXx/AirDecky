import os
import subprocess
import asyncio
import socket
import json
import time
import threading
from typing import Optional, List, Dict
import struct
import tempfile

# The decky plugin module is located at decky-loader/plugin
# For easy intellisense checkout the decky-loader code repo
# and add the `decky-loader/plugin/imports` path to `python.analysis.extraPaths` in `.vscode/settings.json`
import decky

class MDNSDiscovery:
    """Simple mDNS discovery for AirPlay devices"""
    
    def __init__(self):
        self.devices = {}
        
    async def discover_airplay_devices(self, timeout: int = 5) -> List[Dict[str, str]]:
        """Discover AirPlay devices using mDNS"""
        try:
            # Use avahi-browse if available (common on Linux systems)
            result = subprocess.run([
                'avahi-browse', '-t', '-r', '_airplay._tcp'
            ], capture_output=True, text=True, timeout=timeout)
            
            if result.returncode == 0:
                return self._parse_avahi_output(result.stdout)
            else:
                # Fallback to network scanning
                return await self._network_scan()
                
        except (subprocess.TimeoutExpired, FileNotFoundError):
            decky.logger.warning("avahi-browse not available, using network scan")
            return await self._network_scan()
    
    def _parse_avahi_output(self, output: str) -> List[Dict[str, str]]:
        """Parse avahi-browse output to extract device information"""
        devices = []
        lines = output.split('\n')
        
        current_device = {}
        for line in lines:
            line = line.strip()
            if line.startswith('=') and '_airplay._tcp' in line:
                parts = line.split()
                if len(parts) >= 4:
                    current_device = {
                        'name': parts[3].replace('\\032', ' '),
                        'type': 'AirPlay Device'
                    }
            elif line.startswith('address') and current_device:
                # Extract IP address
                parts = line.split('[')
                if len(parts) > 1:
                    ip = parts[1].split(']')[0]
                    current_device['ip'] = ip
                    devices.append(current_device.copy())
                    current_device = {}
                    
        return devices
    
    async def _network_scan(self) -> List[Dict[str, str]]:
        """Fallback network scanning for AirPlay devices"""
        devices = []
        
        try:
            # Get local network range
            result = subprocess.run(['ip', 'route', 'show'], capture_output=True, text=True)
            network_range = self._extract_network_range(result.stdout)
            
            if network_range:
                # Scan common AirPlay ports
                tasks = []
                for i in range(1, 255):
                    ip = f"{network_range}.{i}"
                    tasks.append(self._check_airplay_device(ip))
                
                results = await asyncio.gather(*tasks, return_exceptions=True)
                devices = [r for r in results if isinstance(r, dict)]
                
        except Exception as e:
            decky.logger.error(f"Network scan error: {e}")
            
        return devices
    
    def _extract_network_range(self, route_output: str) -> Optional[str]:
        """Extract network range from ip route output"""
        for line in route_output.split('\n'):
            if 'src' in line and '192.168' in line:
                parts = line.split()
                for i, part in enumerate(parts):
                    if part == 'src' and i + 1 < len(parts):
                        ip = parts[i + 1]
                        return '.'.join(ip.split('.')[:-1])
        return None
    
    async def _check_airplay_device(self, ip: str) -> Optional[Dict[str, str]]:
        """Check if an IP has an AirPlay service"""
        try:
            # Try to connect to common AirPlay ports
            for port in [7000, 5000, 32498]:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1)
                result = sock.connect_ex((ip, port))
                sock.close()
                
                if result == 0:
                    # Try to get device info via HTTP
                    device_info = await self._get_device_info(ip)
                    if device_info:
                        return device_info
                        
        except Exception:
            pass
        return None
    
    async def _get_device_info(self, ip: str) -> Optional[Dict[str, str]]:
        """Try to get device information via HTTP"""
        try:
            # Try common AirPlay info endpoints
            import urllib.request
            
            for port in [7000, 5000]:
                try:
                    url = f"http://{ip}:{port}/server-info"
                    req = urllib.request.Request(url)
                    req.add_header('User-Agent', 'AirPlay/1.0')
                    
                    with urllib.request.urlopen(req, timeout=2) as response:
                        if response.status == 200:
                            return {
                                'name': f"AirPlay Device ({ip})",
                                'ip': ip,
                                'type': 'AirPlay Device'
                            }
                except:
                    continue
                    
        except Exception:
            pass
        return None

class ScreenCapture:
    """Screen capture utilities for different display systems"""
    
    def __init__(self):
        self.capture_process = None
        self.is_capturing = False
        
    async def check_capture_available(self) -> bool:
        """Check if screen capture is available"""
        # Check for various capture tools
        tools = ['ffmpeg', 'gstreamer-launch-1.0', 'wlr-randr', 'xwininfo']
        available_tools = {}
        
        for tool in tools:
            result = subprocess.run(['which', tool], capture_output=True, text=True)
            available_tools[tool] = result.returncode == 0
            
        # We need at least ffmpeg or gstreamer
        has_capture = available_tools.get('ffmpeg', False) or available_tools.get('gstreamer-launch-1.0', False)
        
        if not has_capture:
            decky.logger.warning("No screen capture tools found")
            return False
            
        # Check display environment
        display_env = os.environ.get("DISPLAY")
        wayland_display = os.environ.get("WAYLAND_DISPLAY")
        
        if not display_env and not wayland_display:
            decky.logger.warning("No display environment detected")
            return False
            
        return True
    
    async def start_capture(self, output_file: str) -> bool:
        """Start screen capture to file"""
        try:
            if self.is_capturing:
                await self.stop_capture()
                
            # Determine capture method based on environment
            if os.environ.get("WAYLAND_DISPLAY"):
                success = await self._start_wayland_capture(output_file)
            elif os.environ.get("DISPLAY"):
                success = await self._start_x11_capture(output_file)
            else:
                decky.logger.error("No supported display environment")
                return False
                
            self.is_capturing = success
            return success
            
        except Exception as e:
            decky.logger.error(f"Error starting capture: {e}")
            return False
    
    async def _start_wayland_capture(self, output_file: str) -> bool:
        """Start Wayland screen capture"""
        try:
            # Try wf-recorder first (if available)
            if subprocess.run(['which', 'wf-recorder'], capture_output=True).returncode == 0:
                cmd = [
                    'wf-recorder',
                    '-f', output_file,
                    '-c', 'h264_vaapi',  # Use hardware encoding if available
                    '--pixel-format', 'yuv420p'
                ]
            else:
                # Fallback to gstreamer with waylandsink
                cmd = [
                    'gst-launch-1.0',
                    'waylandsrc',
                    '!', 'videoconvert',
                    '!', 'x264enc', 'speed-preset=ultrafast', 'tune=zerolatency',
                    '!', 'h264parse',
                    '!', 'mp4mux',
                    '!', 'filesink', f'location={output_file}'
                ]
            
            self.capture_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            return True
            
        except Exception as e:
            decky.logger.error(f"Wayland capture error: {e}")
            return False
    
    async def _start_x11_capture(self, output_file: str) -> bool:
        """Start X11 screen capture"""
        try:
            # Use ffmpeg for X11 capture
            cmd = [
                'ffmpeg',
                '-f', 'x11grab',
                '-s', '1280x800',  # Steam Deck resolution
                '-r', '30',        # 30 FPS
                '-i', ':0.0',      # X11 display
                '-c:v', 'libx264',
                '-preset', 'ultrafast',
                '-tune', 'zerolatency',
                '-pix_fmt', 'yuv420p',
                '-y',
                output_file
            ]
            
            self.capture_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            return True
            
        except Exception as e:
            decky.logger.error(f"X11 capture error: {e}")
            return False
    
    async def stop_capture(self):
        """Stop screen capture"""
        if self.capture_process:
            try:
                self.capture_process.terminate()
                # Wait for process to end
                self.capture_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.capture_process.kill()
            finally:
                self.capture_process = None
                self.is_capturing = False

class AirplayDevice:
    def __init__(self, name: str, ip: str, port: int = 7000):
        self.name = name
        self.ip = ip
        self.port = port
        self.connected = False

class AirplayStreamer:
    """Handle AirPlay streaming protocol"""
    
    def __init__(self):
        self.streaming = False
        self.stream_process = None
        
    async def start_stream(self, device_ip: str, video_file: str) -> bool:
        """Start streaming video file to AirPlay device"""
        try:
            # This is a simplified implementation
            # Real AirPlay requires RTSP protocol implementation
            
            # For now, we'll use ffmpeg to stream via HTTP
            # This won't work with real AirPlay devices but demonstrates the concept
            cmd = [
                'ffmpeg',
                '-re',  # Read input at native frame rate
                '-i', video_file,
                '-c:v', 'copy',  # Copy video codec
                '-c:a', 'copy',  # Copy audio codec
                '-f', 'mpegts',  # Transport stream format
                f'http://{device_ip}:7000/stream'  # Stream to device
            ]
            
            self.stream_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            self.streaming = True
            decky.logger.info(f"Started streaming to {device_ip}")
            return True
            
        except Exception as e:
            decky.logger.error(f"Error starting stream: {e}")
            return False
    
    async def stop_stream(self):
        """Stop the current stream"""
        if self.stream_process:
            try:
                self.stream_process.terminate()
                self.stream_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.stream_process.kill()
            finally:
                self.stream_process = None
                self.streaming = False

class Plugin:
    def __init__(self):
        self.airplay_devices: List[AirplayDevice] = []
        self.streaming = False
        self.current_device: Optional[AirplayDevice] = None
        self.mdns_discovery = MDNSDiscovery()
        self.screen_capture = ScreenCapture()
        self.airplay_streamer = AirplayStreamer()
        self.temp_video_file = None

    # Scan for AirPlay devices on the network
    async def scan_airplay_devices(self) -> List[Dict[str, str]]:
        """Scan for AirPlay devices using mDNS discovery"""
        try:
            decky.logger.info("Scanning for AirPlay devices...")
            devices = await self.mdns_discovery.discover_airplay_devices()
            
            if not devices:
                # Add some mock devices for testing if none found
                decky.logger.info("No real devices found, adding test devices")
                devices = [
                    {"name": "Test Apple TV", "ip": "192.168.1.100", "type": "AppleTV (Test)"},
                ]
            
            decky.logger.info(f"Found {len(devices)} AirPlay devices")
            return devices
            
        except Exception as e:
            decky.logger.error(f"Error scanning for devices: {e}")
            return []

    # Check if we can capture the screen
    async def check_screen_capture_available(self) -> bool:
        """Check if screen capture is available and working"""
        try:
            return await self.screen_capture.check_capture_available()
        except Exception as e:
            decky.logger.error(f"Error checking screen capture: {e}")
            return False

    # Start AirPlay streaming
    async def start_airplay_stream(self, device_ip: str, device_name: str) -> Dict[str, any]:
        """Start streaming to an AirPlay device"""
        try:
            if self.streaming:
                return {"success": False, "error": "Already streaming"}

            # Check if screen capture is available
            capture_available = await self.check_screen_capture_available()
            if not capture_available:
                return {"success": False, "error": "Screen capture not available"}

            # Create device object
            device = AirplayDevice(device_name, device_ip)
            
            # Create temporary video file
            temp_dir = tempfile.gettempdir()
            self.temp_video_file = os.path.join(temp_dir, f"airdecky_stream_{int(time.time())}.mp4")
            
            # Start screen capture
            capture_started = await self.screen_capture.start_capture(self.temp_video_file)
            if not capture_started:
                return {"success": False, "error": "Failed to start screen capture"}
            
            # Give capture a moment to start
            await asyncio.sleep(2)
            
            # Start streaming to device
            stream_started = await self.airplay_streamer.start_stream(device_ip, self.temp_video_file)
            if not stream_started:
                await self.screen_capture.stop_capture()
                return {"success": False, "error": "Failed to start stream to device"}
            
            self.current_device = device
            self.streaming = True
            
            decky.logger.info(f"Started AirPlay stream to {device_name} ({device_ip})")
            
            # Emit event to update UI
            await decky.emit("streaming_status_changed", {
                "streaming": True,
                "device": device_name
            })
            
            return {"success": True, "device": device_name}
            
        except Exception as e:
            decky.logger.error(f"Error starting AirPlay stream: {e}")
            # Clean up on error
            await self.screen_capture.stop_capture()
            await self.airplay_streamer.stop_stream()
            return {"success": False, "error": str(e)}

    # Stop AirPlay streaming
    async def stop_airplay_stream(self) -> Dict[str, any]:
        """Stop the current AirPlay stream"""
        try:
            if not self.streaming:
                return {"success": False, "error": "Not currently streaming"}

            device_name = self.current_device.name if self.current_device else "Unknown"
            
            # Stop streaming
            await self.airplay_streamer.stop_stream()
            
            # Stop screen capture
            await self.screen_capture.stop_capture()
            
            # Clean up temporary file
            if self.temp_video_file and os.path.exists(self.temp_video_file):
                try:
                    os.remove(self.temp_video_file)
                except:
                    pass
                self.temp_video_file = None
            
            self.streaming = False
            self.current_device = None
            
            decky.logger.info("Stopped AirPlay stream")
            
            # Emit event to update UI
            await decky.emit("streaming_status_changed", {
                "streaming": False,
                "device": None
            })
            
            return {"success": True}
            
        except Exception as e:
            decky.logger.error(f"Error stopping AirPlay stream: {e}")
            return {"success": False, "error": str(e)}

    # Get current streaming status
    async def get_streaming_status(self) -> Dict[str, any]:
        """Get the current streaming status"""
        return {
            "streaming": self.streaming,
            "device": self.current_device.name if self.current_device else None,
            "device_ip": self.current_device.ip if self.current_device else None
        }

    # Test network connectivity to a device
    async def test_device_connection(self, device_ip: str) -> bool:
        """Test if we can connect to an AirPlay device"""
        try:
            # Test multiple AirPlay ports
            for port in [7000, 5000, 32498]:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(3)
                result = sock.connect_ex((device_ip, port))
                sock.close()
                
                if result == 0:
                    decky.logger.info(f"Successfully connected to {device_ip}:{port}")
                    return True
                    
            decky.logger.warning(f"Could not connect to {device_ip} on any AirPlay ports")
            return False
            
        except Exception as e:
            decky.logger.error(f"Error testing connection to {device_ip}: {e}")
            return False

    # Get system information relevant to AirPlay
    async def get_system_info(self) -> Dict[str, any]:
        """Get system information for debugging"""
        try:
            info = {
                "platform": os.uname().sysname,
                "kernel": os.uname().release,
                "architecture": os.uname().machine,
                "display_env": os.environ.get("DISPLAY", "Not set"),
                "wayland_display": os.environ.get("WAYLAND_DISPLAY", "Not set"),
            }
            
            # Check for required tools
            tools_check = {}
            tools = ['ffmpeg', 'gstreamer-launch-1.0', 'avahi-browse', 'wf-recorder', 'xwininfo']
            for tool in tools:
                result = subprocess.run(['which', tool], capture_output=True, text=True)
                tools_check[tool] = result.returncode == 0
            
            info["available_tools"] = tools_check
            
            # Check network interfaces
            try:
                result = subprocess.run(['ip', 'addr', 'show'], capture_output=True, text=True)
                info["network_interfaces"] = "Available" if result.returncode == 0 else "Not available"
            except:
                info["network_interfaces"] = "Not available"
            
            return info
            
        except Exception as e:
            decky.logger.error(f"Error getting system info: {e}")
            return {}

    # Asyncio-compatible long-running code, executed in a task when the plugin is loaded
    async def _main(self):
        decky.logger.info("AirDecky plugin started!")
        
        # Check system compatibility
        system_info = await self.get_system_info()
        decky.logger.info(f"System info: {system_info}")
        
        # Check if we have basic requirements
        capture_available = await self.check_screen_capture_available()
        if capture_available:
            decky.logger.info("Screen capture is available")
        else:
            decky.logger.warning("Screen capture may not be available - some features may not work")

    # Function called first during the unload process
    async def _unload(self):
        if self.streaming:
            await self.stop_airplay_stream()
        decky.logger.info("AirDecky plugin unloaded")

    # Function called after `_unload` during uninstall
    async def _uninstall(self):
        decky.logger.info("AirDecky plugin uninstalled")
        pass

    # Migrations that should be performed before entering `_main()`.
    async def _migration(self):
        decky.logger.info("Migrating")
        # Here's a migration example for logs:
        # - `~/.config/decky-template/template.log` will be migrated to `decky.decky_LOG_DIR/template.log`
        decky.migrate_logs(os.path.join(decky.DECKY_USER_HOME,
                                               ".config", "decky-template", "template.log"))
        # Here's a migration example for settings:
        # - `~/homebrew/settings/template.json` is migrated to `decky.decky_SETTINGS_DIR/template.json`
        # - `~/.config/decky-template/` all files and directories under this root are migrated to `decky.decky_SETTINGS_DIR/`
        decky.migrate_settings(
            os.path.join(decky.DECKY_HOME, "settings", "template.json"),
            os.path.join(decky.DECKY_USER_HOME, ".config", "decky-template"))
        # Here's a migration example for runtime data:
        # - `~/homebrew/template/` all files and directories under this root are migrated to `decky.decky_RUNTIME_DIR/`
        # - `~/.local/share/decky-template/` all files and directories under this root are migrated to `decky.decky_RUNTIME_DIR/`
        decky.migrate_runtime(
            os.path.join(decky.DECKY_HOME, "template"),
            os.path.join(decky.DECKY_USER_HOME, ".local", "share", "decky-template"))
