'use client';

import * as React from 'react';
import Dialog from '@mui/material/Dialog';
import DialogTitle from '@mui/material/DialogTitle';
import DialogContent from '@mui/material/DialogContent';
import DialogActions from '@mui/material/DialogActions';
import Button from '@mui/material/Button';
import Typography from '@mui/material/Typography';
import Box from '@mui/material/Box';
import CircularProgress from '@mui/material/CircularProgress';
import Alert from '@mui/material/Alert';
import PictureAsPdfIcon from '@mui/icons-material/PictureAsPdf';
import { useToast } from '../ToastProvider';

interface DocumentPreviewProps {
  open: boolean;
  onClose: () => void;
  documentId: string | null;
  documentTitle?: string;
}

interface DocumentContent {
  document_id: string;
  title: string;
  preview: string;
  total_length: number;
  chunks: number;
}

export default function DocumentPreview({ 
  open, 
  onClose, 
  documentId, 
  documentTitle 
}: DocumentPreviewProps) {
  const [content, setContent] = React.useState<DocumentContent | null>(null);
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState('');
  const { showToast } = useToast();

  React.useEffect(() => {
    if (open && documentId) {
      fetchDocumentContent();
    }
  }, [open, documentId]);

  const fetchDocumentContent = async () => {
    if (!documentId) return;

    setLoading(true);
    setError('');
    setContent(null);

    try {
      const response = await fetch(`/api/document/${documentId}`);
      
      if (!response.ok) {
        if (response.status === 401) {
          throw new Error('Please sign in to view document content');
        }
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.message || 'Failed to load document content');
      }

      const data = await response.json();
      setContent(data);
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to load document';
      setError(errorMessage);
      showToast(`Failed to load document: ${errorMessage}`, 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleClose = () => {
    setContent(null);
    setError('');
    onClose();
  };

  const formatDate = (dateString: string) => {
    try {
      return new Date(dateString).toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      });
    } catch (error) {
      return 'Unknown';
    }
  };

  return (
    <Dialog 
      open={open} 
      onClose={handleClose}
      maxWidth="md"
      fullWidth
      PaperProps={{
        sx: { borderRadius: 2, height: '80vh' }
      }}
    >
      <DialogTitle sx={{ pb: 1 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <PictureAsPdfIcon color="error" />
          <Box>
            <Typography variant="h6" component="div">
              {documentTitle || 'Document Preview'}
            </Typography>
            {content && (
              <Typography variant="caption" color="text.secondary">
                {content.chunks} chunks • {content.total_length} characters
              </Typography>
            )}
          </Box>
        </Box>
      </DialogTitle>
      
      <DialogContent sx={{ pb: 1 }}>
        {loading ? (
          <Box sx={{ 
            display: 'flex', 
            flexDirection: 'column',
            alignItems: 'center', 
            justifyContent: 'center',
            py: 4,
            gap: 2
          }}>
            <CircularProgress />
            <Typography color="text.secondary">
              Loading document content...
            </Typography>
          </Box>
        ) : error ? (
          <Alert severity="error">
            {error}
          </Alert>
        ) : content ? (
          <Box>
            <Typography variant="subtitle2" gutterBottom sx={{ fontWeight: 600 }}>
              Content Preview (First 500 characters)
            </Typography>
            <Box
              sx={{
                p: 2,
                bgcolor: 'grey.50',
                borderRadius: 1,
                border: '1px solid',
                borderColor: 'divider',
                maxHeight: '400px',
                overflow: 'auto',
                fontFamily: 'monospace',
                fontSize: '0.875rem',
                lineHeight: 1.5,
                whiteSpace: 'pre-wrap',
              }}
            >
              {content.preview}
              {content.preview.length >= 500 && (
                <Typography 
                  variant="caption" 
                  sx={{ 
                    display: 'block', 
                    mt: 2, 
                    fontStyle: 'italic',
                    color: 'text.secondary'
                  }}
                >
                  ... (content truncated to 500 characters)
                </Typography>
              )}
            </Box>
          </Box>
        ) : null}
      </DialogContent>
      
      <DialogActions sx={{ p: 3, pt: 1 }}>
        <Button onClick={handleClose}>
          Close
        </Button>
      </DialogActions>
    </Dialog>
  );
}