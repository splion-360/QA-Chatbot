'use client';

import * as React from 'react';
import Dialog from '@mui/material/Dialog';
import DialogTitle from '@mui/material/DialogTitle';
import DialogContent from '@mui/material/DialogContent';
import DialogActions from '@mui/material/DialogActions';
import Button from '@mui/material/Button';
import Typography from '@mui/material/Typography';
import Box from '@mui/material/Box';
import InfinityLoader from '../InfinityLoader';
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

    const startTime = Date.now();
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
      const elapsedTime = Date.now() - startTime;
      const minDuration = 2000;

      if (elapsedTime < minDuration) {
        setTimeout(() => setLoading(false), minDuration - elapsedTime);
      } else {
        setLoading(false);
      }
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
      maxWidth={false}

    >
      <DialogTitle sx={{ p: 2, pb: 1, bgcolor: 'background.paper' }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Box sx={{
            bgcolor: 'error.main',
            borderRadius: 1,
            p: 0.5,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center'
          }}>
            <PictureAsPdfIcon sx={{ color: 'white', fontSize: 20 }} />
          </Box>
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

      <DialogContent sx={{ p: 0, bgcolor: 'transparent' }}>
        {loading ? (
          <Box sx={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            py: 4,
            gap: 2,
          }}>
            <InfinityLoader />
            <Typography color="text.secondary">
              Loading document content...
            </Typography>
          </Box>
        ) : error ? (
          <Alert severity="error">
            {error}
          </Alert>
        ) : content ? (
          <Box
            sx={{
              p: 3,
              bgcolor: 'background.paper',
              borderRadius: 0.5,
              border: '1px solid',
              borderColor: 'divider',
              height: '500px',
              width: '800px',
              overflow: 'hidden',
              fontFamily: 'system-ui, -apple-system, sans-serif',
              fontSize: '0.96rem',
              lineHeight: 1.4,
              whiteSpace: 'pre-wrap',
              color: 'text.primary',
              textAlign: 'left',
            }}
          >
            {content.preview}

          </Box>
        ) : null}
      </DialogContent>

      <DialogActions sx={{ p: 2, pt: 1, bgcolor: 'background.paper' }}>
        <Button onClick={handleClose}>
          Close
        </Button>
      </DialogActions>
    </Dialog>
  );
}