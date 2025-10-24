'use client';

import * as React from 'react';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Paper from '@mui/material/Paper';
import Tabs from '@mui/material/Tabs';
import Tab from '@mui/material/Tab';
import TextField from '@mui/material/TextField';
import IconButton from '@mui/material/IconButton';
import SearchIcon from '@mui/icons-material/Search';
import ChatContainer from './chat/ChatContainer';
import DocumentUpload from './media/DocumentUpload';
import DocumentManagement from './media/DocumentManagement';
import InfinityLoader from './InfinityLoader';
import Copyright from '../internals/components/Copyright';

interface MainGridProps {
  selectedTab?: string;
}

function MediaContent() {
  const [activeTab, setActiveTab] = React.useState(0);
  const [refreshTrigger, setRefreshTrigger] = React.useState(0);
  const [searchQuery, setSearchQuery] = React.useState('');
  const [activeSearchQuery, setActiveSearchQuery] = React.useState('');
  const [isSearching, setIsSearching] = React.useState(false);
  const [lastSearchTime, setLastSearchTime] = React.useState(0);

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setActiveTab(newValue);
  };

  const handleUploadSuccess = () => {
    // Document is queued for processing - no need to refresh or switch tabs
  };

  const handleSearchChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    setSearchQuery(event.target.value);
  };

  const handleSearchSubmit = async () => {
    const now = Date.now();
    const minInterval = 1000;
    
    if (!isSearching && (now - lastSearchTime) >= minInterval) {
      const startTime = Date.now();
      setIsSearching(true);
      setLastSearchTime(now);
      setActiveSearchQuery(searchQuery.trim());
      
      // Wait for minimum 2 seconds
      setTimeout(() => {
        const elapsedTime = Date.now() - startTime;
        const minDuration = 2000;
        
        if (elapsedTime < minDuration) {
          setTimeout(() => setIsSearching(false), minDuration - elapsedTime);
        } else {
          setIsSearching(false);
        }
      }, 100); // Small delay to ensure UI updates
    }
  };

  const handleClearSearch = () => {
    setSearchQuery('');
    setActiveSearchQuery('');
  };

  const handleSearchKeyPress = (event: React.KeyboardEvent) => {
    if (event.key === 'Enter') {
      handleSearchSubmit();
    }
  };

  return (
    <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column', pt: 2 }}>
      <Paper sx={{ mb: 3, borderRadius: 2, elevation: 1 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, px: 3, pt: 2 }}>
          <Tabs
            value={activeTab}
            onChange={handleTabChange}
            indicatorColor="primary"
            textColor="primary"
            sx={{
              flex: 1,
              '& .MuiTab-root': {
                textTransform: 'none',
                fontWeight: 600,
                fontSize: '1rem',
                minHeight: 48,
                letterSpacing: 0.5
              }
            }}
          >
            <Tab label="Document Manager" />
            <Tab label="Upload Document" />
          </Tabs>
          
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <TextField
              size="small"
              placeholder="Search documents..."
              value={searchQuery}
              onChange={handleSearchChange}
              onKeyPress={handleSearchKeyPress}
              sx={{ 
                width: 240,
                '& .MuiOutlinedInput-root': {
                  backgroundColor: 'background.paper',
                }
              }}
            />
            
            <IconButton
              size="small"
              onClick={handleSearchSubmit}
              disabled={isSearching}
              sx={{ 
                color: searchQuery.trim() && !isSearching ? 'primary.main' : 'text.secondary',
                '&:hover': {
                  backgroundColor: 'action.hover',
                },
                '&:disabled': { 
                  color: 'action.disabled'
                }
              }}
              title={isSearching ? 'Searching...' : searchQuery.trim() ? 'Search documents' : 'Show all documents'}
            >
              {isSearching ? <InfinityLoader size={20} /> : <SearchIcon />}
            </IconButton>
          </Box>
        </Box>
        <Box sx={{ px: 3, pb: 1 }}>
          <Box sx={{ height: 1, bgcolor: 'divider' }} />
        </Box>
      </Paper>

      <Box sx={{ flexGrow: 1, minHeight: 0 }}>
        {activeTab === 0 ? (
          <DocumentManagement 
            refreshTrigger={refreshTrigger} 
            searchQuery={activeSearchQuery}
            isSearchActive={!!activeSearchQuery.trim()}
          />
        ) : (
          <DocumentUpload onUploadSuccess={handleUploadSuccess} />
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
