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
import InfinityLoader from '../InfinityLoader';
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
  size: number;
  created_at: string;
}

interface DocumentManagementProps {
  refreshTrigger?: number;
  searchQuery?: string;
  isSearchActive?: boolean;
}

// Global cache outside component to persist across mounts/unmounts
let documentsCache: Record<string, {
  documents: Document[];
  totalDocuments: number;
  totalPages: number;
  lastFetched: number | null;
}> = {};

export default function DocumentManagement({ refreshTrigger, searchQuery = '', isSearchActive = false }: DocumentManagementProps) {
  const [currentPage, setCurrentPage] = React.useState(1);
  const cacheKey = `${searchQuery}-${currentPage}`;
  const currentCache = documentsCache[cacheKey] || { documents: [], totalDocuments: 0, totalPages: 1, lastFetched: null };

  const [documents, setDocuments] = React.useState<Document[]>(currentCache.documents);
  const [loading, setLoading] = React.useState(currentCache.documents.length === 0 && currentCache.lastFetched === null);
  const [error, setError] = React.useState('');
  const [deleteDialogOpen, setDeleteDialogOpen] = React.useState(false);
  const [previewDialogOpen, setPreviewDialogOpen] = React.useState(false);
  const [selectedDocument, setSelectedDocument] = React.useState<Document | null>(null);
  const [deleting, setDeleting] = React.useState(false);
  const [totalPages, setTotalPages] = React.useState(currentCache.totalPages);
  const [totalDocuments, setTotalDocuments] = React.useState(currentCache.totalDocuments);
  const [lastFetched, setLastFetched] = React.useState<number | null>(currentCache.lastFetched);
  const { showToast } = useToast();

  React.useEffect(() => {
    setCurrentPage(1);
  }, [searchQuery]);

  React.useEffect(() => {
    const pageCache = documentsCache[cacheKey];
    const now = Date.now();
    const oneMinute = 60 * 1000;

    if (!pageCache || !pageCache.lastFetched || (now - pageCache.lastFetched) >= oneMinute) {
      fetchDocuments();
    } else {
      setDocuments(pageCache.documents);
      setTotalDocuments(pageCache.totalDocuments);
      setTotalPages(pageCache.totalPages);
      setLastFetched(pageCache.lastFetched);
      setLoading(false);
    }
  }, [refreshTrigger, currentPage, searchQuery]);

  const fetchDocuments = async () => {
    setLoading(true);
    setError('');

    try {
      const searchParams = new URLSearchParams({
        page: currentPage.toString(),
        limit: '10'
      });
      
      if (searchQuery.trim()) {
        searchParams.append('search', searchQuery.trim());
        searchParams.append('search_type', 'title');
      }
      
      const response = await fetch(`/api/documents?${searchParams.toString()}`);

      if (!response.ok) {
        if (response.status === 401) {
          throw new Error('Please sign in to access your documents');
        }
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.message || 'Failed to load documents');
      }

      const data = await response.json();
      const newDocuments = data.documents || [];
      const newTotal = data.pagination?.total || 0;
      const newPages = data.pagination?.pages || 1;
      const now = Date.now();

      setDocuments(newDocuments);
      setTotalDocuments(newTotal);
      setTotalPages(newPages);
      setLastFetched(now);

      // Update global cache for current search and page
      documentsCache[cacheKey] = {
        documents: newDocuments,
        totalDocuments: newTotal,
        totalPages: newPages,
        lastFetched: now,
      };
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to load documents';
      setError(errorMessage);
      showToast(`Failed to load documents: ${errorMessage}`, 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleManualRefresh = async () => {
    const startTime = Date.now();
    setLastFetched(null);
    if (documentsCache[cacheKey]) {
      documentsCache[cacheKey].lastFetched = null;
    }
    
    await fetchDocuments();
    
    const elapsedTime = Date.now() - startTime;
    const minDuration = 2000;
    
    if (elapsedTime < minDuration) {
      await new Promise(resolve => setTimeout(resolve, minDuration - elapsedTime));
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

    const startTime = Date.now();
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

      const filteredDocuments = documents.filter(doc => doc.document_id !== selectedDocument.document_id);
      const newTotal = totalDocuments - 1;
      const now = Date.now();

      setDocuments(filteredDocuments);
      setTotalDocuments(newTotal);
      setLastFetched(now);

      // Update global cache for current search and page
      documentsCache[cacheKey] = {
        documents: filteredDocuments,
        totalDocuments: newTotal,
        totalPages,
        lastFetched: now,
      };

      setDeleteDialogOpen(false);
      setSelectedDocument(null);
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to delete document';
      showToast(`Delete failed: ${errorMessage}`, 'error');
    } finally {
      const elapsedTime = Date.now() - startTime;
      const minDuration = 2000;
      
      if (elapsedTime < minDuration) {
        setTimeout(() => setDeleting(false), minDuration - elapsedTime);
      } else {
        setDeleting(false);
      }
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
          <InfinityLoader />
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
            <Button size="small" onClick={handleManualRefresh}>
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
              {isSearchActive ? `Search Results` : 'Available Documents'}
            </Typography>

            <Typography variant="body2" color="text.secondary">
              {isSearchActive 
                ? `${totalDocuments} result${totalDocuments !== 1 ? 's' : ''} for "${searchQuery}"${totalPages > 1 ? ` • Page ${currentPage} of ${totalPages}` : ''}`
                : `Page ${currentPage} of ${totalPages}`
              }
            </Typography>

          </Box>
          <Button
            onClick={handleManualRefresh}
            variant="outlined"
            size="small"
            sx={{ minWidth: 40, width: 40, height: 32 }}
            title="Refresh documents"
          >
            <RefreshIcon fontSize="small" />
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
              {isSearchActive ? 'No documents found' : 'No documents uploaded yet'}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              {isSearchActive 
                ? `No documents match your search for "${searchQuery}"`
                : 'Upload your first PDF document to get started'
              }
            </Typography>
          </Box>
        ) : (
          <TableContainer>
            <Table sx={{ border: '1px solid', borderColor: 'divider', '& .MuiTableCell-root': { borderBottom: '1px solid', borderColor: 'divider' } }} size="small">
              <TableHead>
                <TableRow sx={{ bgcolor: 'action.hover' }}>
                  <TableCell sx={{ fontWeight: 600, borderRight: '1px solid', borderColor: 'divider', py: 1 }}>Title</TableCell>
                  <TableCell align="center" sx={{ fontWeight: 600, borderRight: '1px solid', borderColor: 'divider', py: 1 }}>Size</TableCell>
                  <TableCell align="center" sx={{ fontWeight: 600, borderRight: '1px solid', borderColor: 'divider', py: 1 }}>Uploaded</TableCell>
                  <TableCell align="center" sx={{ fontWeight: 600, py: 1 }}>Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {documents.map((document) => (
                  <TableRow key={document.document_id} hover>
                    <TableCell sx={{ borderRight: '1px solid', borderColor: 'divider', py: 1 }}>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <PictureAsPdfIcon color="error" fontSize="small" />
                        <Typography variant="body2" sx={{ fontWeight: 500 }}>
                          {document.title}
                        </Typography>
                      </Box>
                    </TableCell>

                    <TableCell align="center" sx={{ borderRight: '1px solid', borderColor: 'divider', py: 1 }}>
                      <Chip
                        label={formatFileSize(document.size)}
                        size="small"
                        variant="outlined"
                      />
                    </TableCell>
                    <TableCell align="center" sx={{ borderRight: '1px solid', borderColor: 'divider', py: 1 }}>
                      <Typography variant="body2" color="text.secondary">
                        {formatDate(document.created_at)}
                      </Typography>
                    </TableCell>
                    <TableCell align="center" sx={{ py: 1 }}>
                      <Box sx={{ display: 'flex', justifyContent: 'center', gap: 0.5 }}>
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
                      </Box>
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
              onChange={(event, page) => {
                setCurrentPage(page);
              }}
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
            startIcon={deleting ? <InfinityLoader size={16} /> : <DeleteIcon />}
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