/**
 * Shared TypeScript types for the Salon Turn Manager.
 */

export type TechnicianStatus = 'AVAILABLE' | 'BUSY' | 'ON_BREAK';

export interface Technician {
    id: number;
    name: string;
    status: TechnicianStatus;
    queue_position: number;
    is_active: boolean;
    status_start_time?: string;
}

export interface AssignResponse {
    assigned_tech_id: number;
    assigned_tech_name: string;
    client: string;
}

export interface CompleteResponse {
    completed_tech_id: number;
    new_queue_position: number;
}

export interface ToggleActiveResponse {
    tech_id: number;
    is_active: boolean;
}

export interface ReorderResponse {
    status: string;
}

export interface RemoveResponse {
    status: string;
    tech_id: number;
}

export interface WebSocketMessage {
    type: 'init' | 'update';
    technicians: Technician[];
}
