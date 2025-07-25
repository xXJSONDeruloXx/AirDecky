import {
  ButtonItem,
  PanelSection,
  PanelSectionRow,
  staticClasses,
  DialogButton,
  ModalRoot,
  showModal,
  Focusable,
  ConfirmModal
} from "@decky/ui";
import {
  addEventListener,
  removeEventListener,
  callable,
  definePlugin,
  toaster,
} from "@decky/api"
import { useState, useEffect } from "react";
import { FaDesktop, FaWifi, FaStop, FaSearch, FaExclamationTriangle, FaTv } from "react-icons/fa";

// Backend function calls
const scanAirplayDevices = callable<[], any[]>("scan_airplay_devices");
const startAirplayStream = callable<[deviceIp: string, deviceName: string], any>("start_airplay_stream");
const stopAirplayStream = callable<[], any>("stop_airplay_stream");
const getStreamingStatus = callable<[], any>("get_streaming_status");
const testDeviceConnection = callable<[deviceIp: string], boolean>("test_device_connection");
const getSystemInfo = callable<[], any>("get_system_info");
const checkScreenCaptureAvailable = callable<[], boolean>("check_screen_capture_available");

// Device selection modal
function DeviceSelectionModal({ devices, onSelect, onClose }: any) {
  const [selectedDevice, setSelectedDevice] = useState<any>(null);
  const [testing, setTesting] = useState<string | null>(null);

  const handleTestConnection = async (device: any) => {
    setTesting(device.ip);
    try {
      const connected = await testDeviceConnection(device.ip);
      toaster.toast({
        title: connected ? "Connection Successful" : "Connection Failed",
        body: connected 
          ? `Successfully connected to ${device.name}` 
          : `Could not connect to ${device.name}`,
        icon: connected ? <FaWifi /> : <FaExclamationTriangle />
      });
    } catch (error) {
      toaster.toast({
        title: "Connection Error",
        body: `Error testing connection: ${error}`,
        icon: <FaExclamationTriangle />
      });
    }
    setTesting(null);
  };

  const handleConnect = () => {
    if (selectedDevice) {
      onSelect(selectedDevice);
      onClose();
    }
  };

  return (
    <ModalRoot onCancel={onClose}>
      <div style={{ padding: "20px", minWidth: "400px" }}>
        <h2>Select AirPlay Device</h2>
        <div style={{ margin: "20px 0" }}>
          {devices.length === 0 ? (
            <div style={{ textAlign: "center", color: "#aaa" }}>
              <FaSearch style={{ fontSize: "48px", marginBottom: "10px" }} />
              <p>No AirPlay devices found</p>
              <p style={{ fontSize: "12px" }}>Make sure devices are on the same network</p>
            </div>
          ) : (
            devices.map((device: any, index: number) => (
              <Focusable
                key={index}
                style={{
                  padding: "10px",
                  margin: "5px 0",
                  border: selectedDevice?.ip === device.ip ? "2px solid #1a9fff" : "1px solid #333",
                  borderRadius: "4px",
                  cursor: "pointer",
                  backgroundColor: selectedDevice?.ip === device.ip ? "#1a9fff20" : "transparent"
                }}
                onClick={() => setSelectedDevice(device)}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <div>
                    <div style={{ fontWeight: "bold" }}>{device.name}</div>
                    <div style={{ fontSize: "12px", color: "#aaa" }}>
                      {device.ip} • {device.type}
                    </div>
                  </div>
                  <DialogButton
                    onClick={(e) => {
                      e.stopPropagation();
                      handleTestConnection(device);
                    }}
                    disabled={testing === device.ip}
                    style={{ minWidth: "80px" }}
                  >
                    {testing === device.ip ? "Testing..." : "Test"}
                  </DialogButton>
                </div>
              </Focusable>
            ))
          )}
        </div>
        <div style={{ display: "flex", gap: "10px", justifyContent: "flex-end" }}>
          <DialogButton onClick={onClose}>Cancel</DialogButton>
          <DialogButton
            onClick={handleConnect}
            disabled={!selectedDevice || devices.length === 0}
            style={{
              backgroundColor: selectedDevice ? "#1a9fff" : "#666",
              color: "white"
            }}
          >
            Connect
          </DialogButton>
        </div>
      </div>
    </ModalRoot>
  );
}

