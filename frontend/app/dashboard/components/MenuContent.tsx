'use client';

import * as React from 'react';
import List from '@mui/material/List';
import ListItem from '@mui/material/ListItem';
import ListItemButton from '@mui/material/ListItemButton';
import ListItemIcon from '@mui/material/ListItemIcon';
import ListItemText from '@mui/material/ListItemText';
import Stack from '@mui/material/Stack';
import ChatRoundedIcon from '@mui/icons-material/ChatRounded';
import PermMediaRoundedIcon from '@mui/icons-material/PermMediaRounded';

const menuItems = [
  { text: 'Chat', icon: <ChatRoundedIcon />, id: 'chat' },
  { text: 'Media', icon: <PermMediaRoundedIcon />, id: 'media' },
];

interface MenuContentProps {
  selectedTab?: string;
  onTabChange?: (tabId: string) => void;
}

export default function MenuContent({ selectedTab = 'chat', onTabChange }: MenuContentProps) {
  const handleTabClick = (tabId: string) => {
    if (onTabChange) {
      onTabChange(tabId);
    }
  };

  return (
    <Stack sx={{ flexGrow: 1, p: 1 }}>
      <List dense>
        {menuItems.map((item) => (
          <ListItem key={item.id} disablePadding sx={{ display: 'block' }}>
            <ListItemButton 
              selected={selectedTab === item.id}
              onClick={() => handleTabClick(item.id)}
            >
              <ListItemIcon>{item.icon}</ListItemIcon>
              <ListItemText primary={item.text} />
            </ListItemButton>
          </ListItem>
        ))}
      </List>
    </Stack>
  );
}
