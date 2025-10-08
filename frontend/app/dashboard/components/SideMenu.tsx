'use client';

import * as React from 'react';
import { styled } from '@mui/material/styles';
import MuiDrawer, { drawerClasses } from '@mui/material/Drawer';
import Box from '@mui/material/Box';
import MenuContent from './MenuContent';
import UserAccountSection from './UserAccountSection';

const drawerWidth = 240;

const Drawer = styled(MuiDrawer)({
  width: drawerWidth,
  flexShrink: 0,
  boxSizing: 'border-box',
  mt: 10,
  [`& .${drawerClasses.paper}`]: {
    width: drawerWidth,
    boxSizing: 'border-box',
  },
});

interface SideMenuProps {
  selectedTab?: string;
  onTabChange?: (tabId: string) => void;
}

export default function SideMenu({ selectedTab, onTabChange }: SideMenuProps) {
  return (
    <Drawer
      variant="permanent"
      sx={{
        display: { xs: 'none', md: 'block' },
        [`& .${drawerClasses.paper}`]: {
          backgroundColor: 'background.paper',
        },
      }}
    >
      <Box
        sx={{
          overflow: 'auto',
          height: '100%',
          display: 'flex',
          flexDirection: 'column',
          mt: 'calc(var(--template-frame-height, 0px) + 16px)',
        }}
      >
        <MenuContent selectedTab={selectedTab} onTabChange={onTabChange} />
      </Box>
      <UserAccountSection />
    </Drawer>
  );
}
