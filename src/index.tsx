import {
  ButtonItem,
  PanelSection,
  PanelSectionRow,
  staticClasses,
  ConfirmModal,
  TextField
} from "@decky/ui";
import {
  callable,
  definePlugin,
  toaster
} from "@decky/api"
import { useState, useEffect } from "react";
import { FaWifi, FaStop, FaSync, FaTv } from "react-icons/fa";

interface AirPlayDevice {
  name: string;
  address: string;
  port: number;
  paired: boolean;
  model: string;
}

interface StreamingStatus {
  streaming: boolean;
  connected_device: string | null;
}

const discoverDevices = callable<[], AirPlayDevice[]>("discover_devices");
const pairDevice = callable<[address: string, port: number, pin: string], boolean>("pair_device");
const startStreaming = callable<[address: string, port: number], boolean>("start_streaming");
const stopStreaming = callable<[], boolean>("stop_streaming");
const getStreamingStatus = callable<[], StreamingStatus>("get_streaming_status");

const PinEntryModal = ({ device, onPair, onCancel }: {
  device: AirPlayDevice;
  onPair: (pin: string) => void;
  onCancel: () => void;
}) => {
  const [pin, setPin] = useState("");
  
  return (
    <ConfirmModal
      strTitle={`Pair with ${device.name}`}
      strDescription="Enter the PIN shown on your AirPlay device"
      strOKButtonText="Pair"
      strCancelButtonText="Cancel"
      onOK={() => onPair(pin)}
      onCancel={onCancel}
    >
      <TextField
        label="PIN"
        value={pin}
        onChange={(e: any) => setPin(e.target.value)}
        placeholder="Enter 4-digit PIN"
        maxLength={4}
      />
    </ConfirmModal>
  );
};

const DeviceListItem = ({ device, onConnect, onPair }: {
  device: AirPlayDevice;
  onConnect: (device: AirPlayDevice) => void;
  onPair: (device: AirPlayDevice) => void;
}) => {
  const buttonText = device.paired ? "Connect" : "Pair";
  const buttonAction = device.paired ? () => onConnect(device) : () => onPair(device);
  
  return (
    <PanelSectionRow>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", width: "100%" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <FaTv />
          <div>
            <div style={{ fontWeight: "bold" }}>{device.name}</div>
            <div style={{ fontSize: "12px", opacity: 0.7 }}>{device.model}</div>
          </div>
        </div>
        <ButtonItem layout="below" onClick={buttonAction}>
          {buttonText}
        </ButtonItem>
      </div>
    </PanelSectionRow>
  );
};

function Content() {
  const [devices, setDevices] = useState<AirPlayDevice[]>([]);
  const [streamingStatus, setStreamingStatus] = useState<StreamingStatus>({ streaming: false, connected_device: null });
  const [isScanning, setIsScanning] = useState(false);
  const [selectedDevice, setSelectedDevice] = useState<AirPlayDevice | null>(null);
  const [showPinModal, setShowPinModal] = useState(false);

  const refreshDevices = async () => {
    setIsScanning(true);
    try {
      const foundDevices = await discoverDevices();
      setDevices(foundDevices);
    } catch (error) {
      toaster.toast({
        title: "Discovery Failed",
        body: "Failed to discover AirPlay devices"
      });
    } finally {
      setIsScanning(false);
    }
  };

  const updateStatus = async () => {
    try {
      const status = await getStreamingStatus();
      setStreamingStatus(status);
    } catch (error) {
      console.error("Failed to get streaming status:", error);
    }
  };

  useEffect(() => {
    refreshDevices();
    updateStatus();
    
    const interval = setInterval(updateStatus, 2000);
    return () => clearInterval(interval);
  }, []);

  const handlePairDevice = (device: AirPlayDevice) => {
    setSelectedDevice(device);
    setShowPinModal(true);
  };

  const handlePinSubmit = async (pin: string) => {
    if (!selectedDevice) return;
    
    setShowPinModal(false);
    
    try {
      const success = await pairDevice(selectedDevice.address, selectedDevice.port, pin);
      
      if (success) {
        toaster.toast({
          title: "Pairing Successful",
          body: `Paired with ${selectedDevice.name}`
        });
        refreshDevices();
      } else {
        toaster.toast({
          title: "Pairing Failed",
          body: "Check the PIN and try again"
        });
      }
    } catch (error) {
      toaster.toast({
        title: "Pairing Error",
        body: "Failed to pair with device"
      });
    }
    
    setSelectedDevice(null);
  };

  const handleConnect = async (device: AirPlayDevice) => {
    try {
      const success = await startStreaming(device.address, device.port);
      
      if (success) {
        toaster.toast({
          title: "Streaming Started",
          body: `Connected to ${device.name}`
        });
        updateStatus();
      } else {
        toaster.toast({
          title: "Connection Failed",
          body: "Failed to start streaming"
        });
      }
    } catch (error) {
      toaster.toast({
        title: "Connection Error",
        body: "Failed to connect to device"
      });
    }
  };

  const handleDisconnect = async () => {
    try {
      const success = await stopStreaming();
      
      if (success) {
        toaster.toast({
          title: "Streaming Stopped",
          body: "Disconnected from AirPlay device"
        });
        updateStatus();
      }
    } catch (error) {
      toaster.toast({
        title: "Disconnect Error",
        body: "Failed to stop streaming"
      });
    }
  };

  return (
    <>
      <PanelSection title="AirPlay Status">
        <PanelSectionRow>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", width: "100%" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <div style={{ 
                width: "8px", 
                height: "8px", 
                borderRadius: "50%", 
                backgroundColor: streamingStatus.streaming ? "#4CAF50" : "#757575" 
              }} />
              <span>
                {streamingStatus.streaming 
                  ? `Streaming to ${streamingStatus.connected_device}` 
                  : "Not streaming"
                }
              </span>
            </div>
            {streamingStatus.streaming && (
              <ButtonItem layout="below" onClick={handleDisconnect}>
                <FaStop /> Stop
              </ButtonItem>
            )}
          </div>
        </PanelSectionRow>
      </PanelSection>

      <PanelSection title="Available Devices">
        <PanelSectionRow>
          <ButtonItem
            layout="below"
            onClick={refreshDevices}
            disabled={isScanning}
          >
            <FaSync style={{ animation: isScanning ? "spin 1s linear infinite" : "none" }} />
            {isScanning ? "Scanning..." : "Refresh Devices"}
          </ButtonItem>
        </PanelSectionRow>
        
        {devices.length === 0 ? (
          <PanelSectionRow>
            <div style={{ textAlign: "center", opacity: 0.7, padding: "20px" }}>
              {isScanning ? "Searching for AirPlay devices..." : "No AirPlay devices found"}
            </div>
          </PanelSectionRow>
        ) : (
          devices.map((device) => (
            <DeviceListItem
              key={`${device.address}:${device.port}`}
              device={device}
              onConnect={handleConnect}
              onPair={handlePairDevice}
            />
          ))
        )}
      </PanelSection>

      {showPinModal && selectedDevice && (
        <PinEntryModal
          device={selectedDevice}
          onPair={handlePinSubmit}
          onCancel={() => {
            setShowPinModal(false);
            setSelectedDevice(null);
          }}
        />
      )}
    </>
  );
}

export default definePlugin(() => {
  console.log("AirDecky plugin initializing");

  return {
    name: "AirDecky",
    titleView: <div className={staticClasses.Title}>AirPlay Screen Mirroring</div>,
    content: <Content />,
    icon: <FaWifi />,
    onDismount() {
      console.log("AirDecky plugin unloading");
    },
  };
});
