'use client';

import { useState } from 'react';
import type { } from '@mui/x-date-pickers/themeAugmentation';
import type { } from '@mui/x-charts/themeAugmentation';
import type { } from '@mui/x-tree-view/themeAugmentation';
import { alpha } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import Box from '@mui/material/Box';
import AppNavbar from './components/AppNavbar';
import Header from './components/Header';
import MainGrid from './components/MainGrid';
import SideMenu from './components/SideMenu';
import AppTheme from '../shared-theme/AppTheme';
import ToastProvider from './components/ToastProvider';
import {
  chartsCustomizations,
  dataGridCustomizations,
  treeViewCustomizations,
} from './theme/customizations';

const xThemeComponents = {
  ...chartsCustomizations,
  ...dataGridCustomizations,
  ...treeViewCustomizations,
};

export default function Dashboard(props: { disableCustomTheme?: boolean }) {
  const [selectedTab, setSelectedTab] = useState('chat');

  const handleTabChange = (tabId: string) => {
    setSelectedTab(tabId);
  };

  return (
    <AppTheme {...props} themeComponents={xThemeComponents}>
      <ToastProvider>
        <CssBaseline enableColorScheme />
        <Box sx={{ display: 'flex', height: '100vh' }}>
          <SideMenu selectedTab={selectedTab} onTabChange={handleTabChange} />
          <AppNavbar />
          <Box
            component="main"
            sx={(theme) => ({
              flexGrow: 1,
              backgroundColor: theme.vars
                ? `rgba(${theme.vars.palette.background.defaultChannel} / 1)`
                : alpha(theme.palette.background.default, 1),
              overflow: 'hidden',
              display: 'flex',
              flexDirection: 'column',
            })}
          >
            <Header />
            <Box
              sx={{
                flexGrow: 1,
                p: 3,
                pt: { xs: 10, md: 3 },
                display: 'flex',
                flexDirection: 'column',
                minHeight: 0,
              }}
            >
              <MainGrid selectedTab={selectedTab} />
            </Box>
          </Box>
        </Box>
      </ToastProvider>
    </AppTheme>
  );
}
