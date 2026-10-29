export type PlatformCommand = {
  id: string;
  label: string;
  detail: string;
  group: string;
  keywords?: string;
  disabled?: boolean;
  disabledReason?: string;
  run: () => void;
};
