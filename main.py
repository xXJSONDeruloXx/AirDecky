import os
import subprocess
import asyncio
import socket
from typing import Optional, List, Dict

# The decky plugin module is located at decky-loader/plugin
# For easy intellisense checkout the decky-loader code repo
# and add the `decky-loader/plugin/imports` path to `python.analysis.extraPaths` in `.vscode/settings.json`
import decky

class AirplayDevice:
    def __init__(self, name: str, ip: str, port: int = 7000):
        self.name = name
        self.ip = ip
        self.port = port
        self.connected = False

class Plugin:
    def __init__(self):
        self.airplay_devices: List[AirplayDevice] = []
        self.streaming = False
        self.current_device: Optional[AirplayDevice] = None

    # Scan for AirPlay devices on the network
    async def scan_airplay_devices(self) -> List[Dict[str, str]]:
        """Scan for AirPlay devices using zeroconf/mDNS discovery"""
        try:
            # This is a simplified implementation - would need proper mDNS discovery
            # For now, returning mock data to demonstrate the UI
            devices = [
                {"name": "Living Room Apple TV", "ip": "192.168.1.100", "type": "AppleTV"},
                {"name": "Bedroom Apple TV", "ip": "192.168.1.101", "type": "AppleTV"},
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
            # Try to check if we can access the display
            # This would need proper implementation with actual screen capture
            result = subprocess.run(['which', 'ffmpeg'], capture_output=True, text=True)
            has_ffmpeg = result.returncode == 0
            
            if not has_ffmpeg:
                decky.logger.warning("FFmpeg not found - screen capture may not work")
                return False
                
            return True
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
            
            # In a real implementation, this would:
            # 1. Start screen capture using X11/Wayland APIs
            # 2. Encode video using hardware encoder if available
            # 3. Establish RTSP connection to AirPlay device
            # 4. Start streaming H.264 video packets
            
            # For now, just simulate the process
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
            return {"success": False, "error": str(e)}

    # Stop AirPlay streaming
    async def stop_airplay_stream(self) -> Dict[str, any]:
        """Stop the current AirPlay stream"""
        try:
            if not self.streaming:
                return {"success": False, "error": "Not currently streaming"}

            # In a real implementation, this would:
            # 1. Stop the video capture
            # 2. Close RTSP connection
            # 3. Clean up resources
            
            device_name = self.current_device.name if self.current_device else "Unknown"
            
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
            # Simple TCP connection test
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(3)
            result = sock.connect_ex((device_ip, 7000))  # AirPlay port
            sock.close()
            return result == 0
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
            for tool in ['ffmpeg', 'gstreamer-launch-1.0', 'xwininfo']:
                result = subprocess.run(['which', tool], capture_output=True, text=True)
                tools_check[tool] = result.returncode == 0
            
            info["available_tools"] = tools_check
            
            return info
        except Exception as e:
            decky.logger.error(f"Error getting system info: {e}")
            return {}

    # Asyncio-compatible long-running code, executed in a task when the plugin is loaded
    async def _main(self):
        self.loop = asyncio.get_event_loop()
        decky.logger.info("AirDecky plugin started!")
        
        # Check system compatibility
        system_info = await self.get_system_info()
        decky.logger.info(f"System info: {system_info}")
        
        # Check if we have basic requirements
        capture_available = await self.check_screen_capture_available()
        if not capture_available:
            decky.logger.warning("Screen capture may not be available")

    # Function called first during the unload process
    async def _unload(self):
        if self.streaming:
            await self.stop_airplay_stream()
        decky.logger.info("AirDecky plugin unloaded")

    # Function called after `_unload` during uninstall
    async def _uninstall(self):
        decky.logger.info("AirDecky plugin uninstalled")
        pass
    # plugin that may remain on the system
    async def _uninstall(self):
        decky.logger.info("Goodbye World!")
        pass

    async def start_timer(self):
        self.loop.create_task(self.long_running())

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
