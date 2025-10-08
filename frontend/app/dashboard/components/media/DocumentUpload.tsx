'use client';

import * as React from 'react';
import Box from '@mui/material/Box';
import Paper from '@mui/material/Paper';
import Typography from '@mui/material/Typography';
import TextField from '@mui/material/TextField';
import Button from '@mui/material/Button';
import Stack from '@mui/material/Stack';
import LinearProgress from '@mui/material/LinearProgress';
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
  const { showToast } = useToast();
  const fileInputRef = React.useRef<HTMLInputElement>(null);

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    if (file.type !== 'application/pdf') {
      setError('Please select a PDF file only');
      setSelectedFile(null);
      return;
    }

    if (file.size > 10 * 1024 * 1024) { // 10MB limit
      setError('File size must be less than 10MB');
      setSelectedFile(null);
      return;
    }

    setError('');
    setSelectedFile(file);
  };

  const handleUpload = async () => {
    console.log('Upload button clicked', { selectedFile: !!selectedFile, title: title.trim(), uploading });
    
    if (!selectedFile || !title.trim()) {
      setError('Please provide both a title and select a PDF file');
      return;
    }

    setUploading(true);
    setError('');

    try {
      const formData = new FormData();
      formData.append('file', selectedFile);
      formData.append('title', title.trim());

      const response = await fetch('/api/document', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.message || 'Upload failed');
      }

      showToast('Document uploaded successfully!', 'success');
      
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
      setUploading(false);
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
              startIcon={<CloudUploadIcon />}
              sx={{ 
                height: 120,
                width: '100%',
                borderStyle: 'dashed',
                borderWidth: 2,
                borderRadius: 2,
                borderColor: 'text.secondary',
                color: 'text.primary',
                bgcolor: 'background.paper',
                flexDirection: 'column',
                gap: 1,
                '&:hover': {
                  borderColor: 'primary.main',
                  bgcolor: 'action.hover',
                  color: 'primary.main',
                }
              }}
              disabled={uploading}
            >
              <Typography variant="body1" sx={{ fontWeight: 500 }}>Click to select PDF file</Typography>
              <Typography variant="caption" color="text.secondary">
                Maximum file size: 10MB
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
            <LinearProgress />
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
        <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.7rem' }}>
          Debug: File={!!selectedFile ? 'Yes' : 'No'}, Title={title.length > 0 ? 'Yes' : 'No'}, Uploading={uploading ? 'Yes' : 'No'}
        </Typography>
      </Stack>
    </Paper>
  );
}