// System info modal
function SystemInfoModal({ onClose }: any) {
  const [systemInfo, setSystemInfo] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadSystemInfo = async () => {
      try {
        const info = await getSystemInfo();
        setSystemInfo(info);
      } catch (error) {
        console.error("Error loading system info:", error);
      }
      setLoading(false);
    };
    loadSystemInfo();
  }, []);

  return (
    <ModalRoot onCancel={onClose}>
      <div style={{ padding: "20px", minWidth: "500px", maxHeight: "400px", overflow: "auto" }}>
        <h2>System Information</h2>
        {loading ? (
          <div>Loading...</div>
        ) : systemInfo ? (
          <div style={{ fontFamily: "monospace", fontSize: "12px" }}>
            <h3>Platform</h3>
            <div>OS: {systemInfo.platform}</div>
            <div>Kernel: {systemInfo.kernel}</div>
            <div>Architecture: {systemInfo.architecture}</div>
            <div>Display: {systemInfo.display_env}</div>
            <div>Wayland: {systemInfo.wayland_display}</div>
            
            <h3 style={{ marginTop: "20px" }}>Available Tools</h3>
            {Object.entries(systemInfo.available_tools || {}).map(([tool, available]: any) => (
              <div key={tool}>
                {tool}: {available ? "✅ Available" : "❌ Not found"}
              </div>
            ))}
          </div>
        ) : (
          <div>Failed to load system information</div>
        )}
        <div style={{ display: "flex", justifyContent: "flex-end", marginTop: "20px" }}>
          <DialogButton onClick={onClose}>Close</DialogButton>
        </div>
      </div>
    </ModalRoot>
  );
}

