'use client';

import * as React from 'react';
import Box from '@mui/material/Box';
import Paper from '@mui/material/Paper';
import Typography from '@mui/material/Typography';
import Button from '@mui/material/Button';
import IconButton from '@mui/material/IconButton';
import Table from '@mui/material/Table';
import TableBody from '@mui/material/TableBody';
import TableCell from '@mui/material/TableCell';
import TableContainer from '@mui/material/TableContainer';
import TableHead from '@mui/material/TableHead';
import TableRow from '@mui/material/TableRow';
import Chip from '@mui/material/Chip';
import CircularProgress from '@mui/material/CircularProgress';
import Alert from '@mui/material/Alert';
import Dialog from '@mui/material/Dialog';
import DialogTitle from '@mui/material/DialogTitle';
import DialogContent from '@mui/material/DialogContent';
import DialogActions from '@mui/material/DialogActions';
import DialogContentText from '@mui/material/DialogContentText';
import VisibilityIcon from '@mui/icons-material/Visibility';
import DeleteIcon from '@mui/icons-material/Delete';
import PictureAsPdfIcon from '@mui/icons-material/PictureAsPdf';
import RefreshIcon from '@mui/icons-material/Refresh';
import Pagination from '@mui/material/Pagination';
import DocumentPreview from './DocumentPreview';
import { useToast } from '../ToastProvider';

interface Document {
  document_id: string;
  title: string;
  filename: string;
  file_size: number;
  created_at: string;
}

interface DocumentManagementProps {
  refreshTrigger?: number;
}

