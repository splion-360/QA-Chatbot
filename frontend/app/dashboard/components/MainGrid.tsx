'use client';

import * as React from 'react';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Paper from '@mui/material/Paper';
import Tabs from '@mui/material/Tabs';
import Tab from '@mui/material/Tab';
import ChatContainer from './chat/ChatContainer';
import DocumentUpload from './media/DocumentUpload';
import DocumentManagement from './media/DocumentManagement';
import Copyright from '../internals/components/Copyright';

interface MainGridProps {
  selectedTab?: string;
}

function MediaContent() {
  const [activeTab, setActiveTab] = React.useState(0);
  const [refreshTrigger, setRefreshTrigger] = React.useState(0);

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setActiveTab(newValue);
  };

  const handleUploadSuccess = () => {
    setRefreshTrigger(prev => prev + 1);
    setActiveTab(1); // Switch to manage tab after successful upload
  };

  return (
    <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column', pt: 2 }}>
      <Paper sx={{ mb: 3, borderRadius: 2, elevation: 1 }}>
        <Tabs
          value={activeTab}
          onChange={handleTabChange}
          indicatorColor="primary"
          textColor="primary"
          sx={{
            px: 3,
            py: 1,
            '& .MuiTab-root': {
              textTransform: 'none',
              fontWeight: 600,
              fontSize: '1rem',
              minHeight: 56,
              letterSpacing: 0.5
            }
          }}
        >
          <Tab label="Upload Documents" />
          <Tab label="Manage Documents" />
        </Tabs>
      </Paper>

      <Box sx={{ flexGrow: 1, minHeight: 0 }}>
        {activeTab === 0 ? (
          <DocumentUpload onUploadSuccess={handleUploadSuccess} />
        ) : (
          <DocumentManagement refreshTrigger={refreshTrigger} />
        )}
      </Box>
    </Box>
  );
}

export default function MainGrid({ selectedTab = 'chat' }: MainGridProps) {
  return (
    <Box sx={{ width: '100%', height: '100%', display: 'flex', flexDirection: 'column' }}>
      <Box sx={{ flexGrow: 1, minHeight: 0 }}>
        {selectedTab === 'chat' ? (
          <ChatContainer />
        ) : (
          <Paper
            elevation={0}
            sx={{
              height: '100%',
              bgcolor: 'background.default',
              borderRadius: 2,
            }}
          >
            <MediaContent />
          </Paper>
        )}
      </Box>
    </Box>
  );
}
