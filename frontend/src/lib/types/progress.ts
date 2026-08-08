export type ProgressStepStatus = 'active' | 'done'

export interface ProgressStep {
  id: string
  message: string
  status: ProgressStepStatus
}
