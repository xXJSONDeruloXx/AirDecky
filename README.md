# AirDecky - AirPlay Screen Mirroring for Steam Deck

[![Chat](https://img.shields.io/badge/chat-on%20discord-7289da.svg)](https://deckbrew.xyz/discord)

Stream your Steam Deck screen to AirPlay devices like Apple TV, making couch co-op and spectating easier than ever.

## Features

- **Device Discovery**: Automatically find AirPlay devices on your network
- **Easy Pairing**: Simple PIN-based pairing with AirPlay devices  
- **Screen Mirroring**: Stream your Steam Deck display in real-time
- **Hardware Accelerated**: Optimized for Steam Deck's hardware capabilities
- **Low Latency**: Minimal delay for responsive gaming experience

## Requirements

- Steam Deck with Decky Loader installed
- AirPlay-compatible device (Apple TV, HomePod, etc.)
- Both devices on the same local network

## Installation

1. Install via the Decky Plugin Store (recommended)
2. Or manually install by placing the plugin files in your Decky plugins directory

## Usage

1. Open the AirDecky plugin from the Decky menu
2. Tap "Refresh Devices" to scan for AirPlay devices
3. Select a device and enter the PIN shown on your AirPlay device
4. Once paired, tap "Connect" to start streaming
5. Use "Stop" to end the streaming session

## Technical Details

### Architecture
- **Frontend**: React/TypeScript UI for device management
- **Backend**: Python service handling AirPlay protocol and screen capture
- **Screen Capture**: FFmpeg-based capture with hardware acceleration
- **Discovery**: Bonjour/mDNS service discovery for AirPlay devices

### Dependencies
- `ffmpeg` - Video capture and encoding
- `zeroconf` - Network service discovery
- `requests` - HTTP communication
- `Pillow` - Image processing

## Troubleshooting

### No devices found
- Ensure both Steam Deck and AirPlay device are on the same network
- Check that AirPlay is enabled on your target device
- Try refreshing the device list

### Connection failed  
- Verify the PIN entered matches what's displayed on the AirPlay device
- Ensure no other device is currently streaming to the same AirPlay device
- Check network connectivity between devices

### Poor streaming quality
- Move closer to your Wi-Fi router for better signal strength
- Close other network-intensive applications
- Try lowering the streaming quality in settings

## Development

### Building from Source

```bash
# Install dependencies
pnpm install

# Build the plugin
pnpm run build

# Deploy to Steam Deck (requires proper SSH setup)
# See original template documentation for deployment setup
```

### Dependencies Setup

The plugin automatically handles Python dependencies, but for manual installation:

```bash
./install_deps.sh
```

## Contributing

Contributions welcome! Please feel free to submit issues and pull requests.

## License

BSD 3-Clause License - see LICENSE file for details.

## Acknowledgments

- Built on the [Decky Plugin Template](https://github.com/SteamDeckHomebrew/decky-plugin-template)
- Inspired by existing AirPlay implementations like [OpenAirplay](https://github.com/openairplay/openairplay) and [PyATV](https://github.com/postlund/pyatv)

We cannot and will not distribute your plugin on the Plugin Store if it's license requires it's inclusion but you have not included a license to be re-distributed with your plugin in the root of your git repository.
