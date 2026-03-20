export interface SmartDevice { id: number; display_name: string; device_type: string; brand: string; status: string; battery_level: number | null; last_seen_at: string | null }
export interface AccessCode { id: number; code: string; code_name: string; valid_from: string; valid_until: string; status: string }
