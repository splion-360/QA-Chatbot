'use client';

import * as React from 'react';
import Box from '@mui/material/Box';
import Paper from '@mui/material/Paper';
import Typography from '@mui/material/Typography';
import TextField from '@mui/material/TextField';
import Button from '@mui/material/Button';
import Stack from '@mui/material/Stack';
import InfinityLoader from '../InfinityLoader';
import Alert from '@mui/material/Alert';
import CloudUploadIcon from '@mui/icons-material/CloudUpload';
import PictureAsPdfIcon from '@mui/icons-material/PictureAsPdf';
import { useToast } from '../ToastProvider';

interface DocumentUploadProps {
  onUploadSuccess?: () => void;
}

export default function DocumentUpload({ onUploadSuccess }: DocumentUploadProps) {
  const [title, setTitle] = React.useState('');
  const [selectedFile, setSelectedFile] = React.useState<File | null>(null);
  const [uploading, setUploading] = React.useState(false);
  const [error, setError] = React.useState('');
  const [dragOver, setDragOver] = React.useState(false);
  const { showToast } = useToast();
  const fileInputRef = React.useRef<HTMLInputElement>(null);

  const validateFile = (file: File) => {
    if (file.type !== 'application/pdf') {
      setError('Please select a PDF file only');
      return false;
    }

    if (file.size > 100 * 1024 * 1024) { // 100MB limit
      setError('File size must be less than 100MB');
      return false;
    }

    setError('');
    return true;
  };

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    if (validateFile(file)) {
      setSelectedFile(file);
      if (!title) {
        setTitle(file.name.replace('.pdf', ''));
      }
    } else {
      setSelectedFile(null);
    }
  };

  const handleDragOver = (event: React.DragEvent) => {
    event.preventDefault();
    setDragOver(true);
  };

  const handleDragLeave = (event: React.DragEvent) => {
    event.preventDefault();
    setDragOver(false);
  };

  const handleDrop = (event: React.DragEvent) => {
    event.preventDefault();
    setDragOver(false);

    const files = event.dataTransfer.files;
    const file = files[0];

    if (file && validateFile(file)) {
      setSelectedFile(file);
      if (!title) {
        setTitle(file.name.replace('.pdf', ''));
      }
    } else {
      setSelectedFile(null);
    }
  };

  const handleUpload = async () => {
    console.log('Upload button clicked', { selectedFile: !!selectedFile, title: title.trim(), uploading });

    if (!selectedFile || !title.trim()) {
      setError('Please provide both a title and select a PDF file');
      return;
    }

    const startTime = Date.now();
    setUploading(true);
    setError('');

    try {
      const formData = new FormData();
      formData.append('file', selectedFile);
      formData.append('title', title.trim());

      const response = await fetch('/api/documents', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        if (response.status === 401) {
          throw new Error('Please sign in to upload documents');
        }
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.message || 'Upload failed');
      }

      showToast('Document uploaded successfully and will be available soon!', 'success');

      // Reset form only on successful upload
      setTitle('');
      setSelectedFile(null);
      setError('');
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }

      // Notify parent component
      if (onUploadSuccess) {
        onUploadSuccess();
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Upload failed';
      setError(errorMessage);
      showToast(`Upload failed: ${errorMessage}`, 'error');
      // Don't reset form on error so user can retry
    } finally {
      const elapsedTime = Date.now() - startTime;
      const minDuration = 2000;
      
      if (elapsedTime < minDuration) {
        setTimeout(() => setUploading(false), minDuration - elapsedTime);
      } else {
        setUploading(false);
      }
    }
  };

  const handleRemoveFile = () => {
    setSelectedFile(null);
    setError('');
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  return (
    <Paper sx={{ p: 4, borderRadius: 2, elevation: 1 }}>
      <Stack spacing={4}>
        <TextField
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          fullWidth
          required
          placeholder="Enter a descriptive title for your document"
          disabled={uploading}
          variant="outlined"
          sx={{
            '& .MuiOutlinedInput-root': {
              borderRadius: 2,
            }
          }}
        />

        <Box>
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf"
            onChange={handleFileSelect}
            style={{ display: 'none' }}
            disabled={uploading}
          />

          {!selectedFile ? (
            <Button
              variant="outlined"
              onClick={() => fileInputRef.current?.click()}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
              startIcon={<CloudUploadIcon />}
              sx={{
                height: 120,
                width: '100%',
                borderStyle: 'dashed',
                borderWidth: 2,
                borderRadius: 2,
                borderColor: dragOver ? 'primary.main' : 'text.secondary',
                color: dragOver ? 'primary.main' : 'text.primary',
                bgcolor: dragOver ? 'action.hover' : 'background.paper',
                flexDirection: 'column',
                gap: 1,
                transition: 'all 0.2s ease',
                '&:hover': {
                  borderColor: 'primary.main',
                  bgcolor: 'action.hover',
                  color: 'primary.main',
                }
              }}
              disabled={uploading}
            >
              <Typography variant="body1" sx={{ fontWeight: 500 }}>
                {dragOver ? 'Drop PDF file here' : 'Click to select PDF file or drag & drop'}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                Maximum file size: 100MB
              </Typography>
            </Button>
          ) : (
            <Paper
              variant="outlined"
              sx={{
                p: 2,
                display: 'flex',
                alignItems: 'center',
                gap: 2,
                bgcolor: 'background.default',
                borderRadius: 2,
                border: '1px solid',
                borderColor: 'divider'
              }}
            >
              <PictureAsPdfIcon color="error" sx={{ fontSize: 32 }} />
              <Box sx={{ flexGrow: 1 }}>
                <Typography variant="body1" sx={{ fontWeight: 500 }}>
                  {selectedFile.name}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  {(selectedFile.size / (1024 * 1024)).toFixed(2)} MB
                </Typography>
              </Box>
              <Button
                size="small"
                onClick={handleRemoveFile}
                disabled={uploading}
              >
                Remove
              </Button>
            </Paper>
          )}
        </Box>

        {error && (
          <Alert severity="error">
            {error}
          </Alert>
        )}

        {uploading && (
          <Box>
            <Typography variant="body2" gutterBottom>
              Uploading document...
            </Typography>
            <InfinityLoader />
          </Box>
        )}

        <Button
          variant="outlined"
          onClick={handleUpload}
          disabled={!selectedFile || !title.trim() || uploading}
          startIcon={<CloudUploadIcon />}
          size="small"
          sx={{
            alignSelf: 'flex-start',
            textTransform: 'none',
            fontWeight: 500,
            borderRadius: 1.5,
            px: 2,
            py: 0.75,
          }}
        >
          {uploading ? 'Uploading...' : 'Upload Document'}
        </Button>

        {/* Debug info */}
      </Stack>
    </Paper>
  );
}