// Main plugin content
function Content() {
  const [devices, setDevices] = useState<any[]>([]);
  const [streaming, setStreaming] = useState(false);
  const [currentDevice, setCurrentDevice] = useState<string | null>(null);
  const [scanning, setScanning] = useState(false);
  const [screenCaptureAvailable, setScreenCaptureAvailable] = useState(false);

  // Load initial status
  useEffect(() => {
    const loadStatus = async () => {
      try {
        const status = await getStreamingStatus();
        setStreaming(status.streaming);
        setCurrentDevice(status.device);

        const captureAvailable = await checkScreenCaptureAvailable();
        setScreenCaptureAvailable(captureAvailable);
      } catch (error) {
        console.error("Error loading status:", error);
      }
    };
    loadStatus();

    // Listen for streaming status changes
    const handleStreamingStatus = (data: any) => {
      setStreaming(data.streaming);
      setCurrentDevice(data.device);
    };

    addEventListener("streaming_status_changed", handleStreamingStatus);
    return () => removeEventListener("streaming_status_changed", handleStreamingStatus);
  }, []);

  const handleScanDevices = async () => {
    setScanning(true);
    try {
      const foundDevices = await scanAirplayDevices();
      setDevices(foundDevices);
      
      if (foundDevices.length === 0) {
        toaster.toast({
          title: "No Devices Found",
          body: "No AirPlay devices were found on the network",
          icon: <FaSearch />
        });
      } else {
        toaster.toast({
          title: "Devices Found",
          body: `Found ${foundDevices.length} AirPlay device(s)`,
          icon: <FaWifi />
        });
      }
    } catch (error) {
      toaster.toast({
        title: "Scan Failed",
        body: `Error scanning for devices: ${error}`,
        icon: <FaExclamationTriangle />
      });
    }
    setScanning(false);
  };

  const handleStartStreaming = (device: any) => {
    showModal(
      <ConfirmModal
        strTitle="Start AirPlay Streaming"
        strDescription={`Start streaming your Steam Deck screen to ${device.name}?`}
        onOK={async () => {
          try {
            const result = await startAirplayStream(device.ip, device.name);
            if (result.success) {
              toaster.toast({
                title: "Streaming Started",
                body: `Now streaming to ${device.name}`,
                icon: <FaTv />
              });
            } else {
              toaster.toast({
                title: "Streaming Failed",
                body: result.error || "Unknown error",
                icon: <FaExclamationTriangle />
              });
            }
          } catch (error) {
            toaster.toast({
              title: "Streaming Error",
              body: `Error starting stream: ${error}`,
              icon: <FaExclamationTriangle />
            });
          }
        }}
      />
    );
  };

  const handleStopStreaming = () => {
    showModal(
      <ConfirmModal
        strTitle="Stop AirPlay Streaming"
        strDescription="Stop the current AirPlay stream?"
        onOK={async () => {
          try {
            const result = await stopAirplayStream();
            if (result.success) {
              toaster.toast({
                title: "Streaming Stopped",
                body: "AirPlay streaming has been stopped",
                icon: <FaStop />
              });
            } else {
              toaster.toast({
                title: "Stop Failed",
                body: result.error || "Unknown error",
                icon: <FaExclamationTriangle />
              });
            }
          } catch (error) {
            toaster.toast({
              title: "Stop Error",
              body: `Error stopping stream: ${error}`,
              icon: <FaExclamationTriangle />
            });
          }
        }}
      />
    );
  };

  const handleShowDeviceSelection = () => {
    showModal(
      <DeviceSelectionModal
        devices={devices}
        onSelect={handleStartStreaming}
        onClose={() => {}}
      />
    );
  };

  const handleShowSystemInfo = () => {
    showModal(<SystemInfoModal onClose={() => {}} />);
  };

  return (
    <div style={{ padding: "20px" }}>
      {/* Warning about compatibility */}
      {!screenCaptureAvailable && (
        <div style={{
          padding: "10px",
          backgroundColor: "#ff6b6b20",
          border: "1px solid #ff6b6b",
          borderRadius: "4px",
          marginBottom: "20px"
        }}>
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <FaExclamationTriangle color="#ff6b6b" />
            <div>
              <strong>Compatibility Warning</strong>
              <div style={{ fontSize: "12px" }}>
                Screen capture may not be available. This is experimental software.
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Current status */}
      <PanelSection title="AirPlay Status">
        <PanelSectionRow>
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <FaDesktop />
            <div>
              <div style={{ fontWeight: "bold" }}>
                {streaming ? "Streaming Active" : "Not Streaming"}
              </div>
              {currentDevice && (
                <div style={{ fontSize: "12px", color: "#aaa" }}>
                  Connected to: {currentDevice}
                </div>
              )}
            </div>
          </div>
        </PanelSectionRow>
      </PanelSection>

      {/* Control buttons */}
      <PanelSection title="Controls">
        <PanelSectionRow>
          <ButtonItem
            layout="below"
            onClick={handleScanDevices}
            disabled={scanning}
          >
            <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
              <FaSearch />
              {scanning ? "Scanning..." : "Scan for Devices"}
            </div>
          </ButtonItem>
        </PanelSectionRow>

        {devices.length > 0 && !streaming && (
          <PanelSectionRow>
            <ButtonItem
              layout="below"
              onClick={handleShowDeviceSelection}
            >
              <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                <FaTv />
                Start Streaming
              </div>
            </ButtonItem>
          </PanelSectionRow>
        )}

        {streaming && (
          <PanelSectionRow>
            <ButtonItem
              layout="below"
              onClick={handleStopStreaming}
            >
              <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                <FaStop />
                Stop Streaming
              </div>
            </ButtonItem>
          </PanelSectionRow>
        )}
      </PanelSection>

      {/* Device list */}
      {devices.length > 0 && (
        <PanelSection title={`Found Devices (${devices.length})`}>
          {devices.map((device, index) => (
            <PanelSectionRow key={index}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <div>
                  <div style={{ fontWeight: "bold" }}>{device.name}</div>
                  <div style={{ fontSize: "12px", color: "#aaa" }}>
                    {device.ip} • {device.type}
                  </div>
                </div>
                {!streaming && (
                  <DialogButton
                    onClick={() => handleStartStreaming(device)}
                    style={{ minWidth: "80px" }}
                  >
                    Connect
                  </DialogButton>
                )}
              </div>
            </PanelSectionRow>
          ))}
        </PanelSection>
      )}

      {/* Debug section */}
      <PanelSection title="Debug">
        <PanelSectionRow>
          <ButtonItem
            layout="below"
            onClick={handleShowSystemInfo}
          >
            System Information
          </ButtonItem>
        </PanelSectionRow>
      </PanelSection>
    </div>
  );
}

export default definePlugin(() => {
  return {
    name: "AirDecky",
    title: <div className={staticClasses.Title}>AirDecky</div>,
    content: <Content />,
    icon: <FaTv />,
  };
});