export default function DocumentManagement({ refreshTrigger }: DocumentManagementProps) {
  const [documents, setDocuments] = React.useState<Document[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState('');
  const [deleteDialogOpen, setDeleteDialogOpen] = React.useState(false);
  const [previewDialogOpen, setPreviewDialogOpen] = React.useState(false);
  const [selectedDocument, setSelectedDocument] = React.useState<Document | null>(null);
  const [deleting, setDeleting] = React.useState(false);
  const [currentPage, setCurrentPage] = React.useState(1);
  const [totalPages, setTotalPages] = React.useState(1);
  const [totalDocuments, setTotalDocuments] = React.useState(0);
  const { showToast } = useToast();

  React.useEffect(() => {
    fetchDocuments();
  }, [refreshTrigger, currentPage]);

  const fetchDocuments = async () => {
    setLoading(true);
    setError('');

    try {
      const response = await fetch(`/api/documents?page=${currentPage}&limit=10`);

      if (!response.ok) {
        if (response.status === 401) {
          throw new Error('Please sign in to access your documents');
        }
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.message || 'Failed to load documents');
      }

      const data = await response.json();
      setDocuments(data.documents || []);
      setTotalDocuments(data.pagination?.total || 0);
      setTotalPages(data.pagination?.pages || 1);
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to load documents';
      setError(errorMessage);
      showToast(`Failed to load documents: ${errorMessage}`, 'error');
    } finally {
      setLoading(false);
    }
  };

  const handlePreview = (document: Document) => {
    setSelectedDocument(document);
    setPreviewDialogOpen(true);
  };

  const handleDeleteClick = (document: Document) => {
    setSelectedDocument(document);
    setDeleteDialogOpen(true);
  };

  const handleDeleteConfirm = async () => {
    if (!selectedDocument) return;

    setDeleting(true);

    try {
      const response = await fetch(`/api/document/${selectedDocument.document_id}`, {
        method: 'DELETE',
      });

      if (!response.ok) {
        if (response.status === 401) {
          throw new Error('Please sign in to delete documents');
        }
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.message || 'Failed to delete document');
      }

      showToast('Document deleted successfully', 'success');

      setDocuments(prev => prev.filter(doc => doc.document_id !== selectedDocument.document_id));

      setDeleteDialogOpen(false);
      setSelectedDocument(null);
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to delete document';
      showToast(`Delete failed: ${errorMessage}`, 'error');
    } finally {
      setDeleting(false);
    }
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

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  if (loading) {
    return (
      <Paper sx={{ p: 4 }}>
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
            Loading documents...
          </Typography>
        </Box>
      </Paper>
    );
  }

  if (error) {
    return (
      <Paper sx={{ p: 4 }}>
        <Alert
          severity="error"
          action={
            <Button size="small" onClick={fetchDocuments}>
              Retry
            </Button>
          }
        >
          {error}
        </Alert>
      </Paper>
    );
  }

  return (
    <>
      <Paper sx={{ p: 4 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 3 }}>
          <Box>
            <Typography variant="h5" sx={{ fontWeight: 600 }}>
              Manage Documents
            </Typography>
            {totalDocuments > 0 && (
              <Typography variant="body2" color="text.secondary">
                {totalDocuments} document{totalDocuments !== 1 ? 's' : ''} • Page {currentPage} of {totalPages}
              </Typography>
            )}
          </Box>
          <Button
            startIcon={<RefreshIcon />}
            onClick={fetchDocuments}
            variant="outlined"
            size="small"
          >
            Refresh
          </Button>
        </Box>

        {documents.length === 0 ? (
          <Box sx={{
            textAlign: 'center',
            py: 6,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            gap: 2
          }}>
            <PictureAsPdfIcon sx={{ fontSize: 64, color: 'text.secondary' }} />
            <Typography variant="h6" color="text.secondary">
              No documents uploaded yet
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Upload your first PDF document to get started
            </Typography>
          </Box>
        ) : (
          <TableContainer>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>Document</TableCell>
                  <TableCell>Filename</TableCell>
                  <TableCell>Size</TableCell>
                  <TableCell>Uploaded</TableCell>
                  <TableCell align="right">Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {documents.map((document) => (
                  <TableRow key={document.document_id} hover>
                    <TableCell>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <PictureAsPdfIcon color="error" />
                        <Typography variant="body2" sx={{ fontWeight: 500 }}>
                          {document.title}
                        </Typography>
                      </Box>
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2" color="text.secondary">
                        {document.filename}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Chip
                        label={formatFileSize(document.file_size)}
                        size="small"
                        variant="outlined"
                      />
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2" color="text.secondary">
                        {formatDate(document.created_at)}
                      </Typography>
                    </TableCell>
                    <TableCell align="right">
                      <IconButton
                        size="small"
                        onClick={() => handlePreview(document)}
                        title="Preview content"
                      >
                        <VisibilityIcon />
                      </IconButton>
                      <IconButton
                        size="small"
                        onClick={() => handleDeleteClick(document)}
                        title="Delete document"
                        color="error"
                      >
                        <DeleteIcon />
                      </IconButton>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        )}

        {totalPages > 1 && (
          <Box sx={{ display: 'flex', justifyContent: 'center', mt: 3 }}>
            <Pagination
              count={totalPages}
              page={currentPage}
              onChange={(event, page) => setCurrentPage(page)}
              color="primary"
              size="medium"
              showFirstButton
              showLastButton
            />
          </Box>
        )}
      </Paper>

      {/* Delete Confirmation Dialog */}
      <Dialog
        open={deleteDialogOpen}
        onClose={() => !deleting && setDeleteDialogOpen(false)}
      >
        <DialogTitle>Delete Document</DialogTitle>
        <DialogContent>
          <DialogContentText>
            Are you sure you want to delete "{selectedDocument?.title}"?
            This action cannot be undone.
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button
            onClick={() => setDeleteDialogOpen(false)}
            disabled={deleting}
          >
            Cancel
          </Button>
          <Button
            onClick={handleDeleteConfirm}
            color="error"
            variant="contained"
            disabled={deleting}
            startIcon={deleting ? <CircularProgress size={16} /> : <DeleteIcon />}
          >
            {deleting ? 'Deleting...' : 'Delete'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Document Preview Dialog */}
      <DocumentPreview
        open={previewDialogOpen}
        onClose={() => setPreviewDialogOpen(false)}
        documentId={selectedDocument?.document_id || null}
        documentTitle={selectedDocument?.title}
      />
    </>
  );
}