import React from 'react'
import FileUploader from './FileUploader'

interface UploadZoneProps {
  onUploadStart?: (file: File) => void
  onUploadProgress?: (percent: number) => void
  onUploadSuccess?: (response: any) => void
  onUploadError?: (error: Error) => void
  maxSize?: number // MB
  accept?: string
  disabled?: boolean
}

const UploadZone: React.FC<UploadZoneProps> = ({
  onUploadStart,
  onUploadProgress,
  onUploadSuccess,
  onUploadError,
  maxSize = 50,
  accept = '.json',
  disabled = false
}) => {
  return (
    <FileUploader 
      onUploadStart={onUploadStart}
      onUploadProgress={onUploadProgress}
      onUploadSuccess={onUploadSuccess}
      onUploadError={onUploadError}
      maxSize={maxSize}
      accept={accept}
      disabled={disabled}
    />
  )
}

export default UploadZone