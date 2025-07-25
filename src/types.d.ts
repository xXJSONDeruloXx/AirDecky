declare module "*.svg" {
  const content: string;
  export default content;
}

declare module "*.png" {
  const content: string;
  export default content;
}

declare module "*.css" {
  const content: Record<string, string>;
  export default content;
}

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

declare module "*.jpg" {
  const content: string;
  export default content;
}
